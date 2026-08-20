"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { EvaluationSummary } from "@/lib/types";
import { Button, Chip } from "@/components/ui/Button";
import { AttemptRow } from "@/components/ui/AttemptRow";
import { EmptyState, PageHeader, PageSkeleton } from "@/components/ui/PageHeader";

export default function AttemptsPage() {
  const [rows, setRows] = useState<EvaluationSummary[]>([]);
  const [skill, setSkill] = useState("");
  const [module, setModule] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const params = new URLSearchParams();
    if (skill) params.set("skill", skill);
    if (module) params.set("module", module);
    const query = params.toString() ? `?${params}` : "";
    setLoading(true);
    api
      .listEvaluations(query)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [skill, module]);

  return (
    <div className="section-gap">
      <PageHeader eyebrow="Review" title="Attempts" lede="Every evaluation, including ones still scoring." />
      <div className="chip-row">
        <Chip selected={skill === ""} onClick={() => setSkill("")}>
          All skills
        </Chip>
        <Chip selected={skill === "listening"} onClick={() => setSkill("listening")}>
          Listening
        </Chip>
        <Chip selected={skill === "reading"} onClick={() => setSkill("reading")}>
          Reading
        </Chip>
        <Chip selected={skill === "writing"} onClick={() => setSkill("writing")}>
          Writing
        </Chip>
        <Chip selected={skill === "speaking"} onClick={() => setSkill("speaking")}>
          Speaking
        </Chip>
        <Chip selected={module === ""} onClick={() => setModule("")}>
          All modules
        </Chip>
        <Chip selected={module === "academic"} onClick={() => setModule("academic")}>
          Academic
        </Chip>
        <Chip selected={module === "general"} onClick={() => setModule("general")}>
          General Training
        </Chip>
      </div>
      {loading ? (
        <PageSkeleton />
      ) : rows.length === 0 ? (
        <EmptyState title="No attempts yet" body="Sit a Listening, Reading, Writing, or Speaking paper to see it here.">
          <div className="btn-row">
            <Button href="/app/listening">Listen</Button>
            <Button href="/app/reading" variant="secondary">
              Read
            </Button>
            <Button href="/app/writing" variant="secondary">
              Write
            </Button>
          </div>
        </EmptyState>
      ) : (
        <div className="card">{rows.map((item) => <AttemptRow key={item.id} item={item} />)}</div>
      )}
    </div>
  );
}
