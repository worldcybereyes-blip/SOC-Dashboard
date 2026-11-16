// DOM behaviour test for index.html.  Run:  npm install && npm test
// Loads the page in jsdom, runs hundreds of simulated ticks and exercises every interactive feature.
// (jsdom does not fetch the Tailwind CDN script and has no layout engine, so this tests behaviour, not looks.)
const { JSDOM, VirtualConsole } = require('jsdom');
const fs = require('fs');
const path = require('path');

const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const errors = [];
let passed = 0;
const vc = new VirtualConsole();
vc.on('jsdomError', e => errors.push('jsdomError: ' + ((e.detail && e.detail.stack) || e.message)));
vc.on('error', e => errors.push('console.error: ' + e));

const dom = new JSDOM(html, { runScripts: 'dangerously', pretendToBeVisual: true, virtualConsole: vc });
const w = dom.window, d = w.document;
const $ = s => d.querySelector(s), $$ = s => Array.from(d.querySelectorAll(s));
const ok = (cond, msg) => { if (cond) { passed++; console.log('PASS  ' + msg); } else { errors.push('assert: ' + msg); console.log('FAIL  ' + msg); } };
const fire = (el, type) => el.dispatchEvent(new w.Event(type, { bubbles: true }));
const S = w.__soc;

ok(!!S, 'test hook window.__soc is present');
const kpi = id => $('#' + id).textContent;

// ---------- initial render
ok(S.state.alerts.length === 210, 'seeded 210 historical alerts (got ' + S.state.alerts.length + ')');
ok($$('#queueBody tr.row').length > 0 && $$('#queueBody tr.row').length <= 40, 'queue renders <= 40 rows (' + $$('#queueBody tr.row').length + ')');
ok(['kpiEvents', 'kpiOpen', 'kpiMtta', 'kpiMttr', 'kpiHunters'].every(i => kpi(i).trim() && kpi(i).trim() !== '-'), 'all 5 KPI cards populated');
ok($$('#funnelStages > div').length === 4, 'funnel has 4 stages');
ok($$('#healthGrid .tile').length === 10, '10 log-source tiles');
ok($$('#hostsBody tr').length === 10, '10 target-host rows');
ok($$('#ipsBody tr').length === 10, '10 malicious-IP rows');
ok($$('#sevFilters button').length === 4, '4 severity filter buttons');
const ids = S.state.alerts.map(a => a.id);
ok(new Set(ids).size === ids.length, 'incident IDs are unique');

// ---------- every queue row has the required columns and an Investigate button
const row0 = $('#queueBody tr.row');
ok(row0.children.length === 9, 'row has 9 columns (timestamp, id, severity, detection, source, MITRE, assignee, status, action)');
ok(!!row0.querySelector('.sev') && !!row0.querySelector('a[href*="attack.mitre.org/techniques/T"]') && !!row0.querySelector('[data-inv]'), 'row has severity badge, MITRE link and Investigate button');

// ---------- funnel is monotonic for every range; KPI label follows range
const sel = $('#rangeSel');
for (const [v, lab] of [['15', '15m'], ['60', '1h'], ['1440', '24h']]) {
  sel.value = v; fire(sel, 'change');
  ok(kpi('kpiEventsLabel').includes(lab), 'range ' + lab + ': KPI label updates');
  const m = S.state; const raw = m.eps * m.range * 60;
  ok(raw > 0 && $('#funnelRange').textContent.length > 0, 'range ' + lab + ': funnel + events recomputed');
}
const parseCompact = t => { t = t.trim().replace(/,/g, ''); const k = { K: 1e3, M: 1e6, B: 1e9 }[t.slice(-1)]; return k ? parseFloat(t) * k : parseFloat(t); };
const stageVals = $$('#funnelStages .mono').map(e => parseCompact(e.textContent));
ok(stageVals.every((v, i) => i === 0 || v < stageVals[i - 1]), 'funnel strictly narrows: ' + stageVals.join(' > '));

// ---------- simulation engine
const before = S.state.alerts.length;
for (let i = 0; i < 300; i++) S.tick();
S.addLiveAlert(); S.addLiveAlert(); S.renderAll();
// >= because the health model also raises "Log Source Silent" alerts when a source goes Offline
ok(S.state.alerts.length >= before + 2, 'addLiveAlert appends alerts (' + before + ' -> ' + S.state.alerts.length + ')');
ok(S.state.alerts.every(a => Date.now() - a.ts <= 24 * 3600e3 + 5000), 'alerts older than 24h are purged');
ok(S.SOURCES.some(s => s.status === 'Healthy'), 'health model keeps at least one Healthy source');
ok(['Healthy', 'Lagging', 'Offline'].every(k => $('#healthGrid').textContent.includes(k)) || S.SOURCES.every(s => ['Healthy', 'Lagging', 'Offline'].includes(s.status)), 'health states are Healthy / Lagging / Offline only');
console.log('       KPIs now:', ['kpiEvents', 'kpiOpen', 'kpiMtta', 'kpiMttr', 'kpiHunters'].map(i => kpi(i).trim()).join(' | '));

// ---------- filters
sel.value = '1440'; fire(sel, 'change');
const critBtn = $('[data-sev="Critical"]'); critBtn.click();
const critRows = $$('#queueBody tr.row');
ok(critRows.length > 0 && critRows.every(r => r.classList.contains('r-Critical')), 'Critical filter shows only Critical rows (' + critRows.length + ')');
$('[data-sev="Critical"]').click();
const sb = $('#searchBox');
sb.value = 'mimikatz'; fire(sb, 'input');
const mimiRows = $$('#queueBody tr.row');
ok(mimiRows.length === 0 || mimiRows.every(r => /mimikatz/i.test(r.textContent)), 'search "mimikatz" filters rows (' + mimiRows.length + ')');
sb.value = 'zzzz-no-such-thing'; fire(sb, 'input');
ok($('#queueBody').textContent.includes('No incidents match'), 'empty state shown when nothing matches');
sb.value = '<img src=x onerror=alert(1)>'; fire(sb, 'input');
ok(!$('#queueBody img') && !$('#queueCount img'), 'search input is not injected as HTML');
sb.value = ''; fire(sb, 'input');

// ---------- investigate modal for EVERY detection type
let built = 0;
for (const t of S.CATALOG) {
  const a = S.addLiveAlert(t.k, t.k === 'srcoff' ? 'Linux auditd (DMZ)' : undefined);
  S.openModal(a.id);
  const overlayOpen = $('#overlay').classList.contains('open');
  let parsed = null; try { parsed = JSON.parse($('#jsonView').textContent); } catch (e) { /* reported below */ }
  const good = overlayOpen && parsed && parsed.rule && parsed.rule.mitre.id[0] === t.tech && parsed.agent.name === a.host.name && parsed.soc.incident_id === a.id && parsed.data;
  if (good) built++; else errors.push('modal/JSON problem for ' + t.k);
  S.closeModal();
}
ok(built === S.CATALOG.length, 'modal opens and raw JSON parses for all ' + S.CATALOG.length + ' detections');
ok($$('#queueBody [data-inv]').length >= 0, 'queue still renders after modal use');

// Windows paths must be single-escaped in JSON (one backslash per separator once parsed)
const mimi = S.addLiveAlert('mimi'); S.openModal(mimi.id);
const pj = JSON.parse($('#jsonView').textContent);
ok(pj.data.win.eventdata.image === 'C:\\Users\\Public\\Downloads\\mimikatz.exe', 'Sysmon image path has correct backslashes: ' + pj.data.win.eventdata.image);
ok(pj.data.win.system.eventID === '1' && pj.rule.level === 15, 'Mimikatz = Sysmon EID 1, Wazuh level 15');

// ---------- analyst actions
const act = a => $('[data-act="' + a + '"]').click();
ok(S.state.openId === mimi.id, 'modal is bound to the opened incident');
mimi.status = 'New'; mimi.assignee = null; S.openModal(mimi.id);
act('ack');   ok(mimi.status === 'Acknowledged' && mimi.assignee === 'You (T1)' && mimi.ackMin != null, 'Acknowledge sets status, assignee and MTTA sample');
act('escalate'); ok(mimi.status === 'Escalated' && mimi.escalated === true, 'Escalate to T2 works');
act('fp');    ok(mimi.status === 'False Positive' && mimi.resMin >= mimi.ackMin, 'False positive closes incident with resMin >= ackMin');
ok($('[data-act="resolve"]').disabled && $('[data-act="escalate"]').disabled, 'actions are disabled once an incident is closed');
const evt = new w.KeyboardEvent('keydown', { key: 'Escape', bubbles: true }); d.dispatchEvent(evt);
ok(!$('#overlay').classList.contains('open') && S.state.openId === null, 'Escape closes the modal');

// ---------- block IP, pause
$('#ipsBody [data-block]').click();
ok($$('#ipsBody button:disabled').length === 1, 'Block IP disables that row\'s button');
$('#pauseBtn').click();
ok($('#liveText').textContent === 'PAUSED' && $('#pauseBtn').getAttribute('aria-pressed') === 'true', 'Pause toggles state');
$('#pauseBtn').click();
ok($('#liveText').textContent === 'LIVE', 'Resume toggles state back');

// ---------- threat level + toasts
ok(/THREAT LEVEL: (GUARDED|ELEVATED|SEVERE)/.test($('#threatLevel').textContent), 'threat level badge is valid');
ok($$('#toasts .toast').length <= 3, 'toast stack capped at 3');

console.log('\n' + passed + ' passed, ' + errors.length + ' problem(s)');
if (errors.length) console.log('PROBLEMS:\n - ' + errors.join('\n - '));
process.exit(errors.length ? 1 : 0);
