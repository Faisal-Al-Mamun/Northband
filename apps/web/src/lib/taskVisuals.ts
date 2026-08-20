export type VisualKind = "line" | "bar" | "pie";

export type VisualSeries = {
  key: string;
  label: string;
  color: string;
};

export type TaskVisualSpec = {
  id: string;
  kind: VisualKind;
  title: string;
  yLabel?: string;
  xKey: string;
  series: VisualSeries[];
  rows: Record<string, string | number>[];
};

const HOUSEHOLDS: TaskVisualSpec = {
  id: "households-ew",
  kind: "line",
  title: "Households in owned and rented accommodation, England and Wales, 1918–2011",
  yLabel: "Percentage of households",
  xKey: "year",
  series: [
    { key: "Owned", label: "Owned", color: "#1b4d4a" },
    { key: "Rented", label: "Rented", color: "#8a6328" },
  ],
  rows: [
    { year: "1918", Owned: 23, Rented: 77 },
    { year: "1939", Owned: 32, Rented: 68 },
    { year: "1953", Owned: 32, Rented: 68 },
    { year: "1961", Owned: 42, Rented: 58 },
    { year: "1971", Owned: 50, Rented: 50 },
    { year: "1981", Owned: 58, Rented: 42 },
    { year: "1991", Owned: 67, Rented: 33 },
    { year: "2001", Owned: 69, Rented: 31 },
    { year: "2011", Owned: 64, Rented: 36 },
  ],
};

const ENERGY: TaskVisualSpec = {
  id: "energy-2020",
  kind: "bar",
  title: "Share of energy use by sector, 2020",
  yLabel: "Percentage of total energy use",
  xKey: "sector",
  series: [{ key: "Share", label: "Share", color: "#1b4d4a" }],
  rows: [
    { sector: "Transport", Share: 29 },
    { sector: "Industry", Share: 25 },
    { sector: "Residential", Share: 22 },
    { sector: "Commercial", Share: 15 },
    { sector: "Agriculture & other", Share: 9 },
  ],
};

const ENERGY_MIX: TaskVisualSpec = {
  id: "energy-mix-2000-2020",
  kind: "bar",
  title: "Energy produced by source in a European country, 2000 and 2020",
  yLabel: "Percentage of total energy produced",
  xKey: "source",
  series: [
    { key: "y2000", label: "2000", color: "#1b4d4a" },
    { key: "y2020", label: "2020", color: "#8a6328" },
  ],
  rows: [
    { source: "Coal", y2000: 42, y2020: 18 },
    { source: "Gas", y2000: 28, y2020: 31 },
    { source: "Nuclear", y2000: 22, y2020: 21 },
    { source: "Renewables", y2000: 8, y2020: 30 },
  ],
};

const INTERNET: TaskVisualSpec = {
  id: "internet-users",
  kind: "line",
  title: "Internet users as a percentage of the population, 2000–2020",
  yLabel: "Percentage of population",
  xKey: "year",
  series: [
    { key: "UK", label: "UK", color: "#1b4d4a" },
    { key: "USA", label: "USA", color: "#8a6328" },
    { key: "China", label: "China", color: "#3d6b7a" },
  ],
  rows: [
    { year: "2000", UK: 27, USA: 43, China: 2 },
    { year: "2005", UK: 70, USA: 68, China: 9 },
    { year: "2010", UK: 85, USA: 72, China: 34 },
    { year: "2015", UK: 92, USA: 75, China: 50 },
    { year: "2020", UK: 95, USA: 89, China: 70 },
  ],
};

const LIBRARY_VISITS: TaskVisualSpec = {
  id: "library-visits",
  kind: "pie",
  title: "Reasons for visiting a public library (survey of 1,000 adults)",
  xKey: "reason",
  series: [{ key: "Percent", label: "Percent", color: "#1b4d4a" }],
  rows: [
    { reason: "Borrow books", Percent: 38 },
    { reason: "Study / work", Percent: 24 },
    { reason: "Use computers", Percent: 18 },
    { reason: "Children’s activities", Percent: 12 },
    { reason: "Other", Percent: 8 },
  ],
};

const CATALOG: { spec: TaskVisualSpec; tests: RegExp[] }[] = [
  {
    spec: HOUSEHOLDS,
    tests: [/household/i, /owned and rented/i, /england and wales/i, /1918/],
  },
  {
    spec: ENERGY_MIX,
    tests: [/energy produced/i, /coal, gas, nuclear/i, /2000 and 2020/],
  },
  {
    spec: ENERGY,
    tests: [/energy use/i, /by sector/i],
  },
  {
    spec: INTERNET,
    tests: [/internet users/i, /percentage of the population/i],
  },
  {
    spec: LIBRARY_VISITS,
    tests: [/public library/i, /reasons for visiting/i],
  },
  {
    spec: {
      id: "commute-modes",
      kind: "bar",
      title: "Main mode of travel to work in a city, 1990–2020",
      yLabel: "Percentage of workers",
      xKey: "mode",
      series: [
        { key: "y1990", label: "1990", color: "#1b4d4a" },
        { key: "y2005", label: "2005", color: "#8a6328" },
        { key: "y2020", label: "2020", color: "#3d6b7a" },
      ],
      rows: [
        { mode: "Car", y1990: 62, y2005: 58, y2020: 44 },
        { mode: "Bus", y1990: 18, y2005: 16, y2020: 14 },
        { mode: "Rail", y1990: 9, y2005: 12, y2020: 18 },
        { mode: "Cycle / walk", y1990: 8, y2005: 10, y2020: 16 },
        { mode: "Work from home", y1990: 3, y2005: 4, y2020: 8 },
      ],
    },
    tests: [/travelled to work/i, /1990, 2005 and 2020/i],
  },
  {
    spec: {
      id: "uni-enrolment",
      kind: "bar",
      title: "University enrolment by field, 2010 and 2022",
      yLabel: "Percentage of students",
      xKey: "field",
      series: [
        { key: "y2010", label: "2010", color: "#1b4d4a" },
        { key: "y2022", label: "2022", color: "#8a6328" },
      ],
      rows: [
        { field: "Business", y2010: 28, y2022: 24 },
        { field: "STEM", y2010: 22, y2022: 31 },
        { field: "Health", y2010: 14, y2022: 18 },
        { field: "Arts & humanities", y2010: 21, y2022: 15 },
        { field: "Education", y2010: 15, y2022: 12 },
      ],
    },
    tests: [/enrolment by field/i, /2010 and 2022/i],
  },
  {
    spec: {
      id: "water-use",
      kind: "pie",
      title: "Freshwater use by sector, 2021",
      xKey: "sector",
      series: [{ key: "Percent", label: "Percent", color: "#1b4d4a" }],
      rows: [
        { sector: "Agriculture", Percent: 54 },
        { sector: "Industry", Percent: 22 },
        { sector: "Households", Percent: 16 },
        { sector: "Energy", Percent: 5 },
        { sector: "Other", Percent: 3 },
      ],
    },
    tests: [/freshwater was used/i, /water was used in a country in 2021/i],
  },
];

export function findTaskVisual(
  prompt: string,
  opts?: { skill?: string; task?: string; module?: string },
): TaskVisualSpec | null {
  if (opts?.skill && opts.skill !== "writing") return null;
  if (opts?.task && opts.task !== "task1") return null;
  if (opts?.module === "general") return null;
  const text = prompt || "";
  for (const entry of CATALOG) {
    if (entry.tests.some((re) => re.test(text))) return entry.spec;
  }
  return null;
}

export function mentionsVisual(prompt: string) {
  return /\b(chart|graph|figure|diagram|table|map)\b/i.test(prompt);
}

const FALLBACK_COLORS = ["#1b4d4a", "#8a6328", "#3d6b7a", "#6b4f3a"];

export function normalizeTaskVisual(raw: TaskVisualSpec | null | undefined): TaskVisualSpec | null {
  if (!raw || !Array.isArray(raw.rows) || raw.rows.length === 0) return null;
  const series = (raw.series || []).map((item, index) => ({
    key: item.key,
    label: item.label || item.key,
    color: item.color || FALLBACK_COLORS[index % FALLBACK_COLORS.length],
  }));
  if (!series.length) return null;
  return {
    id: raw.id || "bank-visual",
    kind: raw.kind === "line" || raw.kind === "pie" ? raw.kind : "bar",
    title: raw.title,
    yLabel: raw.yLabel,
    xKey: raw.xKey,
    series,
    rows: raw.rows,
  };
}
