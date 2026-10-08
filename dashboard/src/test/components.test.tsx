import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { FieldRow } from "../api/types";
import { DataTable } from "../components/DataTable";
import { KpiStrip, RiskPill, Segmented, Toggle } from "../components/ui";
import { addDays, daysBetween, fmtDay, fmtInr, fmtNum, initials } from "../lib/format";

describe("format", () => {
  it("formats calendar dates without timezone drift", () => {
    expect(fmtDay("2026-10-25")).toBe("25 Oct");
    expect(fmtDay(null)).toBe("–");
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(daysBetween("2026-10-20", "2026-10-25")).toBe(5);
  });
  it("uses Indian digit grouping", () => {
    expect(fmtInr(2860000)).toBe("₹28,60,000");
    expect(fmtNum(2.25)).toBe("2.3");
    expect(initials("Gurdeep Grewal")).toBe("GG");
  });
});

describe("KpiStrip", () => {
  it("renders every metric with its label and value", () => {
    render(<KpiStrip items={[{ label: "Acres booked", value: "1,234", hint: "56 bookings" }, { label: "Red fields", value: 7 }]} />);
    expect(screen.getByText("Acres booked")).toBeInTheDocument();
    expect(screen.getByText("1,234")).toBeInTheDocument();
    expect(screen.getByText("56 bookings")).toBeInTheDocument();
    expect(screen.getByText("7")).toBeInTheDocument();
  });
});

describe("RiskPill (risk legend)", () => {
  it("names the level in words, not only colour", () => {
    render(
      <>
        <RiskPill level="RED" score={72} />
        <RiskPill level="YELLOW" />
        <RiskPill level="GREEN" />
      </>,
    );
    expect(screen.getByText("Red")).toBeInTheDocument();
    expect(screen.getByText("72")).toBeInTheDocument();
    expect(screen.getByText("Amber")).toBeInTheDocument();
    expect(screen.getByText("Green")).toBeInTheDocument();
  });
});

describe("controls", () => {
  it("Toggle reports the new value and is a switch", () => {
    const onChange = vi.fn();
    render(<Toggle checked={false} onChange={onChange} label="Available" />);
    fireEvent.click(screen.getByRole("switch", { name: "Available" }));
    expect(onChange).toHaveBeenCalledWith(true);
  });
  it("Segmented selects an option", () => {
    const onChange = vi.fn();
    render(<Segmented value="a" onChange={onChange} options={[{ value: "a", label: "All" }, { value: "b", label: "Booked" }]} />);
    expect(screen.getByRole("tab", { name: "All" })).toHaveAttribute("aria-selected", "true");
    fireEvent.click(screen.getByRole("tab", { name: "Booked" }));
    expect(onChange).toHaveBeenCalledWith("b");
  });
});

describe("DataTable", () => {
  const row = (id: string, name: string): Pick<FieldRow, "field_id" | "farmer_name"> => ({ field_id: id, farmer_name: name });
  it("renders rows, numbers them, and is keyboard clickable", () => {
    const onRowClick = vi.fn();
    render(
      <DataTable
        numbered
        rows={[row("F1", "Gurpreet"), row("F2", "Harjit")]}
        rowKey={(r) => r.field_id}
        onRowClick={onRowClick}
        columns={[{ key: "n", header: "Farmer", render: (r) => r.farmer_name }]}
      />,
    );
    expect(screen.getByText("Harjit")).toBeInTheDocument();
    const harjitRow = screen.getByText("Harjit").closest("tr")!;
    fireEvent.keyDown(harjitRow, { key: "Enter" });
    expect(onRowClick).toHaveBeenCalledWith(row("F2", "Harjit"));
  });
  it("shows the empty state", () => {
    render(<DataTable rows={[]} rowKey={() => "x"} columns={[]} empty={<p>No stops</p>} />);
    expect(screen.getByText("No stops")).toBeInTheDocument();
  });
});
