import path from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    // Necessário no Docker Desktop/Windows: eventos de arquivo do bind mount
    // (host -> container) não chegam de forma confiável via inotify, então o
    // watcher padrão do Vite às vezes não detecta mudanças salvas no host —
    // fazendo o navegador rodar código desatualizado silenciosamente.
    watch: {
      usePolling: true,
      interval: 300,
    },
  },
})
