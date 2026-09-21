# Nagaad Municipal Risk Dashboard

Standalone, city-scoped flood dashboard (Beledweyne first). This version is a **historical flood extent** overlay, not a probabilistic risk model. Other hazards (conflict, etc.) are out of scope. It is meant to be **embedded** in the Nagaad MIS Municipal Risk page (`/portal/risk?city=Beledweyne`).

ETL scripts, briefing Word/PowerPoint files, and converted GIS working copies stay **on the local machine** (gitignored). GitHub Pages only gets the web app and the layers it loads.

## Stack

- Vite + React + TypeScript + Tailwind
- MapLibre GL JS, PMTiles, Esri World Light Gray basemap (no API key)
- Docker ETL locally (GDAL/GeoPandas + tippecanoe) — not in the public repo
- GitHub Pages host for the MIS iframe

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

## Process Beledweyne data (local only)

Raw GIS is **not** in git (~5.9 GB). `etl/`, `converted/`, and `docs/` are local. Docker must be running:

```powershell
copy .env.example .env
npm run etl
```

This writes the Pages layers into `public/data/beledweyne/` (GeoJSON, PMTiles, `summary.json`).

## Publish

Embed URL:

`https://nagaadproject.github.io/nagaad-municipal-risk/beledweyne?embed=1`

In Nagaad MIS Admin → Municipal Risk, add that URL with city **Beledweyne**.

## Disclaimer

Figures are an **indicative overlay** from historical flood extent and available exposure layers. They are not a full probabilistic risk model.
