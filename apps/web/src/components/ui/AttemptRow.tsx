import Link from "next/link";
import type { EvaluationSummary } from "@/lib/types";
import { attemptTitle, shortDate } from "@/lib/labels";
import { StatusBadge } from "./PageHeader";

export function AttemptRow({ item }: { item: EvaluationSummary }) {
  return (
    <Link className="attempt-row" href={`/app/results/${item.id}`}>
      <span className="attempt-copy">
        <strong>{attemptTitle(item.skill, item.module, item.task)}</strong>
        <span className="muted">{shortDate(item.created_at)}</span>
      </span>
      <StatusBadge status={item.status} stage={item.stage} />
      <strong>{item.overall_band?.toFixed(1) ?? "—"}</strong>
    </Link>
  );
}
