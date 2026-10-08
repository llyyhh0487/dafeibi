# -*- coding: utf-8 -*-
"""
生成「菲比啾比 · 切句打点工具」单文件 HTML
==========================================
把两个音频以 base64 内嵌进 HTML，双击即可打开（file:// 可用，不需要服务器）。

用法：python tools/make_sfx_marker.py
输出：桌面/菲比切句工具.html

工具里的操作：
  Enter      播放 / 暂停
  Space      在当前位置插一个切点（听到句子结尾就按）
  Backspace  撤销上一个切点
  点击波形    跳转；拖动波形  擦洗
  1/2/3      播放速度 1x / 0.75x / 0.5x
导出 JSON（含每段起止时间），回合到脚本即可。
"""
import base64
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(os.path.expanduser("~"), "Desktop", "tmp")
OUT = os.path.join(os.path.expanduser("~"), "Desktop", "菲比切句工具.html")

TRACKS = [
    ("jubi", "菲比啾比", "菲比啾比纯享版_音频.mp4"),
    ("bibi", "菲比比",   "菲比比？纯享版（番外）_音频.mp4"),
]

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>菲比啾比 · 切句打点工具</title>
<style>
  :root { --bg:#14161a; --panel:#1d2026; --line:#2c3038; --fg:#e8eaee; --dim:#8b93a1;
          --accent:#4da3ff; --mark:#22c55e; --warn:#f59e0b; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font:14px/1.5 system-ui,-apple-system,"Microsoft YaHei",sans-serif; }
  header { padding:14px 20px; border-bottom:1px solid var(--line); }
  h1 { margin:0 0 4px; font-size:17px; }
  .ver { font-size:12px; color:var(--dim); font-weight:400; margin-left:8px; }
  .hint { margin:0; color:var(--dim); font-size:13px; }
  .hint b { color:var(--accent); }
  .tabs { display:flex; gap:8px; padding:12px 20px 0; }
  .tab { padding:7px 16px; border:1px solid var(--line); border-radius:8px 8px 0 0;
         background:var(--panel); color:var(--dim); cursor:pointer; font-size:14px; }
  .tab.on { color:var(--fg); border-bottom-color:var(--panel); background:#242832; }
  .wrap { padding:0 20px 28px; }
  .wavebox { position:relative; background:var(--panel); border:1px solid var(--line);
             border-radius:0 8px 8px 8px; overflow:hidden; }
  canvas { display:block; width:100%; height:190px; cursor:crosshair; }
  .ruler { display:flex; justify-content:space-between; color:var(--dim);
           font-size:12px; padding:2px 4px 0; }
  .bar { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin:12px 0; }
  button { background:#2a2f3a; color:var(--fg); border:1px solid var(--line);
           border-radius:7px; padding:7px 14px; cursor:pointer; font-size:13px; }
  button:hover { background:#333a47; }
  button.pri { background:var(--accent); border-color:var(--accent); color:#06121f; font-weight:600; }
  button.seg { background:#22303f; border-color:#2f465e; }
  .pill { color:var(--dim); font-size:13px; }
  .pill b { color:var(--fg); font-variant-numeric:tabular-nums; }
  .rates { display:inline-flex; gap:6px; }
  .rates button { padding:5px 11px; font-size:12.5px; }
  .rates button.on { background:var(--accent); border-color:var(--accent);
                     color:#06121f; font-weight:700; }
  .grid { display:grid; grid-template-columns:1fr 320px; gap:16px; align-items:start; }
  .panel { background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:10px 12px; }
  .panel h3 { margin:0 0 8px; font-size:13px; color:var(--dim); font-weight:600; }
  .segs { max-height:300px; overflow:auto; font-variant-numeric:tabular-nums; }
  .seg { display:flex; gap:8px; padding:3px 6px; border-radius:5px; cursor:pointer; font-size:12.5px; }
  .seg:hover { background:#262b35; }
  .seg .i { color:var(--dim); width:26px; }
  .seg .t { width:132px; }
  .seg .d { width:58px; }
  .seg.bad .d { color:var(--warn); }
  .seg.bad { background:rgba(245,158,11,.08); }
  textarea { width:100%; height:120px; background:#0f1115; color:var(--fg);
             border:1px solid var(--line); border-radius:7px; padding:8px;
             font:12px/1.5 ui-monospace,Consolas,monospace; resize:vertical; }
  .ok { color:var(--mark); } .no { color:var(--warn); }
</style>
</head>
<body>
<header>
  <h1>菲比啾比 · 切句打点工具<span class="ver">v2 · 生成于 __BUILT__</span></h1>
  <p class="hint">
    <b>Enter</b> 播放/暂停 &nbsp;·&nbsp; <b>空格</b> 打点（会自动吸到能量谷底） &nbsp;·&nbsp;
    <b>← →</b> 微调最近的切点 &nbsp;·&nbsp; <b>Backspace</b> 撤销 &nbsp;·&nbsp;
    点击波形跳转/拖动擦洗 &nbsp;·&nbsp; 速度按钮或 <b>1/2/3/4</b>
  </p>
</header>

<div class="tabs" id="tabs"></div>
<div class="wrap">
  <div class="wavebox"><canvas id="wave"></canvas></div>
  <div class="ruler"><span id="r0">0:00.000</span><span id="r1">0:00.000</span></div>

  <div class="bar">
    <button class="pri" id="play">▶ 播放</button>
    <button id="mark">✂ 打点 (空格)</button>
    <button id="undo">↶ 撤销</button>
    <button id="clear">清空</button>
    <span style="width:14px"></span>
    <button id="zin">放大</button>
    <button id="zout">缩小</button>
    <button id="zall">全览</button>
    <span style="width:14px"></span>
    <button class="seg" id="audition">▶ 顺序试听所有段</button>
    <span class="pill">速度</span><span class="rates" id="rates"></span>
    <span class="pill">位置 <b id="pos">0:00.000</b></span>
    <span class="pill" id="flash" style="min-width:150px"></span>
  </div>
  <div class="bar" style="margin-top:-4px">
    <span class="pill">吸附</span>
    <label class="pill"><input type="checkbox" id="snapOn" checked> 打点时自动吸到最近的能量谷底（补偿你的反应延迟）</label>
    <button id="snapAll">对已有切点全部重吸</button>
    <span style="width:14px"></span>
    <span class="pill">微调最近切点：<b>← →</b> 5ms &nbsp;<b>Shift+← →</b> 1ms</span>
    <span style="width:14px"></span>
    <button id="importBtn">载入 JSON</button>
    <input type="file" id="importFile" accept=".json,application/json" hidden>
    <span class="pill" id="saveState"></span>
  </div>
  <div class="bar" style="margin-top:-4px">
    <label class="pill"><input type="checkbox" id="loopSeg"> 循环当前段</label>
    <span class="pill">← 点下面「这一段切得怎么样」里的任意一行就开始循环该段，再用 <b>← →</b> 微调，直到听不出被切断</span>
  </div>

  <div class="grid">
    <div class="panel">
      <h3>这一段切得怎么样（点任意一行试听该段；黄色=时长可疑，可能切错或漏切）</h3>
      <div class="segs" id="segs"></div>
    </div>
    <div class="panel">
      <h3>导出结果（回合给我即可）</h3>
      <div class="bar" style="margin:0 0 8px">
        <button id="copy">复制 JSON</button>
        <button id="dl">下载 JSON</button>
        <span class="pill" id="stat"></span>
      </div>
      <textarea id="out" readonly placeholder="标完点这里看结果"></textarea>
    </div>
  </div>
</div>

<script>
const TRACKS = __TRACKS__;

const ctx = new (window.AudioContext || window.webkitAudioContext)();
const cv = document.getElementById('wave');
const g = cv.getContext('2d');
let W = 0, H = 0;

let cur = 0;                       // 当前音轨索引
const state = TRACKS.map(() => ({ ab:null, peaks:null, marks:[], added:[], view:null, src:null }));
let playing = false, startedAt = 0, startOffset = 0, rate = 1, raf = 0;
let auditioning = false, auditionToken = 0, loopRange = null;

function b64buf(b64) {
  const bin = atob(b64);
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u.buffer;
}
const fmt = t => {
  t = Math.max(0, t);
  const m = Math.floor(t / 60), s = t - m * 60;
  return m + ':' + (s < 10 ? '0' : '') + s.toFixed(3);
};

/* ---------- 解码 + 峰值 ---------- */
async function load() {
  for (let i = 0; i < TRACKS.length; i++) {
    const ab = await ctx.decodeAudioData(b64buf(TRACKS[i].b64));
    const n = ab.length, ch = [];
    for (let c = 0; c < ab.numberOfChannels; c++) ch.push(ab.getChannelData(c));
    const per = Math.round(ab.sampleRate * 0.005);         // 5ms 一格
    const cnt = Math.ceil(n / per);
    const pk = new Float32Array(cnt);
    for (let k = 0; k < cnt; k++) {
      let mx = 0;
      const e = Math.min(n, (k + 1) * per);
      for (let c = 0; c < ch.length; c++) {
        const d = ch[c];
        for (let j = k * per; j < e; j += 2) { const v = d[j] < 0 ? -d[j] : d[j]; if (v > mx) mx = v; }
      }
      pk[k] = mx;
    }
    state[i].ab = ab; state[i].peaks = pk;

    // RMS 包络（10ms + 50ms 平滑）：打点时把切点吸附到"能量谷底"，
    // 用来抵消人工按键 150~250ms 的反应延迟。
    const hop = Math.round(ab.sampleRate * 0.01);
    const fn = Math.floor(n / hop);
    const env = new Float32Array(fn);
    for (let f = 0; f < fn; f++) {
      let s = 0, c = 0;
      const e = Math.min(n, (f + 1) * hop);
      for (let c2 = 0; c2 < ch.length; c2++) {
        const d = ch[c2];
        for (let j = f * hop; j < e; j++) { s += d[j] * d[j]; c++; }
      }
      env[f] = Math.sqrt(s / Math.max(1, c));
    }
    const sm = new Float32Array(fn);
    for (let f = 0; f < fn; f++) {
      let s = 0, c = 0;
      for (let k = -2; k <= 2; k++) { const j = f + k; if (j >= 0 && j < fn) { s += env[j]; c++; } }
      sm[f] = s / c;
    }
    state[i].env = sm; state[i].envHop = 0.01;

    state[i].view = { start: 0, span: ab.duration };
  }
  restore();
  buildTabs(); buildRates(); resize(); draw(); refresh();
}

/* ---------- 尺寸 ---------- */
function resize() {
  const dpr = Math.min(2, window.devicePixelRatio || 1);
  const r = cv.getBoundingClientRect();
  W = Math.max(1, Math.round(r.width * dpr));
  H = Math.max(1, Math.round(r.height * dpr));
  cv.width = W; cv.height = H;
  draw();
}
window.addEventListener('resize', resize);

/* ---------- 绘制 ---------- */
function xOf(t) { const v = state[cur].view; return (t - v.start) / v.span * W; }
function tOf(x) { const v = state[cur].view; return v.start + (x / W) * v.span; }

function draw() {
  const st = state[cur], ab = st.ab;
  if (!ab) return;
  const v = st.view, dur = ab.duration;
  g.clearRect(0, 0, W, H);
  g.fillStyle = '#1d2026'; g.fillRect(0, 0, W, H);

  // 网格 + 刻度
  const stepChoices = [0.1,0.2,0.5,1,2,5,10,30];
  let step = stepChoices.find(s => v.span / s <= 22) || 30;
  g.font = (11 * (W / (cv.getBoundingClientRect().width || W))) + 'px sans-serif';
  for (let t = Math.floor(v.start / step) * step; t <= v.start + v.span; t += step) {
    const x = xOf(t);
    g.strokeStyle = '#242932'; g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke();
    g.fillStyle = '#6b7484'; g.fillText(t.toFixed(2) + 's', x + 3, H - 5);
  }

  // 波形
  const mid = H / 2, pk = st.peaks, per = 0.005, cnt = pk.length;
  g.strokeStyle = '#4da3ff'; g.lineWidth = 1; g.beginPath();
  for (let x = 0; x < W; x++) {
    const t0 = tOf(x), t1 = tOf(x + 1);
    let k0 = Math.max(0, Math.floor(t0 / per)), k1 = Math.min(cnt - 1, Math.ceil(t1 / per));
    let mx = 0;
    for (let k = k0; k <= k1; k++) if (pk[k] > mx) mx = pk[k];
    const h = mx * (H * 0.46);
    g.moveTo(x + 0.5, mid - h); g.lineTo(x + 0.5, mid + h);
  }
  g.stroke();

  // 切点
  const segs = segments();
  g.font = '11px sans-serif';
  st.marks.forEach((t, i) => {
    const x = xOf(t);
    g.strokeStyle = '#22c55e'; g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke();
    g.fillStyle = '#22c55e'; g.fillText(String(i + 1), x + 3, 13);
  });

  // 播放头
  if (playing) {
    const x = xOf(pos());
    g.strokeStyle = '#ff3b5c'; g.lineWidth = 1.5;
    g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke();
  }
}

/* ---------- 播放 ---------- */
function stopSrc() {
  if (state[cur].src) { try { state[cur].src.onended = null; state[cur].src.stop(); } catch (e) {} state[cur].src = null; }
}
function pos() {
  if (!playing) return startOffset;
  return Math.min(state[cur].ab.duration, startOffset + (ctx.currentTime - startedAt) * rate);
}
function play(from) {
  const st = state[cur];
  stopSrc(); auditionToken++;
  startOffset = from === undefined ? startOffset : from;
  if (startOffset >= st.ab.duration - 0.01) startOffset = 0;
  const s = ctx.createBufferSource();
  s.buffer = st.ab; s.playbackRate.value = rate;
  s.connect(ctx.destination);
  s.start(0, startOffset);
  st.src = s;
  startedAt = ctx.currentTime; playing = true;
  s.onended = () => { if (st.src === s) { playing = false; startOffset = st.ab.duration; stopSrc(); sync(); } };
  sync();
}
function pause() { startOffset = pos(); playing = false; stopSrc(); sync(); }
function seek(t) { startOffset = Math.max(0, Math.min(state[cur].ab.duration, t)); if (playing) play(startOffset); else sync(); }

function sync() {
  document.getElementById('play').textContent = playing ? '❚❚ 暂停' : '▶ 播放';
  document.getElementById('pos').textContent = fmt(playing ? pos() : startOffset);
}

/* 速度：1x / 0.75x / 0.5x / 0.35x（界面按钮 + 键盘 1~4） */
const RATES = [1, 0.75, 0.5, 0.35];
function buildRates() {
  const box = document.getElementById('rates');
  box.innerHTML = '';
  RATES.forEach(r => {
    const b = document.createElement('button');
    b.textContent = r + 'x';
    if (r === rate) b.className = 'on';
    b.onclick = () => setRate(r);
    box.appendChild(b);
  });
}
function setRate(r) {
  const wasPlaying = playing;
  const at = playing ? pos() : startOffset;
  rate = r;
  if (wasPlaying) play(at);        // 播放中切换要按旧位置续播
  else { startOffset = at; sync(); }
  buildRates();
}

/* ---------- 分段 ---------- */
function segments() {
  const st = state[cur], dur = st.ab ? st.ab.duration : 0;
  const cuts = [0, ...st.marks.slice().sort((a, b) => a - b), dur];
  const out = [];
  for (let i = 0; i < cuts.length - 1; i++) out.push([cuts[i], cuts[i + 1]]);
  return out;
}

/* ---------- 交互 ---------- */
/* 把时间吸附到附近的能量谷底 —— 也就是句子之间/爆破音的自然间隙。
   窗口刻意做得不对称：人按键只会偏晚、不会偏早，所以主要往回找，
   往前只留一点点，免得吸到"下一个"谷底上去（那样误差反而更大）。 */
function snapTime(t) {
  const st = state[cur];
  if (!st.env || !document.getElementById('snapOn').checked) return { t, delta: 0 };
  const hop = st.envHop, N = st.env.length;
  const back = Math.round(0.20 / hop);
  const fwd  = Math.round(0.07 / hop);
  const c = Math.round(t / hop);
  const i0 = Math.max(0, c - back), i1 = Math.min(N - 1, c + fwd);
  let bi = i0, bv = Infinity;
  for (let i = i0; i <= i1; i++) if (st.env[i] < bv) { bv = st.env[i]; bi = i; }
  const nt = bi * hop;
  return { t: nt, delta: nt - t };
}

let flashTimer = 0;
function flash(msg, color) {
  const el = document.getElementById('flash');
  el.innerHTML = `<span style="color:${color || '#22c55e'}">${msg}</span>`;
  clearTimeout(flashTimer);
  flashTimer = setTimeout(() => { el.textContent = ''; }, 1800);
}

function mark() {
  const st = state[cur];
  const raw = playing ? pos() : startOffset;
  const s = snapTime(raw);
  if (st.marks.some(m => Math.abs(m - s.t) < 0.03)) return;
  st.marks.push(s.t); st.added.push(s.t);
  const ms = Math.round(s.delta * 1000);
  flash(ms === 0 ? '已打点（谷底就在附近）'
                 : `已打点 · 吸附 ${ms > 0 ? '+' : ''}${ms} ms`, '#22c55e');
  save(); draw(); refresh();
}
function undo() {
  const st = state[cur];
  if (!st.added.length) return;
  const t = st.added.pop();
  st.marks = st.marks.filter(m => Math.abs(m - t) > 1e-9);
  save(); draw(); refresh();
}

/* 微调离播放头最近的切点 */
function nudge(dt) {
  const st = state[cur];
  if (!st.marks.length) return;
  const p = playing ? pos() : startOffset;
  let bi = 0, bd = Infinity;
  st.marks.forEach((m, i) => { const d = Math.abs(m - p); if (d < bd) { bd = d; bi = i; } });
  const nt = Math.max(0, Math.min(st.ab.duration, st.marks[bi] + dt));
  const wasPlaying = playing;
  st.marks[bi] = nt;
  startOffset = nt;
  if (wasPlaying) play(nt); else sync();
  flash(`第 ${bi + 1} 个切点 ${dt > 0 ? '+' : ''}${Math.round(dt * 1000)}ms → ${nt.toFixed(3)}s`, '#4da3ff');
  save(); draw(); refresh();
}
function resnapAll() {
  const st = state[cur];
  const before = st.marks.slice();
  st.marks = st.marks.map(m => snapTime(m).t);
  st.added = st.marks.slice();
  let moved = 0;
  before.forEach((m, i) => { if (Math.abs(st.marks[i] - m) > 0.005) moved++; });
  save(); draw(); refresh();
  flash(`${moved} / ${st.marks.length} 个切点被重新吸附`, '#4da3ff');
}

/* 进度自动保存（关掉页面也不丢） */
const LSK = 'phoebe-marks-v1';
function save() {
  try {
    localStorage.setItem(LSK, JSON.stringify(TRACKS.map((t, i) => state[i].marks)));
    document.getElementById('saveState').innerHTML = '<span class="ok">已自动保存</span>';
  } catch (e) {
    document.getElementById('saveState').innerHTML = '<span class="no">无法自动保存，请点下载 JSON</span>';
  }
}
function restore() {
  try {
    const s = JSON.parse(localStorage.getItem(LSK) || 'null');
    let n = 0;
    if (Array.isArray(s)) s.forEach((m, i) => {
      if (state[i] && Array.isArray(m) && m.length) { state[i].marks = m.slice(); state[i].added = m.slice(); n += m.length; }
    });
    if (n) document.getElementById('saveState').innerHTML = `<span class="ok">已恢复上次进度（${n} 个切点）</span>`;
  } catch (e) {}
}

cv.addEventListener('pointerdown', e => {
  if (!state[cur].ab) return;
  const r = cv.getBoundingClientRect();
  const dpr = W / r.width;
  const t = tOf((e.clientX - r.left) * dpr);
  cv.dataset.drag = '1';
  seek(t); draw();
  // 先跳转再捕获指针：某些环境下 setPointerCapture 会抛异常，
  // 放在前面会把 seek 一起带走（点波形没反应）。
  try { cv.setPointerCapture(e.pointerId); } catch (err) {}
});
cv.addEventListener('pointermove', e => {
  if (cv.dataset.drag !== '1') return;
  const r = cv.getBoundingClientRect();
  const dpr = W / r.width;
  seek(tOf((e.clientX - r.left) * dpr)); draw();
});
cv.addEventListener('pointerup', () => { cv.dataset.drag = '0'; });

window.addEventListener('keydown', e => {
  if (e.target.tagName === 'TEXTAREA') return;
  if (e.code === 'Enter') { e.preventDefault(); playing ? pause() : play(); }
  else if (e.code === 'Space') { e.preventDefault(); mark(); }
  else if (e.code === 'Backspace') { e.preventDefault(); undo(); }
  else if (e.code === 'ArrowLeft')  { e.preventDefault(); nudge(e.shiftKey ? -0.001 : -0.005); }
  else if (e.code === 'ArrowRight') { e.preventDefault(); nudge(e.shiftKey ?  0.001 :  0.005); }
  else if (e.key >= '1' && e.key <= String(RATES.length)) {
    e.preventDefault(); setRate(RATES[Number(e.key) - 1]);
  }
});

document.getElementById('play').onclick = () => (playing ? pause() : play());
document.getElementById('mark').onclick = mark;
document.getElementById('undo').onclick = undo;
document.getElementById('clear').onclick = () => {
  state[cur].marks = []; state[cur].added = []; save(); draw(); refresh();
};
document.getElementById('snapAll').onclick = resnapAll;
document.getElementById('importBtn').onclick = () => document.getElementById('importFile').click();
document.getElementById('importFile').onchange = async ev => {
  const f = ev.target.files[0];
  if (!f) return;
  try {
    const j = JSON.parse(await f.text());
    TRACKS.forEach((t, i) => {
      const d = j[t.id];
      if (d && Array.isArray(d.marks)) { state[i].marks = d.marks.slice(); state[i].added = d.marks.slice(); }
    });
    save(); draw(); refresh();
    flash('已载入 JSON', '#4da3ff');
  } catch (e) { alert('读不出来：' + e.message); }
};
document.getElementById('zin').onclick = () => zoom(0.5);
document.getElementById('zout').onclick = () => zoom(2);
document.getElementById('zall').onclick = () => {
  state[cur].view = { start: 0, span: state[cur].ab.duration }; draw();
};
function zoom(f) {
  const st = state[cur], v = st.view, dur = st.ab.duration;
  const c = playing ? pos() : startOffset;
  let span = Math.max(0.4, Math.min(dur, v.span * f));
  let start = c - (c - v.start) * (span / v.span);
  start = Math.max(0, Math.min(dur - span, start));
  st.view = { start, span }; draw();
}

/* ---------- 顺序试听 ---------- */
document.getElementById('audition').onclick = async () => {
  if (auditioning) { auditioning = false; auditionToken++; stopSrc(); playing = false; sync(); return; }
  auditioning = true; playing = false;
  const token = ++auditionToken;
  const segs = segments();
  for (let i = 0; i < segs.length; i++) {
    if (!auditioning || token !== auditionToken) return;
    await playRange(segs[i][0], segs[i][1], token);
    await sleep(280);
  }
  auditioning = false; sync();
};
function playRange(a, b, token) {
  return new Promise(res => {
    const st = state[cur];
    stopSrc();
    const s = ctx.createBufferSource();
    s.buffer = st.ab; s.connect(ctx.destination);
    s.start(0, a, Math.max(0.05, b - a));
    st.src = s; playing = false; startOffset = a; sync();
    s.onended = () => { if (token === auditionToken) res(); };
    // 提示音
    setTimeout(() => {
      if (token !== auditionToken) return;
      const o = ctx.createOscillator(), gn = ctx.createGain();
      o.frequency.value = 1200; gn.gain.value = 0.05;
      o.connect(gn); gn.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.05);
    }, Math.max(0, (b - a) * 1000));
  });
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

/* ---------- 列表 / 导出 ---------- */
function refresh() {
  const st = state[cur];
  const segs = segments();
  const box = document.getElementById('segs');
  box.innerHTML = '';
  segs.forEach(([a, b], i) => {
    const d = b - a;
    const bad = d < 0.30 || d > 2.60;
    const row = document.createElement('div');
    row.className = 'seg' + (bad ? ' bad' : '');
    row.innerHTML = `<span class="i">${i + 1}</span><span class="t">${fmt(a)} → ${fmt(b)}</span>` +
                    `<span class="d">${d.toFixed(2)}s</span>`;
    row.onclick = () => {
      if (document.getElementById('loopSeg').checked) { loopRange = [a, b]; play(a); }
      else { loopRange = null; seek(a); play(a); }
    };
    box.appendChild(row);
  });
  const bad = segs.filter(([a, b]) => (b - a) < 0.30 || (b - a) > 2.60).length;
  document.getElementById('stat').innerHTML =
    `共 <b>${segs.length}</b> 段` + (bad ? ` · <span class="no">${bad} 段时长可疑</span>`
                                       : ` · <span class="ok">时长都正常</span>`);
  const json = {};
  TRACKS.forEach((t, i) => {
    json[t.id] = {
      file: t.file, duration: +state[i].ab.duration.toFixed(3),
      marks: state[i].marks.slice().sort((a, b) => a - b).map(m => +m.toFixed(3)),
      segments: segmentsOf(i).map(([a, b]) => [+a.toFixed(3), +b.toFixed(3)])
    };
  });
  document.getElementById('out').value = JSON.stringify(json, null, 1);
}
function segmentsOf(i) {
  const st = state[i], dur = st.ab.duration;
  const cuts = [0, ...st.marks.slice().sort((a, b) => a - b), dur];
  const out = [];
  for (let k = 0; k < cuts.length - 1; k++) out.push([cuts[k], cuts[k + 1]]);
  return out;
}

document.getElementById('copy').onclick = async () => {
  const ta = document.getElementById('out');
  ta.select();
  try { await navigator.clipboard.writeText(ta.value); alert('已复制，粘给我就行'); }
  catch (e) { document.execCommand('copy'); alert('已复制'); }
};
document.getElementById('dl').onclick = () => {
  const blob = new Blob([document.getElementById('out').value], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'phoebe-cuts.json'; a.click();
};

/* ---------- 音轨切换 ---------- */
function buildTabs() {
  const box = document.getElementById('tabs');
  box.innerHTML = '';
  TRACKS.forEach((t, i) => {
    const b = document.createElement('div');
    b.className = 'tab' + (i === cur ? ' on' : '');
    b.textContent = t.name;
    b.onclick = () => {
      playing = false; stopSrc(); auditioning = false; auditionToken++;
      cur = i; startOffset = 0; buildTabs(); refresh(); draw(); sync();
    };
    box.appendChild(b);
  });
}

/* ---------- 启动 ---------- */
load().then(() => {
  setInterval(() => {
    if (playing) {
      // 循环当前段（微调时用）
      if (loopRange && pos() >= loopRange[1] - 0.005) { play(loopRange[0]); }
      draw(); sync();
    }
    const v = state[cur].view;
    if (playing) {                              // 放大时视图跟随播放头
      const p = pos();
      if (v.span < state[cur].ab.duration) {
        if (p < v.start || p > v.start + v.span) {
          state[cur].view.start = Math.max(0, Math.min(state[cur].ab.duration - v.span, p - v.span / 2));
        }
      }
    }
    document.getElementById('r0').textContent = fmt(state[cur].view.start);
    document.getElementById('r1').textContent = fmt(state[cur].view.start + state[cur].view.span);
  }, 50);
});
</script>
</body>
</html>
"""


def main():
    tracks = []
    for tid, name, fname in TRACKS:
        p = os.path.join(SRC_DIR, fname)
        if not os.path.exists(p):
            print(f"  缺少文件: {p}")
            return 1
        raw = open(p, "rb").read()
        tracks.append({
            "id": tid, "name": name, "file": fname,
            "b64": base64.b64encode(raw).decode("ascii"),
        })
        print(f"  {name:<8} {fname}  {len(raw)/1024:.0f} KB")

    import json
    import datetime
    html = HTML.replace("__TRACKS__", json.dumps(tracks, ensure_ascii=False))
    html = html.replace("__BUILT__", datetime.datetime.now().strftime("%m-%d %H:%M"))
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print(f"\n  -> {OUT}  ({os.path.getsize(OUT)/1024/1024:.2f} MB)")
    print("     双击就能打开，不需要服务器。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
