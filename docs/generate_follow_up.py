"""Generate the technical-team follow-up (DOCX) for the Beledweyne flood dashboard."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

OUT_DIR = Path(__file__).resolve().parent
LOGO = OUT_DIR / "nagaad-logo.png"
DOC_NAVY = RGBColor(0x1E, 0x4D, 0x7B)
TODAY = date(2026, 9, 21).strftime("%d %B %Y")


def _set_cell_shading(cell, hex_color: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _shade_header(row) -> None:
    for cell in row.cells:
        _set_cell_shading(cell, "1E4D7B")
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                run.font.bold = True


def _add_table(doc: Document, header: list[str], rows: list[list[str]]) -> None:
    table = doc.add_table(rows=1 + len(rows), cols=len(header))
    table.style = "Table Grid"
    for i, h in enumerate(header):
        table.rows[0].cells[i].text = h
    _shade_header(table.rows[0])
    for r, row in enumerate(rows, start=1):
        for c, val in enumerate(row):
            table.rows[r].cells[c].text = val
    doc.add_paragraph()


def _heading(doc: Document, text: str, level=1) -> None:
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = DOC_NAVY


def build_docx(path: Path) -> None:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(1)
    section.bottom_margin = Inches(0.9)
    section.left_margin = Inches(1)
    section.right_margin = Inches(1)

    header = section.header.paragraphs[0]
    header.text = ""
    if LOGO.exists():
        run = header.add_run()
        run.add_picture(str(LOGO), width=Inches(0.42))
        header.add_run(
            "   Nagaad  ·  Somalia Urban Resilience Project Phase II  ·  Follow-up to the technical team"
        )
    else:
        header.text = "Nagaad  ·  Municipal Flood Risk Dashboard  ·  Technical follow-up"
    if header.runs:
        header.runs[-1].font.size = Pt(9)
        header.runs[-1].font.color.rgb = DOC_NAVY

    footer = section.footer.paragraphs[0]
    footer.text = (
        f"Beledweyne flood screening  ·  {TODAY}  ·  Indicative only — not a probabilistic risk model"
    )
    footer.runs[0].font.size = Pt(8)
    footer.runs[0].font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    title = doc.add_heading("Follow-up to the technical / analysis team", 0)
    for run in title.runs:
        run.font.color.rgb = DOC_NAVY

    intro = doc.add_paragraph()
    intro.add_run("Nagaad Municipal Flood Risk Dashboard — Beledweyne (indicative screening)").bold = True
    meta = doc.add_paragraph()
    meta.add_run(f"Date: {TODAY}\n")
    meta.add_run("To: GIS / analysis, information management, PIU\n")
    meta.add_run("Purpose: request data and written explanations so this screening map can become a municipal decision tool; record two product questions (IDP list labelling, and public hosting on GitHub Pages).")

    _heading(doc, "1. What we already have (so you do not re-send it)")
    doc.add_paragraph(
        "The Beledweyne dashboard is a flood-only screening overlay, built to embed in Nagaad MIS "
        "(/portal/risk?city=Beledweyne). It is not a full risk model. Current layers and KPIs:"
    )
    _add_table(
        doc,
        ["Layer / KPI", "What the current build uses", "Limitation"],
        [
            [
                "Flood",
                "Historical Shabelle flood extent clipped to the Belet Weyne urban polygon (~5,223 ha)",
                "Single ever-flooded mask. Almost the whole city intersects it. No depth, no year, no return period.",
            ],
            [
                "Buildings",
                "SURP II footprints; 47,013 of 51,954 intersect the mask",
                "Footprint counts only. No use, occupancy, or structure type.",
            ],
            [
                "OSM roads",
                "City-wide OpenStreetMap network; 410.3 km of 430.7 km in the mask",
                "Separate from Nagaad roads on purpose. Completeness varies by class.",
            ],
            [
                "Nagaad roads / sites",
                "SURP-II GPKG (completed/ongoing) and design-ready KML/KMZ; 22.7 km of 33.9 km in the mask",
                "All 17 road features intersect the mask, so flood colour is not used on the map — green = built/ongoing, purple = design ready.",
            ],
            [
                "IDP / host sites",
                "IOM DTM / SURP II points; 133 sites, 97,813 people; all 133 intersect the mask",
                "See section 2. Coordinates + population are protection-sensitive if published (section 5).",
            ],
            [
                "Hospitals, schools, markets",
                "Empty placeholder layer (schema ready)",
                "Need your points before this is useful.",
            ],
        ],
    )
    doc.add_paragraph(
        "Please treat figures as screening, not as a basis for demolition, compensation, insurance, or engineering freeboard."
    )

    _heading(doc, "2. Why the list was called “Priority IDP sites” — and why that name is dropped")
    doc.add_paragraph(
        "The sidebar cannot show 133 named sites at once. The first build therefore:"
    )
    for item in [
        "kept only sites that intersect the historical flood mask;",
        "sorted them by IDP individuals (largest first);",
        "showed the top 15 in a table labelled “Priority IDP sites”.",
    ]:
        doc.add_paragraph(item, style="List Bullet")
    doc.add_paragraph(
        "The motive was operational convenience: give a mayor or municipal engineer a short list to start site visits "
        "and humanitarian coordination, not a blank map of 133 dots."
    )
    p = doc.add_paragraph()
    p.add_run("That label over-claimed.").bold = True
    p.add_run(
        " “Priority” in municipal risk work usually means a scored ranking (people + depth + access + critical services "
        "+ investment at risk). We do not have that score. In Beledweyne the flood mask covers nearly the whole urban "
        "area, so “in flood” does not distinguish sites from each other. Headcount-only ranking is a display sort, not "
        "an operational priority. Calling it priority could be read as a targeting or relocation list, which this "
        "product must not imply."
    )
    doc.add_paragraph("The dashboard label is therefore changed to “IDP sites”, sorted by population, with all flooded sites that have people (not a top-15 shortlist). A genuine priority score can be added later if you can supply the inputs in section 4.")
    doc.add_paragraph(
        "How municipalities should use the current list: sequence visits and drainage discussion around the largest "
        "named sites. Do not use it as an order to move people."
    )

    _heading(doc, "3. Explanations we need from you (please answer in writing)")
    doc.add_paragraph(
        "These are the gaps that currently stop us from going beyond a screening map. A short data dictionary plus "
        "source / date / licence for each layer is enough."
    )
    _add_table(
        doc,
        ["#", "Question", "Why it matters"],
        [
            [
                "1",
                "Flood extent: which events and years, who produced it, max envelope vs single event, any depth or duration?",
                "Users currently read “ever flooded” as “this building will flood.” We need to state the method on the map.",
            ],
            [
                "2",
                "Can this flood layer be published on a public website, or is it internal screening only?",
                "Hosting decision (section 5).",
            ],
            [
                "3",
                "IDP layer: which DTM round and date? Are coordinates centroids of camps or GPS of a facility? Are host-community points in or out of scope?",
                "The list mixes camp-like sites and some host neighbourhoods. Population is 0 on several host points.",
            ],
            [
                "4",
                "IOM DTM licence: may we show site names, coordinates, and individual/household counts on a map that can be opened outside MIS?",
                "Humanitarian protection and DTM terms of use. This is the main publication risk.",
            ],
            [
                "5",
                "Building footprints: source, date, licence; may they be served as public vector tiles?",
                "~52,000 outlines are a detailed urban dataset even without names.",
            ],
            [
                "6",
                "Nagaad / SURP-II roads: which packages are approved to show as “design ready” before tender? Any alignments that must stay internal?",
                "Design-ready KML/KMZ may be commercially or politically sensitive.",
            ],
            [
                "7",
                "Official neighbourhood / section names the municipality uses for Beledweyne (polygons, not DTM site names).",
                "City-wide KPIs cannot allocate sandbags, meetings, or machines.",
            ],
            [
                "8",
                "Preferred CRS and delivery format for new layers (we can take GPKG, GeoJSON, or KML; we reproject to WGS84).",
                "Avoid another mixed-format round.",
            ],
        ],
    )

    _heading(doc, "4. Data request — layers to collect next")
    doc.add_paragraph(
        "Please deliver WGS84 GeoPackage or GeoJSON (KML acceptable), clipped or clearly attributable to Beledweyne, "
        "with a one-page dictionary. Suggested order:"
    )
    _add_table(
        doc,
        ["Priority", "Layer", "Minimum fields", "Decision it unlocks"],
        [
            [
                "P1",
                "Neighbourhoods / municipal sections",
                "name (local), population if known",
                "KPI and site lists by area, not only city-wide",
            ],
            [
                "P1",
                "Hospitals and health posts",
                "name, type, operator, beds/staff if known",
                "Service continuity in flood",
            ],
            [
                "P1",
                "Schools and universities",
                "name, type, enrolment if known",
                "Protect education sites and possible shelters",
            ],
            [
                "P1",
                "Markets",
                "name, periodic vs daily",
                "Livelihoods and access",
            ],
            [
                "P1",
                "Flood by event year and/or return period; depth if it exists",
                "year or RP, depth class",
                "Replace the single ever-flooded flag",
            ],
            [
                "P2",
                "Drains, culverts, bridges, pumps, flood walls",
                "type, condition, last cleared",
                "Find blockage and failure points",
            ],
            [
                "P2",
                "DEM or low-lying / ponding pockets",
                "elevation or ponding class",
                "Where water stays after the river drops",
            ],
            [
                "P2",
                "Nagaad works table joined to alignments",
                "package, cost USD, status, drainage Y/N, design standard",
                "Rank investments, not only lines on a map",
            ],
            [
                "P2",
                "Water points / berkads",
                "name, functional Y/N",
                "WASH during flood",
            ],
            [
                "P3",
                "Past damage and displacement",
                "year, households, location",
                "Validate the mask against lived events",
            ],
            [
                "P3",
                "Rainfall / river gauges",
                "station, date, value",
                "Later link to early warning",
            ],
            [
                "P3",
                "Solid-waste dump sites",
                "name, status",
                "Drainage blockage risk",
            ],
        ],
    )
    doc.add_paragraph(
        "Facilities schema already reserved: name, type (hospital | school | university | market), status, source, "
        "inFlood. Extra types (health_post, water_point, municipal_office, mosque) can be added when data arrive. "
        "Use neighbourhood names the municipality actually uses."
    )

    _heading(doc, "5. GitHub Pages and public-data risk — please consult internally before publishing")
    p = doc.add_paragraph()
    p.add_run("This should be an internal decision, not a default of the web stack.").bold = True
    p.add_run(
        " GitHub Pages is the current publish path because it is free and iframe-friendly for MIS. It is not a "
        "security boundary."
    )

    _heading(doc, "5.1 What “public” means here", 2)
    for item in [
        "A GitHub Pages URL is reachable by anyone who has or guesses the link. Search engines can index it.",
        "Embedding in Nagaad MIS does not protect the data. MIS login wraps an iframe; the iframe src can be opened in a new tab with no portal session.",
        "If the GitHub repository is public, processed GeoJSON/PMTiles also sit in git (and in git history even after a later delete, unless rewritten).",
        "A private repository with a public Pages site still publishes the built files. Privacy of the repo ≠ privacy of the dashboard.",
        "Standard GitHub Pages has no Nagaad user login. Paid “private Pages” still shares a URL with anyone who receives it, unless a separate access proxy is added.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    _heading(doc, "5.2 What would go live with the current files", 2)
    _add_table(
        doc,
        ["File", "Content of concern if public"],
        [
            ["idps.geojson", "Site name, DTM id, coordinates, IDP individuals and households"],
            ["buildings.pmtiles", "Vector tiles of ~52,000 building outlines"],
            ["flood.pmtiles", "Historical flood polygon for the city"],
            ["roads.pmtiles", "OSM road network with flood flag"],
            ["project_roads.geojson / project_sites.geojson", "Nagaad alignments, including design-ready packages"],
            ["summary.json", "City-level counts (people, km, hectares)"],
        ],
    )
    doc.add_paragraph(
        "The highest sensitivity is named IDP sites with coordinates and population. Precise camp locations can "
        "create protection, security, and reputational issues even when the numbers are already used internally. "
        "Building footprints and unreleased design alignments are the next concern. OSM roads and a coarse flood "
        "mask are closer to what is often already public — but that is for data owners to confirm, not for the "
        "dashboard team to assume."
    )

    _heading(doc, "5.3 Alternatives (if Pages is not acceptable for some layers)", 2)
    _add_table(
        doc,
        ["Option", "What it gives you", "Trade-off"],
        [
            [
                "A. GitHub Pages, public layers only",
                "Keep the current host. Publish only layers data owners classify as public. Hold IDP names/coordinates (and maybe footprints) until cleared.",
                "Simplest. Dashboard is thinner until clearance.",
            ],
            [
                "B. Same origin as MIS (nagaadmis.mpwr.gov.so or Firebase Hosting already used by the portal)",
                "One login story; easier to put the map behind portal auth if you also stop serving the files as a bare URL.",
                "Needs hosting work on the MIS project. Auth must apply to the data files, not only the portal chrome.",
            ],
            [
                "C. Public map shell + authenticated API for sensitive GeoJSON",
                "Map and OSM/flood can stay on Pages; IDP and buildings load only with a MIS token.",
                "Correct split, more engineering. Tokens in a browser can still be copied by a logged-in user.",
            ],
            [
                "D. Aggregate IDP on the public map",
                "Show neighbourhood counts only; named camps and GPS stay internal.",
                "Safer public product. Loses click-to-site until an internal view exists.",
            ],
            [
                "E. Access proxy (Cloudflare Access, Google IAP, Azure AD) in front of the static site",
                "Pages or any static host, but only Nagaad accounts get in.",
                "Extra licence/ops. MIS iframe must pass that auth (SSO).",
            ],
            [
                "F. Internal-only until the first data-protection review",
                "Keep running on localhost / PIU network; no public URL in MIS yet.",
                "Safest. Delays city users.",
            ],
        ],
    )

    _heading(doc, "5.4 Recommended decision process", 2)
    doc.add_paragraph("Please convene a short internal check before the first public URL is registered in MIS Admin → Municipal Risk. Suggested attendees: PIU / Nagaad information management, GIS/analysis (data owners), and whoever signs off IOM DTM and SURP spatial data. World Bank / SURP II task team if the financing or data agreements require it.")
    doc.add_paragraph("Ask them to classify each layer as: (1) public, (2) MIS-authenticated only, or (3) internal / do not map. Until that classification exists, do not treat GitHub Pages as approved production hosting for IDP coordinates and population.")
    p = doc.add_paragraph()
    p.add_run("Practical default if the meeting cannot happen immediately: ").italic = True
    p.add_run(
        "keep the dashboard local and inside PIU; if a public Pages demo is required, omit idps.geojson (show city-level IDP KPIs only, or no IDP layer) until IOM/PIU clearance is written down."
    )

    _heading(doc, "6. Dashboard improvements once the data and hosting decision exist")
    _add_table(
        doc,
        ["Improvement", "Depends on you", "Decision it unlocks"],
        [
            [
                "Neighbourhood KPI split",
                "Section polygons + names",
                "Allocate response by part of Beledweyne",
            ],
            [
                "Transparent priority score (then, and only then, a “priority” list)",
                "Depth or scenario flood + facilities + works attributes",
                "Rank sites and road packages on one comparable list",
            ],
            [
                "Multi-scenario flood",
                "Event years or return periods",
                "Distinguish “sometimes wet” from deep / frequent water",
            ],
            [
                "Critical facilities on the map",
                "Hospitals, schools, markets, water",
                "Protect services, not only footprints",
            ],
            [
                "Drainage / culverts / bridges",
                "Asset survey",
                "Target the things that actually fail",
            ],
            [
                "Join Nagaad roads to MIS works",
                "Package, cost, contractor, drainage Y/N",
                "Put risk next to the contract the municipality already tracks",
            ],
            [
                "One-page PDF/PNG + Somali labels",
                "Agreed terminology",
                "Brief council without a live laptop",
            ],
        ],
    )

    _heading(doc, "7. What we will do on our side after you reply")
    for item in [
        "Ingest new layers in the same ETL (WGS84 GeoJSON + PMTiles where files are large), keep OSM roads and Nagaad roads separate, document conversions.",
        "Apply the hosting classification: public files on the chosen host; sensitive files withheld or moved behind MIS auth.",
        "Keep the product flood-only until a second hazard is explicitly requested and sourced.",
        "Do not call anything “priority” until there is a documented score and a municipal owner for that score.",
    ]:
        doc.add_paragraph(item, style="List Bullet")

    doc.add_paragraph()
    close = doc.add_paragraph()
    close.add_run(
        "Please reply with (a) written answers to section 3, (b) a first drop of P1 layers if they exist, and "
        "(c) a hosting classification for IDP, buildings, flood, and Nagaad design-ready roads. The dashboard "
        "can stay useful as indicative screening in the meantime."
    )
    note = doc.add_paragraph()
    run = note.add_run(
        "Companion files: Nagaad_Municipal_Risk_Dashboard_Briefing.pptx (purpose and architecture) and "
        "Nagaad_Municipal_Risk_Dashboard_Process.docx (how the ETL was run)."
    )
    run.italic = True

    doc.save(path)


def main() -> None:
    out = OUT_DIR / "Nagaad_Municipal_Risk_Technical_Follow_Up.docx"
    build_docx(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
