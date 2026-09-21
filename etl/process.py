#!/usr/bin/env python3
"""Clip Beledweyne layers, convert Nagaad investments, compute flood exposure, write GeoJSON / summary / PMTiles."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import make_valid
from shapely.ops import linemerge, polygonize, transform, unary_union

RAW = Path(os.environ.get("RAW_DATA", "/data/raw"))
OUT = Path(os.environ.get("OUT_DATA", "/data/out"))
CONVERTED = Path(os.environ.get("CONVERTED_DATA", "/data/converted"))
CITY_URBAN = os.environ.get("CITY_URBAN", "Belet Weyne")
CITY_LABEL = os.environ.get("CITY_LABEL", "Beledweyne")
UTM = "EPSG:32638"
WGS84 = "EPSG:4326"


def log(msg: str) -> None:
    print(msg, flush=True)


def read_vector(path: Path, **kwargs):
    if not path.exists():
        raise FileNotFoundError(path)
    gdf = gpd.read_file(path, **kwargs)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    return gdf.to_crs(4326)


def first_col(gdf: gpd.GeoDataFrame, names: list[str]) -> str | None:
    lower = {c.lower(): c for c in gdf.columns}
    for name in names:
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _drop_z_geom(geom):
    if geom is None or geom.is_empty:
        return geom
    if getattr(geom, "has_z", False):
        return transform(lambda *args: args[:2], geom)
    return geom


def drop_z(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.map(_drop_z_geom)
    return gdf


def mark_in_flood(gdf: gpd.GeoDataFrame, flood: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    gdf = gdf.copy()
    if flood.empty or gdf.empty:
        gdf["inFlood"] = 0
        return gdf
    joined = gpd.sjoin(gdf[["geometry"]], flood[["geometry"]], how="left", predicate="intersects")
    hits = joined.loc[joined["index_right"].notna()].index.unique()
    gdf["inFlood"] = gdf.index.isin(hits).astype(int)
    return gdf


def write_geojson(gdf: gpd.GeoDataFrame, path: Path, name: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if gdf is None or gdf.empty:
        payload = {"type": "FeatureCollection", "name": name or path.stem, "features": []}
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        log(f"  wrote {path.name} (0 features)")
        return
    out = drop_z(gdf)
    out.to_file(path, driver="GeoJSON")
    log(f"  wrote {path.name} ({len(out)} features)")


def tippecanoe(src: Path, dest: Path, layer: str, extra: list[str]) -> None:
    dest.unlink(missing_ok=True)
    cmd = [
        "tippecanoe",
        "-o",
        str(dest),
        "-l",
        layer,
        "--force",
        *extra,
        str(src),
    ]
    log("  " + " ".join(cmd))
    subprocess.run(cmd, check=True)


def clean_str(value, default: str = "") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return default
    text = str(value).replace("\n", " ").replace("\r", " ").strip()
    if text.lower() in {"none", "nan", "<na>"}:
        return default
    return re.sub(r"\s+", " ", text)


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:80] or "feature"


def concat_gdfs(frames: list[gpd.GeoDataFrame]) -> gpd.GeoDataFrame:
    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=4326)
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs=4326)


def length_km(gdf: gpd.GeoDataFrame) -> pd.Series:
    if gdf.empty:
        return pd.Series(dtype=float)
    return gdf.to_crs(UTM).geometry.length / 1000.0


def flooded_length_km(lines: gpd.GeoDataFrame, flood: gpd.GeoDataFrame) -> float:
    if lines.empty or flood.empty:
        return 0.0
    try:
        parts = gpd.overlay(lines[["geometry"]], flood[["geometry"]], how="intersection", keep_geom_type=True)
    except Exception:
        parts = gpd.clip(lines, flood)
    if parts.empty:
        return 0.0
    return float(parts.to_crs(UTM).geometry.length.sum() / 1000)


def read_all_layers(path: Path) -> gpd.GeoDataFrame:
    try:
        layers = gpd.list_layers(path)
        names = [str(n) for n in layers["name"].tolist()] if layers is not None and not layers.empty else []
    except Exception:
        names = []
    if not names:
        return drop_z(read_vector(path))
    frames = [drop_z(read_vector(path, layer=name)) for name in names]
    return concat_gdfs(frames)


def lines_to_site_polygon(geom):
    if geom is None or geom.is_empty:
        return geom
    if geom.geom_type in {"Polygon", "MultiPolygon"}:
        return make_valid(geom)
    if geom.geom_type not in {"LineString", "MultiLineString"}:
        return geom
    try:
        merged = linemerge(geom)
        parts = list(polygonize(merged)) or list(polygonize(geom))
        if parts:
            return make_valid(unary_union(parts))
    except Exception:
        return geom
    return geom


def empty_facilities() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "name": pd.Series(dtype=str),
            "type": pd.Series(dtype=str),
            "status": pd.Series(dtype=str),
            "source": pd.Series(dtype=str),
            "inFlood": pd.Series(dtype=int),
            "geometry": gpd.GeoSeries(dtype="geometry"),
        },
        crs=4326,
    )


def investment_files() -> list[tuple[Path, str]]:
    found: list[tuple[Path, str]] = []
    completed = RAW / "SURP-II Investments completed and ongoing"
    design = RAW / "Design Ready Investments"
    if completed.exists():
        for path in sorted(completed.rglob("*.gpkg")):
            found.append((path, "completed_ongoing"))
    if design.exists():
        for path in sorted(design.rglob("*")):
            if path.suffix.lower() in {".kml", ".kmz"}:
                found.append((path, "design_ready"))
    return found


def normalize_investment(path: Path, stage: str) -> tuple[gpd.GeoDataFrame, dict]:
    raw = read_all_layers(path)
    raw = raw[~raw.geometry.isna() & ~raw.geometry.is_empty].copy()
    rel = str(path.relative_to(RAW)).replace("\\", "/")
    source_format = path.suffix.lower().lstrip(".")
    meta = {
        "sourceFile": rel,
        "sourceFormat": source_format,
        "stage": stage,
        "featureCount": int(len(raw)),
        "geometryTypes": sorted({g for g in raw.geometry.geom_type.unique()}) if not raw.empty else [],
        "inputCrs": "EPSG:4326",
    }
    if raw.empty:
        return gpd.GeoDataFrame(geometry=[], crs=4326), meta

    name_col = first_col(raw, ["subproject_name", "Name", "name"])
    status_col = first_col(raw, ["status"])
    category_col = first_col(raw, ["category"])
    package_col = first_col(raw, ["package_name", "package"])
    length_col = first_col(raw, ["length_km"])
    fallback_name = path.stem.replace(".kmz", "").strip()

    rows = []
    for _, feat in raw.iterrows():
        name = clean_str(feat[name_col] if name_col else None, fallback_name)
        status = clean_str(feat[status_col] if status_col else None)
        category = clean_str(feat[category_col] if category_col else None)
        package = clean_str(feat[package_col] if package_col else None, "Beledweyne Investments")
        if stage == "design_ready":
            status = status or "Design ready"
            if not category:
                category = "Bridge" if "bridge" in f"{name} {fallback_name}".lower() else "Roads"
        if not name:
            name = fallback_name
        rows.append(
            {
                "name": name,
                "status": status or ("Ongoing" if stage == "completed_ongoing" else "Design ready"),
                "category": category or "Roads",
                "packageName": package,
                "stage": stage,
                "network": "nagaad",
                "sourceFile": rel,
                "sourceFormat": source_format,
                "lengthKmSource": pd.to_numeric(feat[length_col], errors="coerce") if length_col else None,
                "geometry": feat.geometry,
            }
        )
    gdf = gpd.GeoDataFrame(rows, crs=4326)
    computed = length_km(gdf)
    gdf["lengthKm"] = computed.to_numpy().round(3)
    src_len = pd.to_numeric(gdf["lengthKmSource"], errors="coerce")
    gdf["lengthKm"] = src_len.where(src_len.notna() & (src_len > 0), gdf["lengthKm"]).round(3)
    gdf = gdf.drop(columns=["lengthKmSource"])
    meta["names"] = sorted({clean_str(n) for n in gdf["name"].tolist() if clean_str(n)})
    return gdf, meta


def process_investments(flood: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, gpd.GeoDataFrame, list[dict]]:
    sources_dir = CONVERTED / "sources"
    sources_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict] = []
    road_parts: list[gpd.GeoDataFrame] = []
    site_parts: list[gpd.GeoDataFrame] = []

    files = investment_files()
    if not files:
        log("WARNING: no SURP-II / Design Ready investment files found")

    for path, stage in files:
        log(f"Converting {path.relative_to(RAW)}…")
        gdf, meta = normalize_investment(path, stage)
        records.append(meta)
        if gdf.empty:
            continue
        is_site = gdf["category"].astype(str).str.lower().isin(["buildings", "building", "office"]) | gdf[
            "name"
        ].astype(str).str.lower().str.contains("office")
        sites = gdf.loc[is_site].copy()
        roads = gdf.loc[~is_site].copy()
        if not sites.empty:
            sites = sites.copy()
            sites["geometry"] = sites.geometry.map(lines_to_site_polygon)
            site_parts.append(sites)
        if not roads.empty:
            road_parts.append(roads)
        write_geojson(gdf, sources_dir / f"{slugify(path.stem)}.geojson", name=path.stem)

    project_roads = concat_gdfs(road_parts)
    project_sites = concat_gdfs(site_parts)
    project_roads = mark_in_flood(project_roads, flood)
    project_sites = mark_in_flood(project_sites, flood)
    if not project_roads.empty:
        project_roads["inFlood"] = project_roads["inFlood"].astype(int)
        project_roads["lengthKm"] = pd.to_numeric(project_roads["lengthKm"], errors="coerce").fillna(0).round(3)
    if not project_sites.empty:
        project_sites["inFlood"] = project_sites["inFlood"].astype(int)

    facilities = empty_facilities()
    existing_facilities = CONVERTED / "facilities.geojson"
    if existing_facilities.exists():
        try:
            prev = read_vector(existing_facilities)
            prev = prev[~prev.geometry.isna() & ~prev.geometry.is_empty]
            if not prev.empty:
                log(f"  keeping {len(prev)} existing facilities from {existing_facilities.name}")
                facilities = mark_in_flood(prev, flood)
        except Exception as exc:
            log(f"  could not reuse existing facilities.geojson: {exc}")
    write_geojson(project_roads, CONVERTED / "project_roads.geojson", name="project_roads")
    write_geojson(project_sites, CONVERTED / "project_sites.geojson", name="project_sites")
    write_geojson(facilities, CONVERTED / "facilities.geojson", name="facilities")
    write_geojson(project_roads, OUT / "project_roads.geojson", name="project_roads")
    write_geojson(project_sites, OUT / "project_sites.geojson", name="project_sites")
    write_geojson(facilities, OUT / "facilities.geojson", name="facilities")

    gpkg = CONVERTED / "beledweyne_nagaad_assets.gpkg"
    gpkg.unlink(missing_ok=True)
    wrote_gpkg = False
    if not project_roads.empty:
        drop_z(project_roads).to_file(gpkg, layer="project_roads", driver="GPKG")
        wrote_gpkg = True
    if not project_sites.empty:
        drop_z(project_sites).to_file(gpkg, layer="project_sites", driver="GPKG", mode="a" if wrote_gpkg else "w")
        wrote_gpkg = True
    if not facilities.empty:
        drop_z(facilities).to_file(gpkg, layer="facilities", driver="GPKG", mode="a" if wrote_gpkg else "w")
    log(f"  wrote {gpkg.name}")

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Beledweyne community facilities",
        "description": "Point layer for hospitals, schools/universities, and markets. Add features here or replace facilities.geojson, then re-run the dashboard copy step.",
        "type": "FeatureCollection",
        "required": ["type", "features"],
        "properties": {
            "type": {"const": "FeatureCollection"},
            "name": {"const": "facilities"},
            "features": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "geometry", "properties"],
                    "properties": {
                        "type": {"const": "Feature"},
                        "geometry": {
                            "type": "object",
                            "properties": {"type": {"enum": ["Point", "MultiPoint"]}},
                        },
                        "properties": {
                            "type": "object",
                            "required": ["name", "type"],
                            "properties": {
                                "name": {"type": "string"},
                                "type": {
                                    "type": "string",
                                    "enum": ["hospital", "school", "university", "market"],
                                },
                                "status": {"type": "string"},
                                "source": {"type": "string"},
                                "inFlood": {"type": "integer", "enum": [0, 1]},
                            },
                        },
                    },
                },
            },
        },
    }
    (CONVERTED / "facilities.schema.json").write_text(json.dumps(schema, indent=2), encoding="utf-8")
    shutil.copy2(CONVERTED / "facilities.schema.json", OUT / "facilities.schema.json")
    return project_roads, project_sites, facilities, records


def write_conversion_log(
    records: list[dict],
    osm_roads: int,
    project_roads: gpd.GeoDataFrame,
    project_sites: gpd.GeoDataFrame,
) -> None:
    try:
        import pyogrio

        pyogrio_ver = pyogrio.__version__
    except Exception:
        pyogrio_ver = "unknown"
    payload = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "city": CITY_LABEL,
        "urbanName": CITY_URBAN,
        "tools": {
            "geopandas": gpd.__version__,
            "pyogrio": pyogrio_ver,
            "pandas": pd.__version__,
            "shapely": "2.x via geopandas",
            "tippecanoe": "felt/tippecanoe (Docker image)",
        },
        "crs": {"geometry": WGS84, "lengthAndArea": UTM},
        "inputs": records,
        "outputs": {
            "convertedDir": str(CONVERTED),
            "dashboardDir": str(OUT),
            "osmRoadsFeatures": osm_roads,
            "projectRoadFeatures": int(len(project_roads)),
            "projectSiteFeatures": int(len(project_sites)),
        },
        "process": [
            "Read SURP-II completed/ongoing GeoPackages with GeoPandas/pyogrio (already EPSG:4326).",
            "Read Design Ready KML/KMZ with the OGR KML driver (WGS84). KMZ is a zip wrapping doc.kml.",
            "Drop Z values, KML chrome fields, and null placeholders (None/nan).",
            "Classify Buildings/office as project sites; remaining lines as Nagaad project roads.",
            "Office LineStrings are polygonized when they close; otherwise kept as lines.",
            "Compute length in UTM 38N; keep source length_km when present and > 0.",
            "Intersect separately with the historical flood mask: OSM network vs Nagaad project roads.",
            "Write per-source GeoJSON, combined GeoJSON, and a QGIS GeoPackage under converted/beledweyne/.",
            "Copy dashboard subsets to public/data/beledweyne/. OSM roads also go to PMTiles.",
            "Write an empty facilities.geojson (hospital/school/university/market) for later collection.",
        ],
    }
    path = CONVERTED / "conversion-log.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    log(f"  wrote {path.name}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    CONVERTED.mkdir(parents=True, exist_ok=True)
    log(f"RAW={RAW}")
    log(f"OUT={OUT}")
    log(f"CONVERTED={CONVERTED}")
    log(f"city urbanName={CITY_URBAN}")

    polys = read_vector(RAW / "raw_data" / "SURPII_city_polygons" / "SURPII_city_polygons.shp")
    name_col = first_col(polys, ["UrbanName", "urbanName"])
    if not name_col:
        raise RuntimeError(f"UrbanName column missing: {list(polys.columns)}")
    boundary = polys[polys[name_col].astype(str).str.strip() == CITY_URBAN].copy()
    if boundary.empty:
        raise RuntimeError(f"No polygon for {CITY_URBAN}")
    boundary["geometry"] = boundary.geometry.map(make_valid)
    city_geom = unary_union(boundary.geometry.values)
    city_gdf = gpd.GeoDataFrame(geometry=[city_geom], crs=4326)
    write_geojson(boundary[["geometry"]].assign(name=CITY_LABEL), OUT / "boundary.geojson")

    flood_path = (
        RAW / "raw_data" / "som_floods" / "flood_historical" / "flood_extent_historical_dissolved.shp"
    )
    log("Clipping flood extent…")
    flood = read_vector(flood_path)
    flood["geometry"] = flood.geometry.map(make_valid)
    flood = gpd.clip(flood, city_gdf)
    flood["geometry"] = flood.geometry.simplify(0.00015, preserve_topology=True)
    flood = flood[~flood.geometry.is_empty]
    if flood.empty:
        log("WARNING: flood clip is empty")
        flood = gpd.GeoDataFrame(geometry=[], crs=4326)
    else:
        flood = gpd.GeoDataFrame(geometry=[unary_union(flood.geometry.values)], crs=4326)
        flood["inFlood"] = 1
    flood_geo = OUT / "flood.geojson"
    write_geojson(flood, flood_geo)

    flood_area_ha = 0.0
    if not flood.empty:
        flood_area_ha = float(flood.to_crs(UTM).geometry.area.sum() / 10_000)

    log("Clipping river…")
    river = read_vector(RAW / "raw_data" / "som_rivers" / "SOM_Rivers_Juba_shabelle.shp")
    river = gpd.clip(river, city_gdf)
    keep = [c for c in river.columns if c.lower() in {"name", "code", "class", "geometry"}]
    write_geojson(river[keep] if keep else river, OUT / "river.geojson")

    (OUT / "conflict.geojson").unlink(missing_ok=True)

    log("IDP sites…")
    idp_path = RAW / "decisionMaking_data" / "belet_weyne_idps_flood_exposure.geojson"
    if idp_path.exists():
        idps = read_vector(idp_path)
    else:
        idps = read_vector(RAW / "raw_data" / "som_idp" / "SURPII_city_idps.shp")
        ucol = first_col(idps, ["UrbanName"])
        if ucol:
            idps = idps[idps[ucol].astype(str).str.strip() == CITY_URBAN]
    idps["geometry"] = idps.geometry.map(make_valid)
    idps = mark_in_flood(idps, flood)
    write_geojson(idps, OUT / "idps.geojson")

    log("Buildings + flood join…")
    buildings = read_vector(
        RAW / "raw_data" / "som_buildings" / "buildings_beledweyne" / "Buildingfootprint_Beledweyne.shp"
    )
    buildings["geometry"] = buildings.geometry.map(make_valid)
    area_col = first_col(buildings, ["area_in_me", "areaM2"])
    conf_col = first_col(buildings, ["confidence"])
    buildings = mark_in_flood(buildings, flood)
    out_b = gpd.GeoDataFrame(
        {
            "areaM2": buildings[area_col] if area_col else None,
            "confidence": buildings[conf_col] if conf_col else None,
            "inFlood": buildings["inFlood"].astype(int),
            "geometry": buildings.geometry,
        },
        crs=4326,
    )
    b_geo = OUT / "buildings.geojson"
    write_geojson(out_b, b_geo)

    log("OSM road network + flood join…")
    roads_geojson = RAW / "decisionMaking_data" / "belet_weyne_roads_flood_exposure.geojson"
    if roads_geojson.exists():
        roads = read_vector(roads_geojson)
    else:
        roads = read_vector(RAW / "raw_data" / "som_roads" / "SURPII_city_roads.shp")
        roads = gpd.clip(roads, city_gdf)
    roads["geometry"] = roads.geometry.map(make_valid)
    hw = first_col(roads, ["highway"])
    nm = first_col(roads, ["name"])
    roads_utm = roads.to_crs(UTM)
    length_m = roads_utm.geometry.length.to_numpy()
    roads = mark_in_flood(roads, flood)
    osm_km_flood = flooded_length_km(roads, flood)
    out_r = gpd.GeoDataFrame(
        {
            "highway": roads[hw] if hw else None,
            "name": roads[nm] if nm else None,
            "lengthM": length_m,
            "inFlood": roads["inFlood"].astype(int),
            "network": "osm",
            "geometry": roads.geometry,
        },
        crs=4326,
    )
    r_geo = OUT / "roads.geojson"
    write_geojson(out_r, r_geo)
    write_geojson(out_r, CONVERTED / "osm_roads.geojson", name="osm_roads")

    log("Nagaad project investments (GPKG + KML/KMZ)…")
    project_roads, project_sites, facilities, inv_records = process_investments(flood)
    project_km_total = float(pd.to_numeric(project_roads["lengthKm"], errors="coerce").fillna(0).sum()) if not project_roads.empty else 0.0
    project_km_flood = flooded_length_km(project_roads, flood)
    write_conversion_log(inv_records, int(len(out_r)), project_roads, project_sites)

    def col_num(gdf, names):
        col = first_col(gdf, names)
        if not col:
            return pd.Series(0, index=gdf.index)
        return pd.to_numeric(gdf[col], errors="coerce").fillna(0)

    idp_ind = col_num(idps, ["idpIndividuals", "IDP_Ind"])
    idp_hh = col_num(idps, ["idpHouseholds", "IDP_HHs"])
    in_f = pd.to_numeric(idps["inFlood"], errors="coerce").fillna(0).astype(int)

    summary = {
        "city": CITY_LABEL,
        "urbanName": CITY_URBAN,
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "buildingsTotal": int(len(out_b)),
        "buildingsInFlood": int((out_b["inFlood"] == 1).sum()),
        "idpSitesTotal": int(len(idps)),
        "idpSitesInFlood": int((in_f == 1).sum()),
        "idpIndividualsTotal": float(idp_ind.sum()),
        "idpIndividualsInFlood": float(idp_ind[in_f == 1].sum()),
        "idpHouseholdsInFlood": float(idp_hh[in_f == 1].sum()),
        "roadsKmTotal": float(length_m.sum() / 1000),
        "roadsKmInFlood": osm_km_flood,
        "osmRoadsKmTotal": float(length_m.sum() / 1000),
        "osmRoadsKmInFlood": osm_km_flood,
        "projectRoadsKmTotal": project_km_total,
        "projectRoadsKmInFlood": project_km_flood,
        "projectRoadsCount": int(len(project_roads)),
        "projectRoadsInFloodCount": int((project_roads["inFlood"] == 1).sum()) if not project_roads.empty else 0,
        "projectSitesTotal": int(len(project_sites)),
        "projectSitesInFlood": int((project_sites["inFlood"] == 1).sum()) if not project_sites.empty else 0,
        "facilitiesTotal": int(len(facilities)),
        "floodAreaHa": flood_area_ha,
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    shutil.copy2(OUT / "summary.json", CONVERTED / "summary.json")
    log(f"summary: {json.dumps(summary)}")

    log("Building PMTiles…")
    tippecanoe(
        flood_geo,
        OUT / "flood.pmtiles",
        "flood",
        ["-Z0", "-z14", "--no-feature-limit", "--no-tile-size-limit"],
    )
    tippecanoe(
        b_geo,
        OUT / "buildings.pmtiles",
        "buildings",
        ["-Z12", "-z16", "--drop-densest-as-needed", "--extend-zooms-if-still-dropping"],
    )
    tippecanoe(
        r_geo,
        OUT / "roads.pmtiles",
        "roads",
        ["-Z10", "-z16", "--drop-densest-as-needed"],
    )

    for temp in (b_geo, r_geo, flood_geo):
        temp.unlink(missing_ok=True)
        log(f"  removed intermediate {temp.name}")

    log("ETL complete.")


if __name__ == "__main__":
    main()
