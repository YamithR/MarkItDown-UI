const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('api', {
  requestBackend: (req) => ipcRenderer.invoke('backend:request', req),
  onBackendEvent: (cb) => ipcRenderer.on('backend:event', (_evt, msg) => cb(msg)),
  pickFiles: () => ipcRenderer.invoke('dialog:pick-files'),
  pickFolder: () => ipcRenderer.invoke('dialog:pick-folder'),
  openPath: (path) => ipcRenderer.invoke('shell:open-path', path),
  getLocale: () => ipcRenderer.invoke('app:locale'),
  getVersion: () => ipcRenderer.invoke('app:version'),
  getFileSize: (path) => ipcRenderer.invoke('file:stat', path),
  openExternal: (url) => ipcRenderer.invoke('shell:open-external', url),
  getPathForFile: (file) => webUtils.getPathForFile(file),
});