"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ProgressSummary } from "@/lib/types";
import { shortDate } from "@/lib/labels";

export function BandTrendChart({ series }: { series: ProgressSummary["series"] }) {
  const data = series.map((point, index) => ({
    name: shortDate(point.created_at) || `#${index + 1}`,
    Writing: point.skill === "writing" ? point.overall_band : null,
    Speaking: point.skill === "speaking" ? point.overall_band : null,
  }));

  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke="#ddd8ce" vertical={false} />
          <XAxis dataKey="name" tick={{ fill: "#5c6b73", fontSize: 12 }} />
          <YAxis domain={[4, 9]} ticks={[4, 5, 6, 7, 8, 9]} tick={{ fill: "#5c6b73", fontSize: 12 }} />
          <Tooltip />
          <Legend />
          <Line type="monotone" dataKey="Writing" stroke="#1b4d4a" strokeWidth={2} connectNulls dot />
          <Line type="monotone" dataKey="Speaking" stroke="#8a6328" strokeWidth={2} connectNulls dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
