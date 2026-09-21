import type { IdpSite } from '../cities/types'
import { formatInt } from '../lib/data'

interface PriorityTableProps {
  sites: IdpSite[]
  onSelect: (site: IdpSite) => void
}

export function PriorityTable({ sites, onSelect }: PriorityTableProps) {
  const rows = sites
    .filter((s) => s.inFlood && s.individuals > 0)
    .sort((a, b) => b.individuals - a.individuals)

  return (
    <section className="flex min-h-0 flex-1 flex-col border-t border-slate-100">
      <div className="flex shrink-0 items-baseline justify-between gap-2 px-2.5 py-1.5">
        <h2 className="text-xs font-semibold text-slate-900">IDP sites</h2>
        <p className="truncate text-[10px] text-slate-500">
          {rows.length} in flood · sorted by population
        </p>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 ? (
          <p className="px-2.5 py-3 text-xs text-slate-500">No exposed IDP sites in the processed data.</p>
        ) : (
          <table className="w-full table-fixed text-left text-[11px]">
            <thead className="sticky top-0 bg-slate-50 text-[9px] uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-2.5 py-1 font-medium">Site</th>
                <th className="w-14 px-1 py-1 font-medium">People</th>
                <th className="w-9 px-2 py-1 font-medium">HH</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((site) => (
                <tr
                  key={`${site.name}-${site.lng}`}
                  className="cursor-pointer border-t border-slate-100 hover:bg-sky-50"
                  tabIndex={0}
                  onClick={() => onSelect(site)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter' || event.key === ' ') {
                      event.preventDefault()
                      onSelect(site)
                    }
                  }}
                >
                  <td className="truncate px-2.5 py-1 font-medium text-slate-800" title={site.name}>
                    {site.name}
                  </td>
                  <td className="px-1 py-1 tabular-nums text-slate-800">{formatInt(site.individuals)}</td>
                  <td className="px-2 py-1 tabular-nums text-slate-600">{formatInt(site.households)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}
