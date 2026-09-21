interface SourcesFooterProps {
  generatedAt?: string
  embed: boolean
}

export function SourcesFooter({ generatedAt, embed }: SourcesFooterProps) {
  const date = generatedAt ? generatedAt.slice(0, 10) : undefined
  const full =
    'Indicative flood screening only — not a full probabilistic risk model. Historical Shabelle flood extent is clipped to the city and intersected separately with buildings, OSM roads, Nagaad project roads, and IDP sites. Buildings from SURP II footprints; city-wide roads from OSM; Nagaad roads from SURP-II GeoPackages and design-ready KML/KMZ. IDP sites from IOM DTM / SURP II. Hospitals, schools, and markets are reserved for later collection. Basemap tiles © Esri.' +
    (date ? ` Data processed ${date}.` : '')

  const compact = [
    'Indicative screening — not a probabilistic model',
    'Shabelle historical flood',
    'SURP II / OSM / IOM DTM',
    'Basemap © Esri',
    date ? `Processed ${date}` : null,
  ]
    .filter(Boolean)
    .join(' · ')

  return (
    <footer
      className={`shrink-0 border-t border-slate-200 bg-slate-50 text-[10px] leading-tight text-slate-600 ${
        embed ? 'px-2.5 py-1' : 'px-4 py-1.5'
      }`}
      title={full}
    >
      {embed ? <p className="truncate">{compact}</p> : <p>{full}</p>}
    </footer>
  )
}
