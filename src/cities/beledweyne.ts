import type { CityConfig } from './types'

export const beledweyne: CityConfig = {
  slug: 'beledweyne',
  label: 'Beledweyne',
  urbanName: 'Belet Weyne',
  region: 'Hiraan',
  center: [45.204, 4.736],
  zoom: 12,
  minZoom: 10,
  bounds: [
    [45.164, 4.7],
    [45.272, 4.785],
  ],
  layers: [
    {
      id: 'flood',
      label: 'Flood extent',
      group: 'hazard',
      defaultOn: true,
      legend: [{ color: '#2563eb', label: 'Ever flooded' }],
    },
    {
      id: 'buildings',
      label: 'Buildings',
      group: 'exposure',
      defaultOn: true,
      legend: [
        { color: '#dc2626', label: 'In flood' },
        { color: '#a8a29e', label: 'Outside' },
      ],
    },
    {
      id: 'idps',
      label: 'IDP / host sites',
      group: 'exposure',
      defaultOn: true,
      legend: [
        { color: '#c026d3', label: 'In flood' },
        { color: '#7c3aed', label: 'Outside' },
      ],
    },
    {
      id: 'roads',
      label: 'OSM roads',
      group: 'infrastructure',
      defaultOn: true,
      legend: [
        { color: '#b45309', label: 'In flood' },
        { color: '#57534e', label: 'Outside' },
      ],
    },
    {
      id: 'river',
      label: 'Shabelle river',
      group: 'infrastructure',
      defaultOn: true,
      legend: [{ color: '#0284c7', label: 'River centreline' }],
    },
    {
      id: 'boundary',
      label: 'City boundary',
      group: 'infrastructure',
      defaultOn: true,
      legend: [{ color: '#0f172a', label: 'Urban extent' }],
    },
    {
      id: 'projectRoads',
      label: 'Nagaad roads',
      group: 'investment',
      defaultOn: true,
      legend: [
        { color: '#059669', label: 'Completed / ongoing' },
        { color: '#7c3aed', label: 'Design ready' },
      ],
    },
    {
      id: 'projectSites',
      label: 'Nagaad sites',
      group: 'investment',
      defaultOn: true,
      legend: [{ color: '#047857', label: 'Office / buildings' }],
    },
    {
      id: 'facilities',
      label: 'Facilities',
      group: 'services',
      defaultOn: false,
      legend: [
        { color: '#1d4ed8', label: 'Hospital' },
        { color: '#7c3aed', label: 'School / university' },
        { color: '#d97706', label: 'Market' },
      ],
    },
  ],
}
