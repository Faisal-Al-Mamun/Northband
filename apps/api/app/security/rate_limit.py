from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, Request, status

_hits: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def enforce_rate_limit(key: str, *, limit: int, window_seconds: int) -> None:
    now = monotonic()
    bucket = _hits[key]
    cutoff = now - window_seconds
    while bucket and bucket[0] < cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many attempts. Wait a few minutes and try again.",
        )
    bucket.append(now)


def limit_auth(request: Request) -> None:
    enforce_rate_limit(f"auth:{client_ip(request)}", limit=8, window_seconds=300)


def limit_evaluations(request: Request) -> None:
    enforce_rate_limit(f"eval:{client_ip(request)}", limit=20, window_seconds=600)
