"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TaskVisualSpec } from "@/lib/taskVisuals";

const PIE_COLORS = ["#1b4d4a", "#8a6328", "#3d6b7a", "#6b4f3a", "#4a6b52"];

export function TaskVisual({ spec }: { spec: TaskVisualSpec }) {
  const keys = spec.series.map((item) => item.key);
  return (
    <figure className="task-figure">
      <div className={`task-chart${spec.kind === "pie" ? " is-pie" : ""}`} role="img" aria-label={spec.title}>
        <ResponsiveContainer width="100%" height={spec.kind === "pie" ? 300 : 280}>
          {spec.kind === "line" ? (
            <LineChart data={spec.rows} margin={{ top: 8, right: 12, left: 8, bottom: 4 }}>
              <CartesianGrid stroke="#ddd8ce" vertical={false} />
              <XAxis dataKey={spec.xKey} tick={{ fill: "#5c6b73", fontSize: 12 }} />
              <YAxis domain={[0, 100]} ticks={[0, 20, 40, 60, 80, 100]} tick={{ fill: "#5c6b73", fontSize: 12 }} />
              <Tooltip />
              <Legend />
              {spec.series.map((series) => (
                <Line
                  key={series.key}
                  type="monotone"
                  dataKey={series.key}
                  name={series.label}
                  stroke={series.color}
                  strokeWidth={2.2}
                  dot={{ r: 3.5 }}
                />
              ))}
            </LineChart>
          ) : spec.kind === "bar" ? (
            <BarChart data={spec.rows} margin={{ top: 8, right: 12, left: 8, bottom: 4 }}>
              <CartesianGrid stroke="#ddd8ce" vertical={false} />
              <XAxis dataKey={spec.xKey} tick={{ fill: "#5c6b73", fontSize: 12 }} interval={0} />
              <YAxis domain={[0, 100]} ticks={[0, 20, 40, 60, 80, 100]} tick={{ fill: "#5c6b73", fontSize: 12 }} />
              <Tooltip />
              {spec.series.map((series) => (
                <Bar key={series.key} dataKey={series.key} name={series.label} fill={series.color} radius={[6, 6, 0, 0]} />
              ))}
            </BarChart>
          ) : (
            <PieChart>
              <Pie
                data={spec.rows}
                dataKey={spec.series[0].key}
                nameKey={spec.xKey}
                cx="50%"
                cy="48%"
                innerRadius={46}
                outerRadius={82}
                paddingAngle={2}
              >
                {spec.rows.map((row, index) => (
                  <Cell key={String(row[spec.xKey])} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
      <div className="figure-table-wrap">
        <table className="figure-table">
          <thead>
            <tr>
              <th>{spec.xKey.charAt(0).toUpperCase() + spec.xKey.slice(1)}</th>
              {spec.series.map((series) => (
                <th key={series.key}>{series.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {spec.rows.map((row) => (
              <tr key={String(row[spec.xKey])}>
                <th scope="row">{row[spec.xKey]}</th>
                {keys.map((key) => (
                  <td key={key}>{row[key]}{typeof row[key] === "number" ? "%" : ""}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <figcaption>{spec.title}{spec.yLabel ? ` (${spec.yLabel.toLowerCase()})` : ""}</figcaption>
    </figure>
  );
}
