import Link from "next/link";
import type { ButtonHTMLAttributes, ReactNode } from "react";
import { IconMic } from "./Icons";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "amber";
type Size = "sm" | "md" | "lg";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  block?: boolean;
  href?: string;
  loading?: boolean;
  children: ReactNode;
};

export function Button({
  variant = "primary",
  size = "md",
  block,
  href,
  loading,
  className = "",
  children,
  disabled,
  ...rest
}: Props) {
  const cls = [
    "ui-btn",
    `ui-btn-${variant}`,
    `ui-btn-${size}`,
    block ? "ui-btn-block" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const label = loading ? "Please wait…" : children;

  if (href) {
    if (disabled || loading) {
      return (
        <span className={cls} aria-disabled="true">
          {label}
        </span>
      );
    }
    return (
      <Link href={href} className={cls}>
        {label}
      </Link>
    );
  }

  return (
    <button className={cls} disabled={disabled || loading} {...rest}>
      {label}
    </button>
  );
}

export function Chip({
  selected,
  children,
  onClick,
  disabled,
}: {
  selected?: boolean;
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className={`chip${selected ? " is-on" : ""}`}
      aria-pressed={selected}
      onClick={onClick}
      disabled={disabled}
    >
      {children}
    </button>
  );
}

export function Tab({
  selected,
  children,
  onClick,
}: {
  selected?: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button type="button" role="tab" className={`tab${selected ? " is-on" : ""}`} aria-selected={selected} onClick={onClick}>
      {children}
    </button>
  );
}

export function IconButton({
  label,
  onClick,
  children,
}: {
  label: string;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button type="button" className="icon-btn" aria-label={label} onClick={onClick}>
      {children}
    </button>
  );
}

export function RecordButton({
  recording,
  onClick,
}: {
  recording: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className={`record-btn${recording ? " is-on" : ""}`}
      onClick={onClick}
      aria-pressed={recording}
      aria-label={recording ? "Stop recording" : "Start recording"}
    >
      {recording ? <span className="rec-dot" /> : <IconMic />}
      {recording ? "Stop" : "Record"}
    </button>
  );
}

export function Brand({ href = "/" }: { href?: string }) {
  return (
    <Link href={href} className="brand">
      <span className="brand-mark">N</span>
      Northband
    </Link>
  );
}
