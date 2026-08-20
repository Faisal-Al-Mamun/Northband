import type { ReactNode } from "react";
import { statusLabel, statusTone } from "@/lib/labels";

export function PageHeader({
  title,
  lede,
  eyebrow,
  action,
}: {
  title: string;
  lede?: string;
  eyebrow?: string;
  action?: ReactNode;
}) {
  return (
    <div className="topbar">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1 className="page-title">{title}</h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {action}
    </div>
  );
}

export function EmptyState({
  title,
  body,
  children,
}: {
  title: string;
  body: string;
  children?: ReactNode;
}) {
  return (
    <div className="card empty">
      <h2>{title}</h2>
      <p className="muted">{body}</p>
      {children}
    </div>
  );
}

export function StatusBadge({ status, stage }: { status: string; stage?: string | null }) {
  return <span className={`badge ${statusTone(status)}`}>{statusLabel(status, stage)}</span>;
}

export function Stepper({ step, total, label }: { step: number; total: number; label: string }) {
  return (
    <div>
      <div className="step-meta">
        <span>
          Step {step} of {total}
        </span>
        <span>{label}</span>
      </div>
      <div className="stepper" aria-hidden="true">
        {Array.from({ length: total }, (_, index) => (
          <span key={index} className={`step${index < step ? " is-on" : ""}`} />
        ))}
      </div>
    </div>
  );
}

export function Toast({ message }: { message: string }) {
  return (
    <div className="toast" role="status">
      {message}
    </div>
  );
}

export function PageSkeleton() {
  return (
    <div className="skeleton-page" aria-hidden="true">
      <div className="skeleton skeleton-hero" />
      <div className="skeleton skeleton-row" />
      <div className="skeleton skeleton-row" />
    </div>
  );
}

export function ErrorCard({
  message,
  children,
}: {
  message: string;
  children?: ReactNode;
}) {
  return (
    <div className="card section-gap">
      <p className="error">{message}</p>
      {children}
    </div>
  );
}
