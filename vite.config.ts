import { copyFileSync, mkdirSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'

const MAPLIBRE_WORKER_FILES = ['maplibre-gl-worker.mjs', 'maplibre-gl-shared.mjs'] as const

/** Serve MapLibre's worker + shared module as a pair so GitHub Pages does not 404 the import. */
function maplibreWorkerFiles(): Plugin {
  const distDir = resolve('node_modules/maplibre-gl/dist')
  const names = new Set<string>(MAPLIBRE_WORKER_FILES)

  return {
    name: 'maplibre-worker-files',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const pathname = req.url?.split('?')[0] ?? ''
        const name = pathname.split('/').pop() ?? ''
        if (!pathname.includes('/maplibre/') || !names.has(name)) {
          next()
          return
        }
        res.setHeader('Content-Type', 'text/javascript; charset=utf-8')
        res.end(readFileSync(resolve(distDir, name)))
      })
    },
    closeBundle() {
      const outDir = resolve('dist/maplibre')
      mkdirSync(outDir, { recursive: true })
      for (const name of MAPLIBRE_WORKER_FILES) {
        copyFileSync(resolve(distDir, name), resolve(outDir, name))
      }
    },
  }
}

export default defineConfig({
  base: process.env.GITHUB_PAGES === 'true' ? '/nagaad-municipal-risk/' : '/',
  plugins: [react(), tailwindcss(), maplibreWorkerFiles()],
  optimizeDeps: {
    exclude: ['maplibre-gl'],
  },
})
