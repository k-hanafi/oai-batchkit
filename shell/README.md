# batchkit-shell

Electron shell. Hosts the React frontend (renderer process) and will, in Phase 7, spawn and supervise the Python backend (main process).

Security: `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true` from the first commit. The preload script exposes a narrowly-scoped API at `window.batchkit`.

## Local setup

```bash
cd shell
npm install
npm start
```

`npm start` launches Electron via electron-forge. Set `VITE_DEV_SERVER_URL` to point at `npm run dev` in `frontend/` for HMR; otherwise the shell loads the static `frontend/dist/`.

## Commands

```bash
npm start            # launch dev electron
npm run lint         # eslint
npm run package      # build the .app
npm run make         # build .dmg / .zip (Phase 7)
```
