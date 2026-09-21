import type { CitySummary } from '../cities/types'
import { formatHa, formatInt, formatKm } from '../lib/data'

interface KpiStripProps {
  summary: CitySummary | null
  embed: boolean
}

export function KpiStrip({ summary, embed }: KpiStripProps) {
  const osmInFlood = summary?.osmRoadsKmInFlood ?? summary?.roadsKmInFlood
  const osmTotal = summary?.osmRoadsKmTotal ?? summary?.roadsKmTotal
  const projectInFlood = summary?.projectRoadsKmInFlood
  const projectTotal = summary?.projectRoadsKmTotal

  const items = [
    {
      label: 'Flood area',
      value: summary ? formatHa(summary.floodAreaHa) : '—',
      hint: summary ? 'Historical extent in the city' : 'Run ETL to populate',
    },
    {
      label: 'Buildings in flood',
      value: summary ? formatInt(summary.buildingsInFlood) : '—',
      hint: summary ? `of ${formatInt(summary.buildingsTotal)} footprints` : 'Intersected footprints',
    },
    {
      label: 'IDP people exposed',
      value: summary ? formatInt(summary.idpIndividualsInFlood) : '—',
      hint: summary
        ? `${formatInt(summary.idpSitesInFlood)} of ${formatInt(summary.idpSitesTotal)} sites`
        : 'Sites intersecting flood',
    },
    {
      label: 'OSM roads in flood',
      value: summary && osmInFlood != null ? formatKm(osmInFlood) : '—',
      hint: summary && osmTotal != null ? `of ${formatKm(osmTotal)} mapped` : 'OpenStreetMap network',
    },
    {
      label: 'Nagaad roads in flood',
      value: summary && projectInFlood != null ? formatKm(projectInFlood) : '—',
      hint:
        summary && projectTotal != null
          ? `of ${formatKm(projectTotal)} invested / designed`
          : 'Completed, ongoing, design-ready',
    },
  ]

  return (
    <div className={`grid shrink-0 grid-cols-5 ${embed ? 'gap-1' : 'gap-3'}`}>
      {items.map((item) => (
        <div
          key={item.label}
          className={`min-w-0 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm ${
            embed ? 'px-2 py-1' : 'px-3 py-2'
          }`}
          title={`${item.label}: ${item.value} — ${item.hint}`}
        >
          <div className="truncate text-[9px] font-medium uppercase leading-none tracking-wide text-slate-500">
            {item.label}
          </div>
          <div
            className={`truncate font-semibold leading-tight text-slate-900 ${embed ? 'text-sm' : 'text-2xl'}`}
          >
            {item.value}
          </div>
          <div className="truncate text-[9px] leading-none text-slate-500">{item.hint}</div>
        </div>
      ))}
    </div>
  )
}
