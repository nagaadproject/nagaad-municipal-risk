# Nagaad Municipal Risk Dashboard

Standalone, city-scoped flood dashboard (Beledweyne first). This version is a **historical flood extent** overlay, not a probabilistic risk model. Other hazards (conflict, etc.) are out of scope. It is meant to be **embedded** in the Nagaad MIS Municipal Risk page (`/portal/risk?city=Beledweyne`).

## Stack

- Vite + React + TypeScript + Tailwind
- MapLibre GL JS, PMTiles, Esri World Light Gray basemap (no API key)
- Docker ETL (GDAL/GeoPandas + tippecanoe)
- GitHub Pages is a possible host — **consult internally before publishing** (IDP coordinates and population are sensitive)

## Run locally (dashboard only)

Processed Beledweyne layers are already in `public/data/beledweyne/`. You do **not** need Docker or the raw GIS folder just to open the map.

Need **Node.js 22+** (or current LTS). In PowerShell from this repo:

```powershell
npm install
npm run dev
```

Vite prints the URL. If 5173 is busy it uses 5174, 5175, and so on. Then open:

- Standalone: http://localhost:5173/beledweyne
- MIS embed chrome: http://localhost:5173/beledweyne?embed=1

If those data files were missing, the UI still loads and shows an empty-data banner.

## Process Beledweyne data (only if you re-run GIS)

Raw GIS is **not** in this repo (~5.9 GB). Docker must be running. Point it at the local folder:

```powershell
copy .env.example .env
# .env already points at:
# D:/Municipal Risk Dashboards/DATA/risk_dashboard/beledweyne_data

npm run etl
```

This clips the Belet Weyne urban polygon, intersects buildings / OSM roads / Nagaad project roads / IDP sites with the historical flood mask, writes GeoJSON + `summary.json`, and builds PMTiles.

Converted reusable geofiles (GPKG → GeoJSON, KML/KMZ → GeoJSON, OSM roads kept separate from Nagaad roads) are stored in `converted/beledweyne/`. How each format was converted is documented in [`docs/conversions.md`](docs/conversions.md).

`public/data/beledweyne/facilities.geojson` is an empty layer ready for hospitals, schools/universities, and markets.

## Publish

Do not put a public URL in MIS until PIU / IM have classified IDP, buildings, flood, and Nagaad design-ready roads (see `docs/Nagaad_Municipal_Risk_Technical_Follow_Up.docx`).

If hosting is approved:

1. Create a GitHub repo named `nagaad-municipal-risk` (nagaadproject org).
2. Enable Pages (GitHub Actions source). The workflow in `.github/workflows/pages.yml` deploys on push to `main`.
3. Embed URL (example): `https://nagaadproject.github.io/nagaad-municipal-risk/beledweyne?embed=1`
4. In Nagaad MIS Admin → Municipal Risk, add that URL with city **Beledweyne**.

## Docs

- [`docs/Nagaad_Municipal_Risk_Technical_Follow_Up.docx`](docs/Nagaad_Municipal_Risk_Technical_Follow_Up.docx) — follow-up to the analysis team (data request, IDP label, GitHub Pages)
- [`docs/Nagaad_Municipal_Risk_Dashboard_Process.docx`](docs/Nagaad_Municipal_Risk_Dashboard_Process.docx) — how the ETL was run
- [`docs/Nagaad_Municipal_Risk_Dashboard_Briefing.pptx`](docs/Nagaad_Municipal_Risk_Dashboard_Briefing.pptx) — purpose and architecture
- [`docs/conversions.md`](docs/conversions.md) — format conversions

## Disclaimer

Figures are an **indicative overlay** from historical flood extent and available exposure layers. They are not a full probabilistic risk model.
