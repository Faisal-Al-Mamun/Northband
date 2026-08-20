from __future__ import annotations

import json
import re
import time
from typing import Any
from uuid import UUID

import httpx
from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from app.config import settings
from app.db.models import LlmCallLog
from app.db.session import SessionLocal

JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)

_openai_clients: dict[tuple[str, str], AsyncOpenAI] = {}
_gemini_client = None


class ProviderConfig(BaseModel):
    provider: str
    model: str


AGENT_ENV = {
    "writing": "agent_writing",
    "speaking": "agent_speaking",
    "grammar": "agent_grammar",
    "scoring": "agent_scoring",
    "feedback": "agent_feedback",
    "performance": "agent_performance",
    "revision": "agent_revision",
    "explain": "agent_explain",
    "coach": "agent_coach",
    "bank": "agent_bank",
}

# Grammar, performance, and explain are cheap specialists: smaller model when configured.
CHEAP_AGENTS = frozenset({"grammar", "performance", "explain"})


def resolve_provider(agent: str) -> ProviderConfig:
    override = getattr(settings, AGENT_ENV.get(agent, ""), "") or ""
    if override and ":" in override:
        provider, model = override.split(":", 1)
        return ProviderConfig(provider=provider.strip(), model=model.strip())
    if agent in CHEAP_AGENTS and (settings.llm_cheap_model or settings.llm_cheap_provider):
        return ProviderConfig(
            provider=(settings.llm_cheap_provider or settings.llm_default_provider).strip(),
            model=(settings.llm_cheap_model or settings.llm_default_model).strip(),
        )
    return ProviderConfig(provider=settings.llm_default_provider, model=settings.llm_default_model)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    match = JSON_FENCE.search(text)
    if match:
        text = match.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object in model response")
    return json.loads(text[start : end + 1])


def _json_schema(schema: type[BaseModel]) -> dict[str, Any]:
    raw = schema.model_json_schema()
    return _with_additional_properties(raw)


def _with_additional_properties(node: Any) -> Any:
    if isinstance(node, dict):
        if node.get("type") == "object" or "properties" in node:
            node = {**node, "additionalProperties": node.get("additionalProperties", False)}
        return {key: _with_additional_properties(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_with_additional_properties(item) for item in node]
    return node


def _openai_client(base_url: str, api_key: str) -> AsyncOpenAI:
    key = (base_url, api_key or "not-set")
    client = _openai_clients.get(key)
    if client is None:
        client = AsyncOpenAI(base_url=base_url, api_key=api_key or "not-set")
        _openai_clients[key] = client
    return client


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        from google import genai

        _gemini_client = genai.Client(api_key=settings.gemini_api_key)
    return _gemini_client


async def _complete_openai_compat(
    *,
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel] | None = None,
) -> tuple[str, int | None, int | None]:
    client = _openai_client(base_url, api_key)
    response_format: dict[str, Any] = {"type": "json_object"}
    if schema is not None:
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": schema.__name__[:64],
                "schema": _json_schema(schema),
                "strict": False,
            },
        }
    try:
        response = await client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format=response_format,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except Exception:
        if response_format.get("type") == "json_schema":
            response = await client.chat.completions.create(
                model=model,
                temperature=0.2,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        else:
            raise
    content = response.choices[0].message.content or ""
    usage = response.usage
    return (
        content,
        usage.prompt_tokens if usage else None,
        usage.completion_tokens if usage else None,
    )


async def _complete_gemini(
    *,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel] | None = None,
) -> tuple[str, int | None, int | None]:
    client = _get_gemini_client()
    config: dict[str, Any] = {"temperature": 0.2, "response_mime_type": "application/json"}
    if schema is not None:
        config["response_schema"] = schema
    try:
        response = await client.aio.models.generate_content(
            model=model or settings.gemini_model,
            contents=f"{system}\n\n{user}\n\nReturn valid JSON only.",
            config=config,
        )
    except Exception:
        config.pop("response_schema", None)
        response = await client.aio.models.generate_content(
            model=model or settings.gemini_model,
            contents=f"{system}\n\n{user}\n\nReturn valid JSON only.",
            config=config,
        )
    usage = getattr(response, "usage_metadata", None)
    prompt_tokens = getattr(usage, "prompt_token_count", None) if usage else None
    completion_tokens = getattr(usage, "candidates_token_count", None) if usage else None
    return response.text or "", prompt_tokens, completion_tokens


def _has_live_key(provider: str) -> bool:
    if provider == "openrouter":
        return bool(settings.openrouter_api_key)
    if provider == "gemini":
        return bool(settings.gemini_api_key)
    if provider in {"openai_compat", "openai"}:
        return bool(settings.openai_compat_api_key)
    if provider == "mock":
        return True
    return False


def live_llm_configured(agent: str = "bank") -> bool:
    cfg = resolve_provider(agent)
    if cfg.provider == "mock":
        return False
    return _has_live_key(cfg.provider)


async def _call_provider(
    provider: str,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel] | None = None,
) -> tuple[str, int | None, int | None]:
    if provider == "openrouter":
        return await _complete_openai_compat(
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            model=model,
            system=system,
            user=user,
            schema=schema,
        )
    if provider in {"openai_compat", "openai"}:
        return await _complete_openai_compat(
            base_url=settings.openai_compat_base_url,
            api_key=settings.openai_compat_api_key,
            model=model or settings.openai_compat_model,
            system=system,
            user=user,
            schema=schema,
        )
    if provider == "gemini":
        return await _complete_gemini(model=model, system=system, user=user, schema=schema)
    raise ValueError(f"Unknown provider: {provider}")


async def _log_call(
    *,
    job_id: UUID | None,
    agent: str,
    provider: str,
    model: str,
    latency_ms: int,
    prompt_tokens: int | None,
    completion_tokens: int | None,
    success: bool,
    error: str | None,
) -> None:
    async with SessionLocal() as db:
        db.add(
            LlmCallLog(
                job_id=job_id,
                agent=agent,
                provider=provider,
                model=model,
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                success=success,
                error=error,
            )
        )
        await db.commit()


class LLMRouter:
    async def complete_json(
        self,
        *,
        agent: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        job_id: UUID | None = None,
        retries: int = 2,
    ) -> BaseModel:
        configured = resolve_provider(agent)
        provider = configured.provider
        model = configured.model
        if not _has_live_key(provider):
            provider = "mock"
            model = "heuristic-fallback"

        schema_hint = json.dumps(_json_schema(schema), ensure_ascii=False)
        system_with_schema = f"{system}\n\nJSON schema:\n{schema_hint}"

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            started = time.perf_counter()
            prompt_tokens = completion_tokens = None
            try:
                extra = ""
                if attempt and last_error:
                    extra = (
                        f"\n\nYour previous output failed validation: {last_error}. "
                        "Return ONLY a JSON object that matches the required schema."
                    )
                if provider == "mock":
                    from app.llm.mock_responses import mock_json_for_agent

                    raw = json.dumps(mock_json_for_agent(agent, user))
                else:
                    raw, prompt_tokens, completion_tokens = await _call_provider(
                        provider, model, system_with_schema, user + extra, schema
                    )
                parsed = schema.model_validate(_extract_json(raw))
                await _log_call(
                    job_id=job_id,
                    agent=agent,
                    provider=provider,
                    model=model,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    success=True,
                    error=None,
                )
                return parsed
            except (ValidationError, ValueError, json.JSONDecodeError, httpx.HTTPError, Exception) as exc:
                last_error = exc
                await _log_call(
                    job_id=job_id,
                    agent=agent,
                    provider=provider,
                    model=model,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    success=False,
                    error=str(exc)[:2000],
                )
        if last_error:
            raise last_error
        raise RuntimeError("LLM call failed")


llm_router = LLMRouter()
