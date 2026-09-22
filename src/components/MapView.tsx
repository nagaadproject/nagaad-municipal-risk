import { useEffect, useRef, useState, useImperativeHandle, forwardRef } from 'react'
import {
  Map as MapLibreMap,
  NavigationControl,
  Popup,
  ScaleControl,
  addProtocol,
  setWorkerUrl,
  type LngLatBoundsLike,
  type MapLayerMouseEvent,
  type StyleSpecification,
} from 'maplibre-gl'
import { Protocol } from 'pmtiles'
import type { CityConfig } from '../cities/types'
import { dataUrl, pmtilesUrl } from '../lib/data'

const viteBase = import.meta.env.BASE_URL.endsWith('/')
  ? import.meta.env.BASE_URL
  : `${import.meta.env.BASE_URL}/`
setWorkerUrl(`${viteBase}maplibre/maplibre-gl-worker.mjs`)

let protocolRegistered = false

function ensurePmtilesProtocol() {
  if (protocolRegistered) return
  const protocol = new Protocol({ metadata: true })
  addProtocol('pmtiles', (request, abortController) => protocol.tilev4(request, abortController))
  protocolRegistered = true
}

async function loadGeoJsonFile(slug: string, file: string) {
  const res = await fetch(absDataUrl(slug, file))
  if (!res.ok) return { type: 'FeatureCollection', features: [] }
  const json = (await res.json()) as Record<string, unknown>
  delete json.crs
  if (json.type !== 'FeatureCollection' || !Array.isArray(json.features)) {
    return { type: 'FeatureCollection', features: [] }
  }
  return json
}

function absDataUrl(slug: string, file: string) {
  return new URL(dataUrl(slug, file), window.location.href).href
}

type BasemapId = 'map' | 'satellite'

const BASEMAPS: Record<
  BasemapId,
  { layerId: string; sourceId: string; label: string }
> = {
  map: { layerId: 'esri-map', sourceId: 'esri-map', label: 'Map' },
  satellite: { layerId: 'esri-satellite', sourceId: 'esri-satellite', label: 'Satellite' },
}

const BASEMAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    'esri-map': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: 'Tiles © Esri — Esri, HERE, Garmin, FAO, NOAA, USGS',
      maxzoom: 16,
    },
    'esri-satellite': {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: 'Tiles © Esri — Source: Esri, Maxar, Earthstar Geographics',
      maxzoom: 19,
    },
  },
  layers: [
    { id: 'esri-map', type: 'raster', source: 'esri-map' },
    {
      id: 'esri-satellite',
      type: 'raster',
      source: 'esri-satellite',
      layout: { visibility: 'none' },
    },
  ],
}

function applyBasemap(map: MapLibreMap, basemap: BasemapId) {
  for (const id of Object.keys(BASEMAPS) as BasemapId[]) {
    const layerId = BASEMAPS[id].layerId
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, 'visibility', id === basemap ? 'visible' : 'none')
    }
  }
}

const TOP_LAYERS = [
  'projectRoads-line',
  'projectSites-fill',
  'projectSites-line',
  'projectSites-circle',
  'idps-circle',
  'facilities-circle',
]

export interface MapHandle {
  flyTo: (lng: number, lat: number) => void
}

interface MapViewProps {
  city: CityConfig
  layerOn: Record<string, boolean>
}

function popupHtml(title: string, rows: [string, string][]): string {
  const body = rows
    .filter(([, v]) => v && v !== 'undefined' && v !== 'null')
    .map(([k, v]) => `<div><span style="color:#64748b">${k}:</span> ${v}</div>`)
    .join('')
  return `<strong>${title}</strong>${body}`
}

function floodLabel(value: unknown): string {
  return Number(value) === 1 ? 'In flood extent' : 'Outside'
}

export const MapView = forwardRef<MapHandle, MapViewProps>(function MapView(
  { city, layerOn },
  ref,
) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<MapLibreMap | null>(null)
  const popupRef = useRef<Popup | null>(null)
  const readyRef = useRef(false)
  const userMovedRef = useRef(false)
  const [basemap, setBasemap] = useState<BasemapId>('map')
  const basemapRef = useRef(basemap)
  basemapRef.current = basemap

  useImperativeHandle(ref, () => ({
    flyTo(lng: number, lat: number) {
      userMovedRef.current = true
      mapRef.current?.flyTo({ center: [lng, lat], zoom: 16, essential: true })
    },
  }))

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    ensurePmtilesProtocol()

    const map = new MapLibreMap({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: city.center,
      zoom: city.zoom,
      minZoom: city.minZoom ?? 10,
      attributionControl: { compact: true },
    })
    map.addControl(new NavigationControl({ visualizePitch: false, showCompass: false }), 'top-right')
    map.addControl(new ScaleControl({ maxWidth: 80 }), 'bottom-left')

    userMovedRef.current = false
    const markUserMoved = () => {
      userMovedRef.current = true
    }
    const hasUserMoved = () => userMovedRef.current
    const fitCity = () => {
      if (!city.bounds) return
      map.fitBounds(city.bounds as LngLatBoundsLike, {
        padding: 28,
        maxZoom: 13,
        duration: 0,
      })
    }
    map.on('dragstart', markUserMoved)
    map.on('zoomstart', (event) => {
      if (event.originalEvent) markUserMoved()
    })
    fitCity()
    map.once('load', () => {
      applyBasemap(map, basemapRef.current)
      map.resize()
      if (!hasUserMoved()) fitCity()
    })
    mapRef.current = map
    popupRef.current = new Popup({ closeButton: true, maxWidth: '280px' })
    const ro = new ResizeObserver(() => {
      map.resize()
    })
    ro.observe(containerRef.current)

    const bindClick = (
      layerId: string,
      titleFrom: (p: Record<string, unknown>) => string,
      rowsFrom: (p: Record<string, unknown>) => [string, string][],
    ) => {
      map.on('click', layerId, (e: MapLayerMouseEvent) => {
        const f = e.features?.[0]
        if (!f || !e.lngLat) return
        const p = (f.properties ?? {}) as Record<string, unknown>
        popupRef.current
          ?.setLngLat(e.lngLat)
          .setHTML(popupHtml(titleFrom(p), rowsFrom(p)))
          .addTo(map)
      })
      map.on('mouseenter', layerId, () => {
        map.getCanvas().style.cursor = 'pointer'
      })
      map.on('mouseleave', layerId, () => {
        map.getCanvas().style.cursor = ''
      })
    }

    map.on('error', (e) => {
      console.warn('Map error', e.error ?? e)
    })

    const raiseTopLayers = () => {
      for (const id of TOP_LAYERS) {
        if (map.getLayer(id)) map.moveLayer(id)
      }
    }

    let overlaysStarted = false
    const startOverlays = async () => {
      if (overlaysStarted || !map.isStyleLoaded()) return
      overlaysStarted = true
      const slug = city.slug
      try {
      const [boundary, river, idps, projectRoads, projectSites, facilities] = await Promise.all([
        loadGeoJsonFile(slug, 'boundary.geojson'),
        loadGeoJsonFile(slug, 'river.geojson'),
        loadGeoJsonFile(slug, 'idps.geojson'),
        loadGeoJsonFile(slug, 'project_roads.geojson'),
        loadGeoJsonFile(slug, 'project_sites.geojson'),
        loadGeoJsonFile(slug, 'facilities.geojson'),
      ])
      if (map.getSource('idps')) return
      map.addSource('boundary', { type: 'geojson', data: boundary })
      map.addSource('river', { type: 'geojson', data: river })
      map.addSource('idps', { type: 'geojson', data: idps })
      map.addSource('projectRoads', { type: 'geojson', data: projectRoads })
      map.addSource('projectSites', { type: 'geojson', data: projectSites })
      map.addSource('facilities', { type: 'geojson', data: facilities })

      map.addLayer({
        id: 'river-line',
        type: 'line',
        source: 'river',
        paint: { 'line-color': '#0284c7', 'line-width': 2.4 },
      })
      map.addLayer({
        id: 'boundary-line',
        type: 'line',
        source: 'boundary',
        paint: { 'line-color': '#0f172a', 'line-width': 2, 'line-dasharray': [2, 1] },
      })
      map.addLayer({
        id: 'projectRoads-line',
        type: 'line',
        source: 'projectRoads',
        paint: {
          'line-color': [
            'case',
            [
              'any',
              ['==', ['get', 'stage'], 'completed_ongoing'],
              ['in', ['get', 'status'], ['literal', ['Completed', 'Ongoing']]],
            ],
            '#059669',
            '#7c3aed',
          ],
          'line-width': ['interpolate', ['linear'], ['zoom'], 11, 2.2, 16, 5],
          'line-opacity': 0.95,
        },
      })
      map.addLayer({
        id: 'projectSites-fill',
        type: 'fill',
        source: 'projectSites',
        filter: ['match', ['geometry-type'], ['Polygon', 'MultiPolygon'], true, false],
        paint: { 'fill-color': '#047857', 'fill-opacity': 0.55 },
      })
      map.addLayer({
        id: 'projectSites-line',
        type: 'line',
        source: 'projectSites',
        paint: { 'line-color': '#047857', 'line-width': 2.4 },
      })
      map.addLayer({
        id: 'projectSites-circle',
        type: 'circle',
        source: 'projectSites',
        filter: ['==', ['geometry-type'], 'Point'],
        paint: {
          'circle-radius': 7,
          'circle-color': '#047857',
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#fff',
        },
      })
      map.addLayer({
        id: 'idps-circle',
        type: 'circle',
        source: 'idps',
        paint: {
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['coalesce', ['to-number', ['get', 'idpIndividuals']], 0],
            0,
            4,
            500,
            7,
            2000,
            12,
            6000,
            18,
          ],
          'circle-color': [
            'case',
            ['==', ['to-number', ['get', 'inFlood']], 1],
            '#c026d3',
            '#7c3aed',
          ],
          'circle-stroke-width': 1.2,
          'circle-stroke-color': '#fff',
          'circle-opacity': 0.92,
        },
      })
      map.addLayer({
        id: 'facilities-circle',
        type: 'circle',
        source: 'facilities',
        paint: {
          'circle-radius': 7,
          'circle-color': [
            'match',
            ['get', 'type'],
            'hospital',
            '#1d4ed8',
            'school',
            '#7c3aed',
            'university',
            '#7c3aed',
            'market',
            '#d97706',
            '#334155',
          ],
          'circle-stroke-width': 1.5,
          'circle-stroke-color': '#fff',
        },
      })

      bindClick(
        'idps-circle',
        (p) => String(p.settlementName ?? 'Settlement'),
        (p) => [
          ['Type', String(p.settlementClass ?? '')],
          ['IDP individuals', String(p.idpIndividuals ?? 0)],
          ['Households', String(p.idpHouseholds ?? 0)],
          ['Flood exposure', floodLabel(p.inFlood)],
        ],
      )
      bindClick(
        'projectRoads-line',
        (p) => String(p.name ?? 'Nagaad road'),
        (p) => [
          ['Status', String(p.status ?? '')],
          ['Category', String(p.category ?? '')],
          ['Length', p.lengthKm != null ? `${p.lengthKm} km` : ''],
          ['Flood exposure', floodLabel(p.inFlood)],
        ],
      )
      bindClick(
        'projectSites-fill',
        (p) => String(p.name ?? 'Nagaad site'),
        (p) => [
          ['Status', String(p.status ?? '')],
          ['Category', String(p.category ?? '')],
          ['Flood exposure', floodLabel(p.inFlood)],
        ],
      )
      bindClick(
        'projectSites-line',
        (p) => String(p.name ?? 'Nagaad site'),
        (p) => [
          ['Status', String(p.status ?? '')],
          ['Category', String(p.category ?? '')],
          ['Flood exposure', floodLabel(p.inFlood)],
        ],
      )
      bindClick(
        'facilities-circle',
        (p) => String(p.name ?? 'Facility'),
        (p) => [
          ['Type', String(p.type ?? '')],
          ['Status', String(p.status ?? '')],
          ['Flood exposure', floodLabel(p.inFlood)],
        ],
      )

      map.addSource('flood', {
        type: 'vector',
        url: pmtilesUrl(absDataUrl(slug, 'flood.pmtiles')),
      })
      map.addSource('buildings', {
        type: 'vector',
        url: pmtilesUrl(absDataUrl(slug, 'buildings.pmtiles')),
      })
      map.addSource('roads', {
        type: 'vector',
        url: pmtilesUrl(absDataUrl(slug, 'roads.pmtiles')),
      })

      const addVectorLayers = () => {
        if (map.getLayer('flood-fill')) return
        if (!['flood', 'buildings', 'roads'].every((id) => map.isSourceLoaded(id))) return
        map.addLayer({
          id: 'flood-fill',
          type: 'fill',
          source: 'flood',
          'source-layer': 'flood',
          paint: { 'fill-color': '#2563eb', 'fill-opacity': 0.32 },
        })
        map.addLayer({
          id: 'buildings-fill',
          type: 'fill',
          source: 'buildings',
          'source-layer': 'buildings',
          minzoom: 11,
          paint: {
            'fill-color': ['case', ['==', ['get', 'inFlood'], 1], '#dc2626', '#a8a29e'],
            'fill-opacity': 0.75,
          },
        })
        map.addLayer({
          id: 'buildings-line',
          type: 'line',
          source: 'buildings',
          'source-layer': 'buildings',
          minzoom: 15,
          paint: { 'line-color': '#44403c', 'line-width': 0.4, 'line-opacity': 0.5 },
        })
        map.addLayer({
          id: 'roads-line',
          type: 'line',
          source: 'roads',
          'source-layer': 'roads',
          paint: {
            'line-color': ['case', ['==', ['get', 'inFlood'], 1], '#b45309', '#57534e'],
            'line-width': ['interpolate', ['linear'], ['zoom'], 11, 0.4, 16, 2.2],
            'line-opacity': 0.85,
          },
        })
        bindClick(
          'buildings-fill',
          () => 'Building',
          (p) => [
            ['Flood exposure', floodLabel(p.inFlood)],
            ['Area m²', String(p.areaM2 ?? '')],
          ],
        )
        bindClick(
          'roads-line',
          (p) => String(p.name || p.highway || 'OSM road'),
          (p) => [
            ['Class', String(p.highway ?? '')],
            ['Network', 'OpenStreetMap'],
            ['Flood exposure', floodLabel(p.inFlood)],
          ],
        )
        raiseTopLayers()
        for (const [id, on] of Object.entries(layerOn)) {
          setLayerVisibility(map, id, on)
        }
      }

      map.on('sourcedata', addVectorLayers)
      map.on('idle', addVectorLayers)

      readyRef.current = true
      for (const [id, on] of Object.entries(layerOn)) {
        setLayerVisibility(map, id, on)
      }
      map.resize()
      } catch (err) {
        overlaysStarted = false
        console.warn('Map overlays failed', err)
      }
    }

    if (map.loaded()) startOverlays()
    else map.once('load', startOverlays)
    map.once('idle', startOverlays)

    return () => {
      ro.disconnect()
      map.remove()
      mapRef.current = null
      readyRef.current = false
    }
    // city.slug is the identity of this map instance
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [city.slug])

  useEffect(() => {
    const map = mapRef.current
    if (!map || !readyRef.current) return
    for (const layer of city.layers) {
      setLayerVisibility(map, layer.id, layerOn[layer.id] !== false)
    }
  }, [layerOn, city.layers])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    applyBasemap(map, basemap)
  }, [basemap])

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute left-2 top-2 z-10 flex overflow-hidden rounded border border-slate-200 bg-white text-[11px] font-medium shadow-sm">
        {(Object.keys(BASEMAPS) as BasemapId[]).map((id) => (
          <button
            key={id}
            type="button"
            className={`px-2 py-1 ${
              basemap === id ? 'bg-[#1e4d7b] text-white' : 'bg-white text-slate-700 hover:bg-slate-50'
            }`}
            aria-pressed={basemap === id}
            onClick={() => setBasemap(id)}
          >
            {BASEMAPS[id].label}
          </button>
        ))}
      </div>
    </div>
  )
})

function setLayerVisibility(map: MapLibreMap, id: string, on: boolean) {
  const visibility = on ? 'visible' : 'none'
  const suffixes =
    id === 'buildings' || id === 'projectSites'
      ? ['-fill', '-line', '-circle']
      : id === 'flood'
        ? ['-fill']
        : id === 'roads' || id === 'river' || id === 'boundary' || id === 'projectRoads'
          ? ['-line']
          : ['-circle']
  for (const suffix of suffixes) {
    const layerId = `${id}${suffix}`
    if (map.getLayer(layerId)) {
      map.setLayoutProperty(layerId, 'visibility', visibility)
    }
  }
}
