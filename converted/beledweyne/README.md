# Converted Beledweyne geofiles

This folder stores **WGS84 GeoJSON** (and a QGIS GeoPackage) produced from the mixed SURP-II investment formats, plus the OSM road clip used for flood screening.

Full conversion notes: [`docs/conversions.md`](../../docs/conversions.md).

Machine log after each ETL run: `conversion-log.json`.

| File | Contents |
| --- | --- |
| `sources/` | One GeoJSON per original GPKG/KML/KMZ |
| `osm_roads.geojson` | OSM / city road network, `inFlood` flag, `network=osm` |
| `project_roads.geojson` | Nagaad completed, ongoing, and design-ready roads |
| `project_sites.geojson` | PIU office / lab |
| `facilities.geojson` | Empty points layer for hospitals, schools/universities, markets |
| `facilities.schema.json` | Field list for that layer |
| `beledweyne_nagaad_assets.gpkg` | Same Nagaad layers for QGIS |
| `summary.json` | KPI snapshot including separate OSM vs Nagaad road km |

Raw files stay in `D:\Municipal Risk Dashboards\DATA\risk_dashboard\beledweyne_data`. Re-run `npm run etl` to regenerate this folder.
