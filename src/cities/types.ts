export type LayerGroup = 'hazard' | 'exposure' | 'infrastructure' | 'investment' | 'services'

export interface LegendItem {
  color: string
  label: string
}

export interface LayerDef {
  id: string
  label: string
  group: LayerGroup
  defaultOn: boolean
  legend: LegendItem[]
}

export interface CityConfig {
  slug: string
  label: string
  urbanName: string
  region: string
  center: [number, number]
  zoom: number
  minZoom?: number
  /** Southwest and northeast corners [lng, lat], used to fit the city in embed views. */
  bounds?: [[number, number], [number, number]]
  layers: LayerDef[]
}

export interface CitySummary {
  city: string
  urbanName: string
  generatedAt: string
  buildingsTotal: number
  buildingsInFlood: number
  idpSitesTotal: number
  idpSitesInFlood: number
  idpIndividualsTotal: number
  idpIndividualsInFlood: number
  idpHouseholdsInFlood: number
  roadsKmTotal: number
  roadsKmInFlood: number
  osmRoadsKmTotal?: number
  osmRoadsKmInFlood?: number
  projectRoadsKmTotal?: number
  projectRoadsKmInFlood?: number
  projectRoadsCount?: number
  projectRoadsInFloodCount?: number
  projectSitesTotal?: number
  projectSitesInFlood?: number
  facilitiesTotal?: number
  floodAreaHa: number
}

export interface IdpSite {
  name: string
  class: string
  individuals: number
  households: number
  inFlood: boolean
  lng: number
  lat: number
}
