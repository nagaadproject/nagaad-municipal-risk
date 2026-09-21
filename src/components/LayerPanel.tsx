import type { CityConfig, LayerGroup } from '../cities/types'

const GROUP_LABEL: Record<LayerGroup, string> = {
  hazard: 'Flood hazard',
  exposure: 'Exposure',
  infrastructure: 'Infrastructure',
  investment: 'Investment',
  services: 'Services',
}

function legendCaption(label: string) {
  if (label.startsWith('Completed')) return 'Built'
  if (label === 'Design ready') return 'Design'
  if (label === 'River centreline') return 'River'
  if (label === 'Office / buildings') return 'Sites'
  if (label === 'Ever flooded') return 'Flooded'
  if (label === 'Urban extent') return 'Extent'
  return label
}

interface LayerPanelProps {
  city: CityConfig
  layerOn: Record<string, boolean>
  onToggle: (id: string) => void
}

export function LayerPanel({ city, layerOn, onToggle }: LayerPanelProps) {
  const groups: LayerGroup[] = ['hazard', 'exposure', 'infrastructure', 'investment', 'services']

  return (
    <section className="shrink-0 px-2.5 py-2">
      <h2 className="mb-1 text-xs font-semibold text-slate-900">Layers</h2>
      {groups.map((group) => {
        const layers = city.layers.filter((l) => l.group === group)
        if (!layers.length) return null
        return (
          <div key={group} className="mb-1.5 last:mb-0">
            <div className="mb-0.5 text-[9px] font-semibold uppercase tracking-wide text-slate-400">
              {GROUP_LABEL[group]}
            </div>
            <ul>
              {layers.map((layer) => (
                <li key={layer.id}>
                  <label className="flex cursor-pointer items-center gap-1.5 overflow-hidden rounded px-0.5 py-[3px] hover:bg-slate-50">
                    <input
                      type="checkbox"
                      className="size-3.5 shrink-0 accent-[#1e4d7b]"
                      checked={layerOn[layer.id] !== false}
                      onChange={() => onToggle(layer.id)}
                    />
                    <span
                      className="min-w-0 flex-1 truncate text-[11px] leading-none text-slate-800"
                      title={layer.label}
                    >
                      {layer.label}
                    </span>
                    <span className="flex shrink-0 items-center justify-end gap-1">
                      {layer.legend.map((item) => (
                        <span
                          key={item.label}
                          className="inline-flex items-center gap-0.5"
                          title={item.label}
                        >
                          <span
                            className="inline-block size-2 shrink-0 rounded-[2px]"
                            style={{ background: item.color }}
                          />
                          {layer.legend.length <= 2 && (
                            <span className="text-[9px] leading-none text-slate-500">
                              {legendCaption(item.label)}
                            </span>
                          )}
                        </span>
                      ))}
                    </span>
                  </label>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </section>
  )
}
