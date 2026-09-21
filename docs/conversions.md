# Data conversion notes (Beledweyne)

This dashboard version is **flood screening only**. Conflict and other hazards are not converted or shown. Reusable converted geofiles live in [`converted/beledweyne/`](../converted/beledweyne/). Dashboard copies used by the map live in `public/data/beledweyne/`. Raw GIS stays outside the repo at `D:\Municipal Risk Dashboards\DATA\risk_dashboard\beledweyne_data` and is **read-only** during ETL.

Re-run conversions with `npm run etl` (Docker). The live script is `etl/process.py`. A machine-readable log is written to `converted/beledweyne/conversion-log.json`.

## Why convert

| Source | Format | Problem | Converted form |
| --- | --- | --- | --- |
| SURP-II completed / ongoing | GeoPackage (`.gpkg`) | Fine for QGIS, not for the web map | WGS84 GeoJSON + combined GPKG |
| Design Ready Investments | KML / KMZ | Google Earth format, extra chrome fields, mixed names | Same schema as GPKG roads, WGS84 GeoJSON |
| OSM / SURP city roads | Shapefile or pre-joined GeoJSON | Mixed with project roads in the old dashboard | Separate `osm_roads.geojson` + `roads.pmtiles` |
| Buildings | Shapefile (~large) | Too big for GeoJSON in the browser | PMTiles only (`buildings.pmtiles`) |
| Flood mask | Shapefile | Needs clip + simplify | PMTiles (`flood.pmtiles`, z0–z14) |
| Hospitals / schools / markets | Not collected yet | Need a stable schema | Empty `facilities.geojson` + `facilities.schema.json` |

All vector outputs use **EPSG:4326 (WGS84)**. Lengths and areas are computed in **EPSG:32638 (UTM 38N)** then stored as `lengthKm` / hectares.

## Tools

- **GeoPandas + pyogrio** (GDAL/OGR) to read GPKG, KML, KMZ, shapefile, GeoJSON
- **Shapely** to drop Z, polygonize the office outline, clip and overlay
- **tippecanoe** for PMTiles of flood, buildings, and the OSM road network
- Nagaad project roads stay as GeoJSON (small: a handful of lines)

## SURP-II completed and ongoing (GeoPackage)

Folder: `SURP-II Investments completed and ongoing`

| File | Layer | Geometry | Category | Status |
| --- | --- | --- | --- | --- |
| Construction of Beledweyne PIU office and Lab.gpkg | `construction_of_beledweyne_piu_office_and_lab` | MultiLineString (building outline) | Buildings | Completed |
| Irrid Amin Road IB (3km).gpkg | `irrid_amin_road_ib_3km` | MultiLineString | Roads | Ongoing |
| Inner Ring Road (3.25km).gpkg | `inner_ring_road_325km` | MultiLineString | Roads | Ongoing |
| Sheikh Hassan Barsane Road (3km).gpkg | `sheikh_hassan_barsane_road_3km` | MultiLineString | Roads | Ongoing |

Process:

1. Read every `.gpkg` layer with GeoPandas (`gpd.read_file`, CRS already EPSG:4326).
2. Keep `subproject_name`, `package_name`, `category`, `status`, `length_km`.
3. Drop Z coordinates.
4. If `category` is Buildings or the name contains “office”, treat as a **project site**. Closed line rings are polygonized; otherwise the line is kept.
5. Remaining features are **Nagaad project roads**. `lengthKm` uses the source `length_km` when it is a positive number, otherwise UTM length.
6. Write one GeoJSON per source under `converted/beledweyne/sources/`.

## Design Ready Investments (KML / KMZ)

Folder: `Design Ready Investments`

KML is XML in WGS84. KMZ is a zip that contains `doc.kml`. One file is named `.kmz.kml` (already unzipped KML); it is read as KML.

Process:

1. Read with the OGR KML driver (same GeoPandas path as GPKG).
2. Use `Name` as the feature name. If `Name` is generic (for example `Propose`), fall back to the file stem.
3. Strip KML fields that are not useful (`timestamp`, `tessellate`, `extrude`, `visibility`, `drawOrder`, `icon`, `altitudeMode`).
4. Set `status = Design ready`, `stage = design_ready`. Category is `Bridge` when the name/filename contains “bridge”, otherwise `Roads`.
5. Collapse Road #11 (five LineStrings in one KML) to five features, same package.
6. Write per-source GeoJSON, then merge into `project_roads.geojson`.

## OSM vs Nagaad flood analysis

These are **not mixed** in KPIs or layers:

1. **OSM road network** — clip (or use the existing decision-making GeoJSON), join to the historical flood mask, measure flooded length by overlay intersection. Output: `converted/beledweyne/osm_roads.geojson` and `public/data/beledweyne/roads.pmtiles`. Property `network=osm`.
2. **Nagaad project roads** — completed, ongoing, and design-ready lines only. Same flood overlay, separate kilometre totals. Output: `project_roads.geojson`. Property `network=nagaad`.
3. **Nagaad project sites** — PIU office / lab. Flood flag by intersection, not length.

`summary.json` fields:

- `osmRoadsKmTotal` / `osmRoadsKmInFlood` (also copied to the older `roadsKmTotal` / `roadsKmInFlood` keys)
- `projectRoadsKmTotal` / `projectRoadsKmInFlood`
- `projectRoadsCount` / `projectRoadsInFloodCount`
- `projectSitesTotal` / `projectSitesInFlood`

## Future facilities

`converted/beledweyne/facilities.geojson` is an empty FeatureCollection. Add **Point** features with:

| Field | Values |
| --- | --- |
| `name` | Facility name |
| `type` | `hospital` \| `school` \| `university` \| `market` |
| `status` | optional |
| `source` | optional (who collected it) |
| `inFlood` | `0` or `1` (ETL can recompute on the next run) |

JSON Schema: `converted/beledweyne/facilities.schema.json`. The dashboard layer is off by default until points exist.

To add facilities later: edit `converted/beledweyne/facilities.geojson` (or a shapefile/GPKG you convert the same way), copy into `public/data/beledweyne/facilities.geojson`, or re-run ETL after placing a source file in the raw folder (ETL currently writes the empty template each run — if you collect data, we should point it at a real source file so it is not overwritten).

## Output layout

```
converted/beledweyne/
  sources/                     per-input GeoJSON (correction / reuse)
  osm_roads.geojson            city OSM network + inFlood
  project_roads.geojson        Nagaad roads + inFlood
  project_sites.geojson        Nagaad office/buildings
  facilities.geojson           empty, ready for points
  facilities.schema.json
  beledweyne_nagaad_assets.gpkg
  conversion-log.json
  summary.json

public/data/beledweyne/        dashboard copies (GeoJSON + PMTiles)
```

Do not write converted files into the raw data folder. That tree is a read-only bind in Docker.

## Correcting a geometry

1. Edit the per-source GeoJSON under `converted/beledweyne/sources/` or the original GPKG/KML.
2. If you edit sources only, merge them back into `project_roads.geojson` / `project_sites.geojson` (or re-run ETL from the originals).
3. Copy the combined files into `public/data/beledweyne/` if you skip a full ETL.
4. Refresh the local dashboard.
