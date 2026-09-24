'use strict';

/* ===== State ===== */
const state = {
  lang: 'en',
  files: [],            // {path, name, size, status: 'pending'|'converting'|'ok'|'error', output, error}
  selected: new Set(),  // indexes
  conversionId: null,
  converting: false,
  ocrOn: true,
  dest: '',
};

const $ = (id) => document.getElementById(id);
const tbody = $('file-tbody');

/* ===== Helpers ===== */
function formatSize(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  const units = ['KB', 'MB', 'GB', 'TB'];
  let v = bytes;
  let i = -1;
  do {
    v /= 1024;
    i++;
  } while (v >= 1024 && i < units.length - 1);
  return v.toFixed(v >= 100 ? 0 : 1) + ' ' + units[i];
}

function extOf(name) {
  const idx = name.lastIndexOf('.');
  return idx > 0 ? name.slice(idx + 1).toLowerCase() : '';
}

function nameOf(p) {
  return p.split(/[\\/]/).pop() || p;
}

function dirOf(p) {
  const idx = Math.max(p.lastIndexOf('/'), p.lastIndexOf('\\'));
  return idx > 0 ? p.slice(0, idx) : '.';
}

function basenameNoExt(p) {
  const n = nameOf(p);
  const idx = n.lastIndexOf('.');
  return idx > 0 ? n.slice(0, idx) : n;
}

let toastTimer = null;
function showToast(msg, kind) {
  const el = $('toast');
  el.textContent = msg;
  el.className = 'toast' + (kind ? ' ' + kind : '');
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { el.hidden = true; }, 4500);
}

function setStatusLine(msg, kind) {
  const el = $('status-line');
  el.textContent = msg;
  el.className = 'status-line' + (kind ? ' ' + kind : '');
}

/* ===== i18n ===== */
function applyLanguage(lang) {
  state.lang = lang === 'es' ? 'es' : 'en';
  document.documentElement.lang = state.lang;
  $('lang-en').classList.toggle('active', state.lang === 'en');
  $('lang-es').classList.toggle('active', state.lang === 'es');
  $('drop-text').textContent = t('dropText');
  $('drop-hint').textContent = t('dropHint');
  $('files-title').textContent = t('filesTitle');
  $('th-name').textContent = t('thName');
  $('th-size').textContent = t('thSize');
  $('th-status').textContent = t('thStatus');
  $('dest-label').textContent = t('destLabel');
  $('dest-browse').textContent = t('browse');
  $('dest-open').textContent = t('open');
  $('dest-open').title = t('openTitle');
  $('ocr-label').textContent = t('ocrLabel');
  $('ocr-backend-label').textContent = t('ocrBackendLabel');
  $('ocr-lang-label').textContent = t('ocrLangLabel');
  $('remove-selected').textContent = t('removeSelected');
  $('convert-btn').textContent = t('convertBtn');
  $('file-empty').textContent = t('noFiles');
  renderFiles();
}

/* ===== File list rendering ===== */
function badgeClass(ext) {
  const letter = ext.charCodeAt(0) || 0;
  const hues = [210, 262, 300, 148, 16, 88, 30, 340, 190, 250];
  return 'hsl(' + hues[letter % hues.length] + ', 35%, 42%)';
}

function statusInfo(f) {
  if (f.status === 'converting') return { cls: 'converting', text: t('statusConverting') };
  if (f.status === 'ok') return { cls: 'ok', text: t('statusOk') };
  if (f.status === 'error') return { cls: 'error', text: t('statusError') };
  return { cls: 'pending', text: t('statusPending') };
}

function renderFiles() {
  tbody.innerHTML = '';
  for (let i = 0; i < state.files.length; i++) {
    const f = state.files[i];
    const st = statusInfo(f);
    const tr = document.createElement('tr');
    if (state.selected.has(i)) tr.classList.add('selected');

    const tdCheck = document.createElement('td');
    tdCheck.className = 'col-check';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = state.selected.has(i);
    cb.addEventListener('change', () => toggleSelect(i, cb.checked));
    tdCheck.appendChild(cb);

    const tdName = document.createElement('td');
    tdName.className = 'col-name';
    const nameDiv = document.createElement('div');
    nameDiv.className = 'file-name';
    const badge = document.createElement('span');
    badge.className = 'ext-badge';
    badge.textContent = extOf(f.name) || '?';
    badge.style.background = badgeClass(extOf(f.name));
    const nameSpan = document.createElement('span');
    nameSpan.className = 'file-name-text';
    nameSpan.textContent = f.name;
    nameSpan.title = f.path;
    nameDiv.append(badge, nameSpan);
    tdName.appendChild(nameDiv);

    const tdSize = document.createElement('td');
    tdSize.className = 'col-size file-size';
    tdSize.textContent = formatSize(f.size);

    const tdStatus = document.createElement('td');
    tdStatus.className = 'col-status';
    const statDiv = document.createElement('div');
    statDiv.className = 'file-status';
    if (f.status === 'converting') {
      const spin = document.createElement('div');
      spin.className = 'spinner';
      statDiv.appendChild(spin);
    } else {
      const dot = document.createElement('span');
      dot.className = 'status-dot ' + st.cls;
      statDiv.appendChild(dot);
    }
    const stText = document.createElement('span');
    stText.className = 'status-text ' + (st.cls === 'pending' ? 'dim' : st.cls);
    stText.textContent = st.text;
    if (f.status === 'ok' && f.output) {
      stText.title = f.output;
    }
    if (f.status === 'error' && f.error) {
      stText.title = f.error;
    }
    statDiv.appendChild(stText);
    tdStatus.appendChild(statDiv);

    tr.append(tdCheck, tdName, tdSize, tdStatus);
    tr.addEventListener('click', (e) => {
      if (e.target.tagName === 'INPUT') return;
      const next = !state.selected.has(i);
      clearSelection();
      toggleSelect(i, next);
    });
    tbody.appendChild(tr);
  }

  $('file-count').textContent = String(state.files.length);
  $('file-empty').hidden = state.files.length > 0;
  $('remove-selected').hidden = state.selected.size === 0;
  const anyPending = state.files.some((f) => f.status === 'pending');
  $('convert-btn').disabled = state.converting || state.files.length === 0 || !anyPending;
}

function toggleSelect(i, on) {
  if (on) state.selected.add(i);
  else state.selected.delete(i);
  renderFiles();
}

function clearSelection() {
  state.selected.clear();
  renderFiles();
}

function addFiles(paths) {
  const existing = new Set(state.files.map((f) => f.path));
  let added = 0;
  for (const p of paths) {
    if (existing.has(p)) continue;
    existing.add(p);
    state.files.push({
      path: p,
      name: nameOf(p),
      size: 0,
      status: 'pending',
      output: null,
      error: null,
    });
    added++;
  }
  if (state.dest === '' && state.files.length > 0) {
    const last = state.files[state.files.length - 1].path;
    state.dest = dirOf(last);
    $('dest-input').value = state.dest;
  }
  if (added > 0) renderFiles();
}

function removeSelected() {
  const idxs = [...state.selected].sort((a, b) => b - a);
  for (const i of idxs) state.files.splice(i, 1);
  state.selected.clear();
  renderFiles();
}

/* ===== Backend wire ===== */
async function initBackend() {
  try {
    const resp = await window.api.requestBackend({ cmd: 'list_backends' });
    if (resp && resp.type === 'backends') {
      populateBackends(resp.names || [], resp.default_langs || []);
    }
  } catch {
    // backend offline; surfaced via backend_error event
  }
}

function handleEvent(msg) {
  if (!msg || typeof msg !== 'object') return;

  if (msg.type === 'progress') {
    updateProgress(msg.pct);
    return;
  }
  if (msg.type === 'file_status' && msg.status === 'converting') {
    const f = findFile(msg.file);
    if (f) {
      f.status = 'converting';
      renderFiles();
    }
    return;
  }
  if (msg.type === 'file_done') {
    const f = findFile(msg.file);
    if (msg.status === 'ok') {
      if (f) {
        f.status = 'ok';
        f.output = msg.output || null;
      }
      updateProgressLive();
    } else {
      if (f) {
        f.status = 'error';
        f.error = msg.error || 'unknown error';
      }
    }
    renderFiles();
    return;
  }
  if (msg.type === 'error') {
    setStatusLine(msg.message || 'Error', 'error');
    return;
  }
  if (msg.type === 'stderr') {
    return;
  }
  if (msg.type === 'backend_error') {
    setStatusLine(t('backendError', { msg: msg.message || 'unknown' }), 'error');
    showToast(t('backendError', { msg: msg.message || 'unknown' }), 'error');
    return;
  }
  if (msg.type === 'backend_exit') {
    state.converting = false;
    $('convert-btn').disabled = false;
    if (msg.code !== 0) {
      setStatusLine(t('backendExited', { code: msg.code }), 'error');
      showToast(t('backendRestart'), 'error');
    }
  }
}

function findFile(path) {
  return state.files.find((f) => f.path === path) || null;
}

function populateBackends(names, defaultLangs) {
  const sel = $('ocr-backend');
  sel.innerHTML = '';
  if (!names.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = t('noBackends');
    sel.appendChild(opt);
    sel.disabled = true;
    return;
  }
  sel.disabled = false;
  for (const n of names) {
    const opt = document.createElement('option');
    opt.value = n;
    opt.textContent = n;
    sel.appendChild(opt);
  }
  if (defaultLangs && defaultLangs.length) {
    $('ocr-lang').value = defaultLangs.join(',');
  }
}

function updateProgress(pct) {
  $('progress-fill').style.width = Math.max(0, Math.min(100, pct)) + '%';
  $('progress-pct').textContent = Math.round(pct) + '%';
}

function updateProgressLive() {
  if (!state.converting) return;
  const done = state.files.filter((f) => f.status === 'ok' || f.status === 'error').length;
  const pct = (done / state.files.length) * 100;
  updateProgress(pct);
  setStatusLine(t('converting') + '… ' + done + '/' + state.files.length);
}

function finishConversion(okCount, errCount) {
  if (!state.converting) return;
  state.converting = false;
  $('convert-btn').disabled = false;
  $('progress-wrap').hidden = true;
  for (const f of state.files) {
    if (f.status === 'converting') f.status = 'pending';
  }
  renderFiles();
  const msg = t('batchDoneOk', { ok: okCount, err: errCount });
  setStatusLine(msg, errCount > 0 ? (okCount > 0 ? '' : 'error') : 'ok');
  if (errCount > 0) showToast(msg, 'error');
  else showToast(msg, 'ok');
  if (okCount > 0 && state.dest) {
    $('dest-open').classList.add('emphasized');
  }
}

function startConversion() {
  const pending = state.files.filter((f) => f.status !== 'ok');
  if (pending.length === 0) return;

  let dest = state.dest.trim();
  if (!dest) {
    dest = dirOf(pending[0].path);
    state.dest = dest;
    $('dest-input').value = dest;
    showToast(t('destAuto'));
  }

  state.converting = true;
  $('convert-btn').disabled = true;
  $('progress-wrap').hidden = false;
  updateProgress(0);
  setStatusLine(t('converting') + '…');

  const langs = $('ocr-lang').value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);

  const req = {
    cmd: 'convert',
    paths: pending.map((f) => f.path),
    output: dest,
    recursive: false,
    overwrite: false,
    include: null,
    ocr: { enabled: state.ocrOn, languages: langs },
    backend: $('ocr-backend').value || null,
  };

  window.api
    .requestBackend(req)
    .then((resp) => {
      if (resp && resp.type === 'batch_done') {
        finishConversion(resp.ok || 0, resp.err || 0);
      } else if (resp && resp.type === 'error') {
        state.converting = false;
        $('convert-btn').disabled = false;
        $('progress-wrap').hidden = true;
        setStatusLine(resp.message || 'Error', 'error');
      }
    })
    .catch((err) => {
      state.converting = false;
      $('convert-btn').disabled = false;
      $('progress-wrap').hidden = true;
      setStatusLine(t('backendError', { msg: err.message }), 'error');
    });
}

/* ===== Events & wiring ===== */
function wireEvents() {
  const dz = $('drop-zone');
  let dragDepth = 0;

  dz.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    dz.classList.add('dragover');
  });
  dz.addEventListener('dragenter', (e) => {
    e.preventDefault();
    dragDepth++;
    dz.classList.add('dragover');
  });
  dz.addEventListener('dragleave', () => {
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) dz.classList.remove('dragover');
  });
  dz.addEventListener('drop', (e) => {
    e.preventDefault();
    dragDepth = 0;
    dz.classList.remove('dragover');
    const files = [...e.dataTransfer.files];
    const paths = [];
    for (const f of files) {
      try {
        const p = window.api.getPathForFile(f);
        if (p) paths.push(p);
      } catch {
        // file has no path (e.g. dropped from browser) -> ignore
      }
    }
    if (paths.length) addFiles(paths);
  });
  dz.addEventListener('click', async () => {
    const paths = await window.api.pickFiles();
    if (paths.length) addFiles(paths);
  });

  document.addEventListener('keydown', (e) => {
    if ((e.key === 'Delete' || e.key === 'Backspace') && state.selected.size > 0) {
      e.preventDefault();
      removeSelected();
    }
  });

  $('remove-selected').addEventListener('click', removeSelected);

  $('dest-browse').addEventListener('click', async () => {
    const dir = await window.api.pickFolder();
    if (dir) {
      state.dest = dir;
      $('dest-input').value = dir;
    }
  });

  $('dest-open').addEventListener('click', async () => {
    if (!state.dest) return;
    const ok = await window.api.openPath(state.dest);
    if (!ok) showToast(t('destMissing'), 'error');
  });

  $('ocr-toggle').addEventListener('change', () => {
    state.ocrOn = $('ocr-toggle').checked;
    $('ocr-controls').style.opacity = state.ocrOn ? '1' : '0.4';
    $('ocr-controls').style.pointerEvents = state.ocrOn ? 'auto' : 'none';
  });

  $('convert-btn').addEventListener('click', startConversion);

  document.querySelectorAll('.lang-btn').forEach((b) => {
    b.addEventListener('click', () => applyLanguage(b.dataset.lang));
  });
}

/* ===== Boot ===== */
(async function boot() {
  wireEvents();
  applyLanguage('en');
  try {
    const locale = await window.api.getLocale();
    applyLanguage(locale);
  } catch { /* keep default */ }
  try {
    const ver = await window.api.getVersion();
    $('app-version').textContent = 'v' + ver;
  } catch { /* ignore */ }
  window.api.onBackendEvent(handleEvent);
  await initBackend();
})();