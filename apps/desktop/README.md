# @varta/desktop

Windows/macOS shell (Electron). Owner: WEB-2.

Plan v2 D-7: a thin signed shell that loads the hosted web app (`https://app.<domain>`), not a
bundled Next.js build. `BrowserWindow` uses `contextIsolation: true`, `nodeIntegration: false`,
`sandbox: true` and a navigation allowlist; the preload exposes only notifications, badge count
and tray. Auto-update via electron-updater.
