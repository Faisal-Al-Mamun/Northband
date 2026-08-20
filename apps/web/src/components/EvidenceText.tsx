"use client";

import { useMemo } from "react";

type Props = {
  text: string;
  quotes: string[];
};

export function EvidenceText({ text, quotes }: Props) {
  const parts = useMemo(() => splitByQuotes(text, quotes), [text, quotes]);
  return (
    <p className="answer-block">
      {parts.map((part, index) =>
        part.highlight ? (
          <mark className="evidence-mark" key={`${part.value}-${index}`}>
            {part.value}
          </mark>
        ) : (
          <span key={`${part.value}-${index}`}>{part.value}</span>
        ),
      )}
    </p>
  );
}

function splitByQuotes(text: string, quotes: string[]) {
  const unique = quotes
    .map((item) => item.trim())
    .filter((item) => item.length >= 4)
    .filter((item, index, all) => all.findIndex((other) => other.toLowerCase() === item.toLowerCase()) === index)
    .sort((a, b) => b.length - a.length);
  if (!text || unique.length === 0) return [{ value: text, highlight: false }];

  const ranges: { start: number; end: number }[] = [];
  const lowered = text.toLowerCase();
  for (const quote of unique) {
    const needle = quote.toLowerCase();
    let from = 0;
    while (from < lowered.length) {
      const found = lowered.indexOf(needle, from);
      if (found === -1) break;
      ranges.push({ start: found, end: found + quote.length });
      from = found + quote.length;
    }
  }
  ranges.sort((a, b) => a.start - b.start || b.end - a.end);
  const merged: { start: number; end: number }[] = [];
  for (const range of ranges) {
    const last = merged[merged.length - 1];
    if (!last || range.start > last.end) merged.push({ ...range });
    else last.end = Math.max(last.end, range.end);
  }
  const parts: { value: string; highlight: boolean }[] = [];
  let cursor = 0;
  for (const range of merged) {
    if (range.start > cursor) parts.push({ value: text.slice(cursor, range.start), highlight: false });
    parts.push({ value: text.slice(range.start, range.end), highlight: true });
    cursor = range.end;
  }
  if (cursor < text.length) parts.push({ value: text.slice(cursor), highlight: false });
  return parts;
}
