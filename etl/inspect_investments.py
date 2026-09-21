from pathlib import Path
import tempfile
import zipfile

import geopandas as gpd

raw = Path("/data/raw")
roots = [
    raw / "SURP-II Investments completed and ongoing",
    raw / "Design Ready Investments",
]
for root in roots:
    print("===", root.name, "exists", root.exists())
    if not root.exists():
        continue
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in {".gpkg", ".kml", ".kmz"}:
            continue
        print(f"\nFILE {p.relative_to(raw)} ({p.stat().st_size} bytes)")
        try:
            src = p
            if p.suffix.lower() == ".kmz":
                with zipfile.ZipFile(p) as z:
                    print("  kmz:", z.namelist()[:12])
                    kmls = [n for n in z.namelist() if n.lower().endswith(".kml")]
                    td = tempfile.mkdtemp()
                    z.extract(kmls[0], td)
                    src = Path(td) / kmls[0]
            try:
                print("  layers:", gpd.list_layers(src).to_dict("records"))
            except Exception as e:
                print("  layers error:", e)
            g = gpd.read_file(src)
            print("  crs", g.crs, "n", len(g), "types", g.geom_type.value_counts().to_dict())
            print("  cols", list(g.columns))
            print("  bounds", [round(float(x), 5) for x in g.total_bounds] if len(g) else None)
            props = g.drop(columns="geometry")
            if len(props.columns) and len(props):
                print("  row0", {k: str(v)[:60] for k, v in props.iloc[0].to_dict().items()})
        except Exception as e:
            print("  ERROR", type(e).__name__, e)
