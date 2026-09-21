import { useEffect, useMemo, useRef, useState } from 'react'
import type { CityConfig, CitySummary, IdpSite } from '../cities/types'
import { idpSitesFromGeoJSON, loadGeoJSON, loadSummary } from '../lib/data'
import { KpiStrip } from './KpiStrip'
import { LayerPanel } from './LayerPanel'
import { MapView, type MapHandle } from './MapView'
import { PriorityTable } from './PriorityTable'
import { SourcesFooter } from './SourcesFooter'

interface DashboardProps {
  city: CityConfig
  embed: boolean
}

function logoSrc() {
  const base = import.meta.env.BASE_URL.endsWith('/')
    ? import.meta.env.BASE_URL
    : `${import.meta.env.BASE_URL}/`
  return `${base}nagaad-logo.png`
}

export function Dashboard({ city, embed }: DashboardProps) {
  const mapRef = useRef<MapHandle>(null)
  const [summary, setSummary] = useState<CitySummary | null>(null)
  const [sites, setSites] = useState<IdpSite[]>([])
  const [missingData, setMissingData] = useState(false)

  const [layerOn, setLayerOn] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(city.layers.map((l) => [l.id, l.defaultOn])),
  )

  useEffect(() => {
    setLayerOn(Object.fromEntries(city.layers.map((l) => [l.id, l.defaultOn])))
    let cancelled = false
    ;(async () => {
      const [nextSummary, idps] = await Promise.all([
        loadSummary(city.slug),
        loadGeoJSON(city.slug, 'idps.geojson'),
      ])
      if (cancelled) return
      setSummary(nextSummary)
      setSites(idpSitesFromGeoJSON(idps))
      setMissingData(!nextSummary)
    })()
    return () => {
      cancelled = true
    }
  }, [city])

  const layerOnStable = useMemo(() => layerOn, [layerOn])

  return (
    <div className="flex h-dvh max-h-dvh min-h-0 flex-col overflow-hidden bg-slate-100">
      {!embed && (
        <header className="shrink-0 border-b border-slate-200 bg-[#1e4d7b] px-4 py-2.5 text-white">
          <div className="flex items-center gap-3">
            <img
              src={logoSrc()}
              alt="Nagaad — Somalia Urban Resilience Project Phase II"
              className="h-10 w-10 shrink-0 rounded-full bg-white object-contain p-0.5"
            />
            <div>
              <div className="text-[11px] font-medium uppercase tracking-wider text-sky-100">
                Nagaad Municipal Risk Dashboard
              </div>
              <h1 className="text-lg font-semibold leading-tight">
                {city.label}
                <span className="ml-2 text-sm font-normal text-sky-100">
                  {city.region} · historical flood extent
                </span>
              </h1>
            </div>
          </div>
        </header>
      )}
      {embed && (
        <header className="flex h-9 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-2.5">
          <div className="flex min-w-0 items-center gap-2">
            <img src={logoSrc()} alt="Nagaad" className="h-6 w-6 shrink-0 rounded-full bg-white object-contain" />
            <div className="truncate text-sm font-semibold text-slate-900">{city.label}</div>
          </div>
          <div className="shrink-0 text-[10px] text-slate-500">Historical flood extent</div>
        </header>
      )}

      <div
        className={`flex min-h-0 flex-1 flex-col overflow-hidden ${embed ? 'gap-1.5 p-1.5' : 'gap-2 p-3'}`}
      >
        <KpiStrip summary={summary} embed={embed} />
        {missingData && (
          <div className="shrink-0 rounded-md border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs text-amber-900">
            Processed city data is not in this build yet. Run the ETL (see README) to generate GeoJSON,
            PMTiles, and summary.json.
          </div>
        )}
        <div
          className={`grid min-h-0 flex-1 overflow-hidden ${
            embed
              ? 'grid-cols-[minmax(0,1fr)_17.5rem] gap-1.5'
              : 'grid-cols-1 gap-2 lg:grid-cols-[minmax(0,1fr)_20rem]'
          }`}
        >
          <div className="min-h-0 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
            <MapView ref={mapRef} city={city} layerOn={layerOnStable} />
          </div>
          <aside className="flex min-h-0 flex-col overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
            <LayerPanel
              city={city}
              layerOn={layerOn}
              onToggle={(id) => setLayerOn((prev) => ({ ...prev, [id]: !prev[id] }))}
            />
            <PriorityTable
              sites={sites}
              onSelect={(site) => mapRef.current?.flyTo(site.lng, site.lat)}
            />
          </aside>
        </div>
      </div>
      <SourcesFooter generatedAt={summary?.generatedAt} embed={embed} />
    </div>
  )
}
