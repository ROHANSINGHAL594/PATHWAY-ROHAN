import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [tailwindcss(),react()],
  resolve: {
    alias: {
      'components': path.resolve(__dirname, './src/components'),
      'lib': path.resolve(__dirname, './src/lib'),
      'theme': path.resolve(__dirname, './src/theme'),
      'config': path.resolve(__dirname, './src/config.js'),
      'helpers': path.resolve(__dirname, './src/helpers'),
      'reducers': path.resolve(__dirname, './src/reducers'),
      'providers': path.resolve(__dirname, './src/providers'),
    },
  },
})
