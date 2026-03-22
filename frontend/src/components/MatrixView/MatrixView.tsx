/**
 * Generic scrollable matrix grid shell — FR-4.6.1, FR-4.6.2
 *
 * Props: rowLabels, colLabels, cells (row, col, value, color), title
 * Renders as a sticky-header table with color-coded cells.
 * Uses overflow-scroll for large matrices.
 */
import type { MatrixCell } from '../../types'

interface Props {
  title?: string
  rowLabels: string[]
  colLabels: string[]
  cells: MatrixCell[]
  isLoading?: boolean
}

export default function MatrixView({ title, rowLabels, colLabels, cells, isLoading }: Props) {
  // Build a fast lookup: row → col → cell
  const cellMap = new Map<string, MatrixCell>()
  for (const cell of cells) {
    cellMap.set(`${cell.row}::${cell.col}`, cell)
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        Loading…
      </div>
    )
  }

  if (rowLabels.length === 0 || colLabels.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-muted-foreground text-sm">
        No data available for this matrix.
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {title && (
        <div className="px-4 py-2 border-b border-border bg-card shrink-0">
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        </div>
      )}
      {/* Scrollable matrix */}
      <div className="flex-1 overflow-auto">
        <table className="border-collapse text-xs min-w-max">
          <thead>
            <tr className="sticky top-0 z-10 bg-card">
              {/* Corner cell */}
              <th className="sticky left-0 z-20 bg-card border border-border px-3 py-2 text-left font-medium text-muted-foreground min-w-[140px]">
                &nbsp;
              </th>
              {colLabels.map((col) => (
                <th
                  key={col}
                  className="border border-border px-2 py-2 font-medium text-foreground whitespace-nowrap min-w-[80px] text-center"
                >
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rowLabels.map((row) => (
              <tr key={row} className="hover:bg-accent/40">
                <td className="sticky left-0 bg-card border border-border px-3 py-2 font-medium text-foreground whitespace-nowrap z-10">
                  {row}
                </td>
                {colLabels.map((col) => {
                  const cell = cellMap.get(`${row}::${col}`)
                  const val = cell?.value ?? ''
                  const color = cell?.color ?? 'hsl(var(--muted))'
                  return (
                    <td
                      key={col}
                      className="border border-border text-center px-2 py-2"
                      title={`${row} × ${col}: ${val}`}
                    >
                      <span
                        className="inline-block rounded px-2 py-0.5 text-white text-xs font-medium min-w-[48px] text-center"
                        style={{ backgroundColor: color }}
                      >
                        {typeof val === 'number' && val % 1 !== 0
                          ? (val as number).toFixed(2)
                          : String(val)}
                      </span>
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
