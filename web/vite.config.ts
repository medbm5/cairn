/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Tests run west of Greenwich, where reading a calendar date as UTC shifts it a day back.
if (process.env.VITEST) process.env.TZ = 'America/New_York'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // jsdom workers are slow to start on busy machines; fewer of them avoids start-up timeouts.
    maxWorkers: 3,
  },
})
