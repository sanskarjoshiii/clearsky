import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ImpactFactor, ImpactTableData } from "../api/types";
import { ImpactTable } from "../components/ImpactTable";
import { Sparkline } from "../components/Sparkline";
import { headline, impactAmount, inUnit } from "../lib/impact";

// TEST VALUES, not real emission factors (clearsky ships with none).
const FACTORS: Record<string, ImpactFactor> = {
  pm25: { label: "PM2.5", unit: "kg", kg_per_tonne: 2, source: "TEST VALUE", url: null },
  co2: { label: "CO₂", unit: "t", kg_per_tonne: 1000, source: "TEST VALUE", url: null },
};

const trend = (kg: number) => [
  { date: "2026-09-15", cumulative: 0 },
  { date: "2026-10-20", cumulative: kg },
];

function table(over: Partial<ImpactTableData> = {}): ImpactTableData {
  const village = (n: number, label: string, kg: number) => ({
    label,
    village_id: `V${n}`,
    fields: 1,
    acres: 8,
    tonnes: kg / 2,
    impact: { pm25: kg, co2: kg * 500 },
    trend: trend(kg),
    by_week: { "2026-10-19": { pm25: kg, co2: kg * 500 } },
    rows: [
      {
        label: `Farmer ${n}.`,
        village: label,
        acres: 8,
        tonnes: kg / 2,
        cleared_date: "2026-10-20",
        impact: { pm25: kg, co2: kg * 500 },
        trend: trend(kg),
        by_week: { "2026-10-19": { pm25: kg, co2: kg * 500 } },
      },
    ],
  });
  const groups = Array.from({ length: 10 }, (_, i) => village(i + 1, `Village ${i + 1}`, 40));
  return {
    configured: true,
    estimate: true,
    burn_fraction: 1,
    version: "abc",
    formula: "straw × factor",
    factors: FACTORS,
    group: "village",
    period: "season",
    primary: "pm25",
    season: { from: "2026-09-15", to: "2026-10-20" },
    weeks: ["2026-10-19"],
    district: { label: "Sangrur district", fields: 10, acres: 80, tonnes: 200, impact: { pm25: 400, co2: 200000 }, trend: trend(400) },
    groups,
    ...over,
  };
}

describe("impact units", () => {
  it("shows CO₂ in tonnes and everything else in kg", () => {
    expect(inUnit(20000, "t")).toBe(20);
    expect(impactAmount(20000, "t")).toBe("20 t");
    expect(impactAmount(40, "kg")).toBe("40 kg");
  });
  it("builds a headline only from pollutants that have a factor", () => {
    expect(headline({ pm25: 40, co2: 20000 }, FACTORS)).toBe("~40 kg PM2.5");
    expect(headline({ co2: 20000 }, FACTORS)).toBe("~20 t CO₂");
    expect(headline({ pm25: 40 }, {})).toBeNull();
    expect(headline(null, FACTORS)).toBeNull();
    expect(headline({ pm25: 40 }, undefined)).toBeNull();
  });
});

describe("Sparkline", () => {
  it("renders a labelled trend line", () => {
    render(<Sparkline points={trend(40)} from="2026-09-15" to="2026-10-20" label="Testpur: 40 kg PM2.5 avoided so far" />);
    const svg = screen.getByRole("img", { name: "Testpur: 40 kg PM2.5 avoided so far" });
    expect(svg.querySelectorAll("path")).toHaveLength(2); // filled area + step line
    expect(svg.querySelector("circle")).not.toBeNull();
  });
  it("shows a dash when there is nothing to plot", () => {
    render(<Sparkline points={[]} from="2026-09-15" to="2026-10-20" label="Empty" />);
    expect(screen.getByLabelText("Empty: no data")).toHaveTextContent("–");
  });
});

describe("ImpactTable", () => {
  it("shows the district total, one column per pollutant and the formula pill", () => {
    render(<ImpactTable data={table()} />);
    expect(screen.getByRole("columnheader", { name: "PM2.5 (kg)" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "CO₂ (t)" })).toBeInTheDocument();
    const district = screen.getByText("Sangrur district").closest("tr")!;
    expect(within(district).getByText("400 kg")).toBeInTheDocument();
    expect(within(district).getByText("200 t")).toBeInTheDocument();
    const pill = within(district).getByText(/200 t straw × PM2.5 factor/);
    expect(pill).toHaveAttribute("title", expect.stringContaining("Source: TEST VALUE"));
  });

  it("groups by village and expands a group with the keyboard-accessible button", () => {
    render(<ImpactTable data={table()} />);
    expect(screen.queryByText("Farmer 1.")).not.toBeInTheDocument(); // collapsed by default
    const toggle = screen.getByRole("button", { name: "Village 1: show 1 cleared field" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(screen.getByRole("button", { name: "Village 1: hide 1 cleared field" })).toHaveAttribute("aria-expanded", "true");
    const row = screen.getByText("Farmer 1.").closest("tr")!;
    expect(within(row).getByText("20 Oct")).toBeInTheDocument();
    expect(within(row).getByText("40 kg")).toBeInTheDocument();
    expect(within(row).getByRole("img", { name: /Farmer 1\.: 40 kg PM2\.5 avoided so far \(estimate\)/ })).toBeInTheDocument();
  });

  it("paginates by village", () => {
    render(<ImpactTable data={table()} />);
    expect(screen.getByText("Village 8")).toBeInTheDocument();
    expect(screen.queryByText("Village 9")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Show 2 more villages" }));
    expect(screen.getByText("Village 10")).toBeInTheDocument();
  });

  it("switches to one column per week", () => {
    render(<ImpactTable data={table({ period: "week" })} mode="week" />);
    expect(screen.getByRole("columnheader", { name: "Week of 19 Oct" })).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "CO₂ (t)" })).not.toBeInTheDocument();
  });

  it("renders nothing when no sourced factor is configured", () => {
    const { container } = render(<ImpactTable data={table({ factors: {}, primary: null, configured: false })} />);
    expect(container).toBeEmptyDOMElement();
  });
});
