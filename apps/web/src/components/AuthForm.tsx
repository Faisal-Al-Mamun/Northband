"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { api, getToken, setToken } from "@/lib/api";
import { Brand, Button } from "@/components/ui/Button";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) return;
    api
      .me()
      .then(() => router.replace("/app"))
      .catch(() => setToken(null));
  }, [router]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    const data = new FormData(event.currentTarget);
    const password = String(data.get("password"));
    const confirm = String(data.get("confirm") || "");
    if (mode === "register" && password !== confirm) {
      setError("Passwords do not match.");
      return;
    }
    setPending(true);
    try {
      const payload =
        mode === "register"
          ? await api.register({
              email: String(data.get("email")).trim(),
              password,
              display_name: String(data.get("display_name")).trim(),
            })
          : await api.login({
              email: String(data.get("email")).trim(),
              password,
            });
      setToken(payload.access_token);
      router.push("/app");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="auth-split">
      <aside className="auth-brand">
        <Brand href="/" />
        <div>
          <h2>Practice like the exam. Review like a coach.</h2>
          <p>Four official criteria, reusable language notes, and a short list of what to study next.</p>
        </div>
        <p className="auth-note">Estimates are for practice only — not official IELTS results.</p>
      </aside>
      <div className="auth-form">
        <form className="auth-panel" onSubmit={onSubmit}>
          <h1>{mode === "login" ? "Sign in" : "Create your account"}</h1>
          <p className="muted">
            {mode === "login" ? "Continue to your studio." : "Takes less than a minute. Then you can sit a task."}
          </p>
          {mode === "register" && (
            <label>
              Name
              <input name="display_name" required maxLength={120} placeholder="Your name" autoComplete="name" />
            </label>
          )}
          <label>
            Email
            <input name="email" type="email" required autoComplete="email" maxLength={255} />
          </label>
          <label>
            Password
            <span className="password-wrap">
              <input
                name="password"
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                maxLength={72}
                autoComplete={mode === "register" ? "new-password" : "current-password"}
              />
              <button type="button" onClick={() => setShowPassword((value) => !value)}>
                {showPassword ? "Hide" : "Show"}
              </button>
            </span>
            <span className="helper">At least 8 characters.</span>
          </label>
          {mode === "register" && (
            <label>
              Confirm password
              <input
                name="confirm"
                type={showPassword ? "text" : "password"}
                required
                minLength={8}
                maxLength={72}
                autoComplete="new-password"
              />
            </label>
          )}
          {error && <p className="error">{error}</p>}
          <Button type="submit" loading={pending} block>
            {mode === "login" ? "Sign in" : "Create account"}
          </Button>
          <p className="muted">
            {mode === "login" ? (
              <>
                New here?{" "}
                <Link className="inline-link" href="/register">
                  Create an account
                </Link>
              </>
            ) : (
              <>
                Already have an account?{" "}
                <Link className="inline-link" href="/login">
                  Sign in
                </Link>
              </>
            )}
          </p>
        </form>
      </div>
    </div>
  );
}
