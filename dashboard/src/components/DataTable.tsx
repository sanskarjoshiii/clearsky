import type { ReactNode } from "react";
import { cx, Empty, Skeleton } from "./ui";

export interface Column<T> {
  key: string;
  header: ReactNode;
  render: (row: T) => ReactNode;
  align?: "left" | "right";
  className?: string;
}

/** Dense data table (reference "database" view): 36px header, 40px rows, hairline grid. */
export function DataTable<T>({
  rows,
  columns,
  rowKey,
  onRowClick,
  selectedKey,
  loading,
  empty,
  numbered,
}: {
  rows: T[] | undefined;
  columns: Column<T>[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string | null;
  loading?: boolean;
  empty?: ReactNode;
  numbered?: boolean;
}) {
  if (loading && !rows) {
    return (
      <div className="space-y-2 p-4">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-8" />
        ))}
      </div>
    );
  }
  if (!rows?.length) return <>{empty ?? <Empty title="Nothing here yet" />}</>;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-collapse text-[13px]">
        <thead className="sticky top-0 z-10 bg-canvas">
          <tr className="h-9 border-b border-line text-left text-muted">
            {numbered ? <th className="w-10 border-r border-line px-3 font-normal" aria-label="Row" /> : null}
            {columns.map((c) => (
              <th
                key={c.key}
                scope="col"
                className={cx("whitespace-nowrap border-r border-line px-3 font-normal last:border-r-0", c.align === "right" && "text-right", c.className)}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const key = rowKey(row);
            return (
              <tr
                key={key}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={onRowClick ? (e) => (e.key === "Enter" || e.key === " ") && onRowClick(row) : undefined}
                tabIndex={onRowClick ? 0 : undefined}
                className={cx(
                  "h-10 border-b border-line text-ink",
                  onRowClick && "cursor-pointer hover:bg-hover focus:bg-hover focus:outline-none",
                  selectedKey === key && "bg-agent-soft/50",
                )}
              >
                {numbered ? <td className="border-r border-line px-3 text-faint tabular">{i + 1}</td> : null}
                {columns.map((c) => (
                  <td key={c.key} className={cx("whitespace-nowrap border-r border-line px-3 last:border-r-0", c.align === "right" && "text-right tabular", c.className)}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
