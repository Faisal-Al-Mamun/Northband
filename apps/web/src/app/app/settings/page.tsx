"use client";

import { FormEvent, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";
import { Button, Chip } from "@/components/ui/Button";
import { ErrorCard, PageHeader, PageSkeleton, Toast } from "@/components/ui/PageHeader";

export default function SettingsPage() {
  const [user, setUser] = useState<User | null>(null);
  const [module, setModule] = useState<"academic" | "general">("academic");
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    api
      .me()
      .then((profile) => {
        setUser(profile);
        setModule(profile.preferred_module);
      })
      .catch(() => setLoadError("Could not load your profile."));
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    setError("");
    setSaved(false);
    try {
      const updated = await api.updateMe({
        display_name: String(data.get("display_name")),
        target_band: Number(data.get("target_band")),
        preferred_module: module,
      });
      setUser(updated);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2400);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  }

  if (loadError) {
    return (
      <ErrorCard message={loadError}>
        <Button href="/login">Sign in again</Button>
      </ErrorCard>
    );
  }
  if (!user) return <PageSkeleton />;

  return (
    <div>
      <PageHeader
        eyebrow="Account"
        title="Settings"
        lede="Your target band and preferred module shape the study recommendations."
      />
      <form className="card section-gap" onSubmit={onSubmit}>
        <label>
          Name
          <input name="display_name" defaultValue={user.display_name} required maxLength={120} />
        </label>
        <label>
          Email
          <input value={user.email} readOnly className="settings-email" />
        </label>
        <label>
          Target band
          <input
            name="target_band"
            type="number"
            min={4}
            max={9}
            step={0.5}
            defaultValue={user.target_band ?? 7}
          />
          <span className="helper">Half bands from 4.0 to 9.0.</span>
        </label>
        <div>
          <p className="field-label">Preferred module</p>
          <div className="chip-row">
            <Chip selected={module === "academic"} onClick={() => setModule("academic")}>
              Academic
            </Chip>
            <Chip selected={module === "general"} onClick={() => setModule("general")}>
              General Training
            </Chip>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        <Button type="submit">Save settings</Button>
      </form>
      {saved && <Toast message="Settings saved" />}
    </div>
  );
}
