"use client";

import {
  Bar,
  BarChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { criterionShort } from "@/lib/labels";

type Row = { criterion: string; band: number };

export function CriteriaRadar({ rows }: { rows: Row[] }) {
  const data = rows.map((row) => ({ subject: criterionShort(row.criterion), band: row.band, full: 9 }));
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid stroke="#ddd8ce" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: "#12202a", fontSize: 12 }} />
          <Radar dataKey="band" stroke="#1b4d4a" fill="#1b4d4a" fillOpacity={0.22} />
          <Tooltip />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function CriteriaBars({ rows }: { rows: Row[] }) {
  const data = rows.map((row) => ({ name: criterionShort(row.criterion), band: row.band }));
  return (
    <div className="chart-box">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 12 }}>
          <XAxis type="number" domain={[0, 9]} ticks={[0, 3, 6, 9]} />
          <YAxis type="category" dataKey="name" width={52} tick={{ fontSize: 12 }} />
          <Tooltip />
          <Bar dataKey="band" fill="#1b4d4a" radius={[0, 6, 6, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
