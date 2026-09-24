const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const readline = require('readline');

let mainWindow = null;
let backendProc = null;
let uid = 0;
const pending = new Map();
let backendLog = null;

function logBackendLine(text) {
  try {
    if (!backendLog) {
      const logFile = path.join(app.getPath('userData'), 'backend.log');
      backendLog = fs.createWriteStream(logFile, { flags: 'a' });
    }
    backendLog.write(`[${new Date().toISOString()}] ${text}\n`);
  } catch { /* logging must never break the app */ }
}

function backendCommand() {
  if (app.isPackaged) {
    const exe = process.platform === 'win32' ? 'markitdown-ui-backend.exe' : 'markitdown-ui-backend';
    return {
      cmd: path.join(process.resourcesPath, 'backend', exe),
      args: [],
      env: {
        ...process.env,
        EASYOCR_MODEL_DIR: path.join(process.resourcesPath, 'backend', 'easyocr_models'),
      },
      cwd: process.resourcesPath,
    };
  }
  return {
    cmd: process.platform === 'win32' ? 'python' : 'python3',
    args: ['-m', 'markitdown_ui', '--server'],
    env: {
      ...process.env,
      PYTHONPATH: path.join(__dirname, '..', 'backend'),
    },
    cwd: path.join(__dirname, '..'),
  };
}

function startBackend() {
  const { cmd, args, env, cwd } = backendCommand();
  backendProc = spawn(cmd, args, {
    env,
    cwd,
    windowsHide: true,
    stdio: ['pipe', 'pipe', 'pipe'],
  });

  const rl = readline.createInterface({ input: backendProc.stdout });
  rl.on('line', (line) => {
    let msg;
    try {
      msg = JSON.parse(line);
    } catch {
      return;
    }
    const id = msg.id;
    const terminal = msg.type === 'pong' || msg.type === 'backends' ||
                     msg.type === 'batch_done' || msg.type === 'error';
    if (id != null && terminal && pending.has(id)) {
      pending.get(id).resolve(msg);
      pending.delete(id);
      if (msg.type === 'pong' || msg.type === 'backends' || msg.type === 'batch_done') {
        // reply consumed by the awaiting renderer request; batch events were
        // already forwarded as they streamed in
        return;
      }
    }
    mainWindow?.webContents.send('backend:event', msg);
  });

  backendProc.stderr.on('data', (buf) => {
    const text = buf.toString().trim();
    if (text) {
      logBackendLine(text);
      mainWindow?.webContents.send('backend:event', {
        type: 'stderr',
        id: uid + 1,
        message: text,
      });
    }
  });

  backendProc.on('exit', (code) => {
    logBackendLine(`__BACKEND_EXIT__ code=${code}`);
    rejectAllPending(`backend exited with code ${code}`);
    mainWindow?.webContents.send('backend:event', {
      type: 'backend_exit',
      id: 0,
      code,
    });
    backendProc = null;
  });
  backendProc.on('error', (err) => {
    logBackendLine(`__BACKEND_ERROR__ ${err.message}`);
    rejectAllPending(`backend error: ${err.message}`);
    mainWindow?.webContents.send('backend:event', {
      type: 'backend_error',
      id: 0,
      message: err.message,
    });
  });
}

function rejectAllPending(reason) {
  for (const [id, entry] of pending) {
    entry.reject(new Error(reason));
    pending.delete(id);
  }
}

function requestBackend(req) {
  return new Promise((resolve, reject) => {
    const id = ++uid;
    req = { ...req, id };
    pending.set(id, { resolve, reject });
    if (req.cmd !== 'convert') {
      setTimeout(() => {
        if (pending.has(id)) {
          pending.delete(id);
          reject(new Error(`timeout: no reply for request ${id}`));
        }
      }, 30000);
    }
    backendProc?.stdin.write(JSON.stringify(req) + '\n');
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 760,
    minWidth: 760,
    minHeight: 560,
    title: 'MarkItDown UI',
    icon: path.join(__dirname, 'assets', process.platform === 'win32' ? 'icon.ico' : 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, 'renderer', 'index.html'));
  mainWindow.on('closed', () => { mainWindow = null; });
}

app.whenReady().then(() => {
  startBackend();
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('will-quit', () => {
  backendProc?.stdin.end();
  backendProc?.kill();
});

ipcMain.handle('backend:request', (_evt, req) => requestBackend(req));

ipcMain.handle('dialog:pick-files', async () => {
  const res = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile', 'multiSelections'],
  });
  return res.canceled ? [] : res.filePaths;
});

ipcMain.handle('dialog:pick-folder', async () => {
  const res = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory', 'createDirectory'],
  });
  return res.canceled ? null : res.filePaths[0];
});

ipcMain.handle('shell:open-path', async (_evt, target) => {
  if (!target || typeof target !== 'string') return false;
  try {
    if (fs.existsSync(target)) {
      await shell.openPath(target);
      return true;
    }
    const res = await dialog.showMessageBox(mainWindow, {
      type: 'warning',
      buttons: ['OK'],
      message: 'Destination folder does not exist.',
    });
    return false;
  } catch {
    return false;
  }
});

ipcMain.handle('app:locale', () => {
  const loc = app.getLocale().toLowerCase();
  return loc.startsWith('es') ? 'es' : 'en';
});

ipcMain.handle('app:version', () => app.getVersion());

ipcMain.handle('file:stat', async (_evt, target) => {
  if (!target || typeof target !== 'string') return null;
  try {
    const st = await fs.promises.stat(target);
    return st.size;
  } catch {
    return null;
  }
});

ipcMain.handle('shell:open-external', async (_evt, url) => {
  if (typeof url !== 'string' || !/^https?:\/\//.test(url)) return false;
  try {
    await shell.openExternal(url);
    return true;
  } catch {
    return false;
  }
});