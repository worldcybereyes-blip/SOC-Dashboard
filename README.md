SOC Command Center: Project Report

Step-by-step analysis of how the dashboard was designed, built, tested and packaged.

Prepared for: Rushikesh Kulkarni  |  Date: 07 November 2026  |  Deliverable: `index.html` (1022 lines, single file)

Contents

1. [1. Purpose and scope](#purpose-and-scope)
2. [2. Design decisions](#design-decisions)
3. [3. Architecture](#architecture)
4. [4. Step-by-step build](#step-by-step-build)
5. [5. Testing and verification](#testing-and-verification)
6. [6. Packaging and GitHub](#packaging-and-github)
7. [7. Limitations and next steps](#limitations-and-next-steps)
8. [Appendix A. Simulation parameters](#appendix-a-simulation-parameters)
9. [Appendix B. Glossary](#appendix-b-glossary)
10. [Appendix C. Project files](#appendix-c-project-files)


1. Purpose and scope

This report explains, in the order the work was done, how the SOC Command Center dashboard was designed, built, tested and packaged. It is written so that a junior analyst or developer can read it next to the code and follow every decision. Every code excerpt is extracted from the real `index.html` when the report is generated, so the report and the code cannot drift apart.

The deliverable is one self-contained file, `index.html` (1022 lines, about 688 of them JavaScript). It uses Tailwind CSS from a CDN and plain JavaScript with no framework and no build step: save the file, double-click it, and it runs. All data is generated in the browser by a simulation engine that stands in for a SIEM, so nothing is collected, stored or transmitted.


1.1 Who the dashboard is for

A Tier-1 analyst needs to answer three questions in seconds: what is on fire, what should I take next, and can I trust my data? A Tier-2 analyst needs the evidence behind an escalation. The layout follows that order: KPIs and funnel (health of the operation), the live queue (what to work), the intel and log panels (context), the ingestion monitor (trust), and a drill-down with raw JSON (evidence).


1.2 Requirements traceability

| Requirement | How it is met | Where |
|---|---|---|
| Cyber-security dark mode (#0d1117 / #0f172a) | Design tokens `--bg:#0d1117`, `--panel:#0f172a`; panels use a subtle gradient and 1px hairlines | CSS :root, .panel |
| Severity colour coding | Critical neon red/magenta `#ff2e63` with glow, High orange `#ff8a1f`, Medium yellow `#facc15`, Low blue `#38bdf8`, OK green `#22c55e`. Colour is backed by text labels and a left row border | .sev-*, tr.row.r-* |
| Tight, scannable layout | 12px base type, 4px row padding, monospace for IDs/IPs/times, 12-column grid, sticky table headers | body, td, .grid-cols-12 |
| Top KPI banner (5 cards) | Total Events, Open Incidents, MTTA, MTTR, Active Threat Hunters, each with a sparkline and SLA hint | renderKpis() |
| Alert funnel | Raw Logs > Filtered Events > Triaged Alerts > Escalated Incidents, log-scaled taper with % dropped | renderFunnel() |
| Live alert queue | Timestamp, Incident ID, Severity badge, Source IP/Host, MITRE technique, Assignee, Status, Investigate button; severity filters and free-text search | renderQueue() |
| Top Target Hosts / Failed Logins (4625/4624) | Ten hosts ranked by failed logons, success count, fail ratio bar, targeted account, burst signal | renderHosts() |
| Top Malicious Source IPs with geo | Ten IPs with country/city, ASN/org, tags, hits, reputation score and a Block button | renderIps() |
| Log Ingestion Health | Ten sources (Wazuh, Sysmon, CrowdStrike, firewall, ...) with Healthy / Lagging / Offline state, lag, EPS, uptime and sparkline | renderHealth(), tickHealth() |
| Global time-range selector | 15m / 1h / 24h dropdown re-scales events, queue window, funnel, hosts and IPs; remembered in localStorage | #rangeSel |
| Simulation engine | New alert every 3.5-8 s, statuses advance every 3 s, hosts surge, sources degrade and recover | section 6 of the script |
| Investigate drill-down with raw JSON | Modal with summary, timeline, playbook, analyst actions and a syntax-highlighted Wazuh-style JSON log with Copy and Wrap | openModal(), renderModal() |
| CDN only, runs by double-click | Tailwind 4.1.11 pinned on jsDelivr, fonts from Google Fonts with system fallbacks | <head> |


2. Design decisions


2.1 One file, one dependency

A SOC wall display is often a locked-down kiosk, so the dashboard avoids anything that needs installing. Tailwind is loaded with the browser build (`@tailwindcss/browser@4.1.11`, a pinned version so a CDN update cannot change the look). Everything bespoke (severity badges, table styling, modal, sparklines) lives in one `<style>` block driven by CSS variables, and Tailwind utilities are used only for layout and spacing.

> Note. Offline behaviour: if the Tailwind CDN is unreachable the grid utilities are lost and the page degrades to a single column, but the custom components still render and the JavaScript still runs. For an air-gapped SOC, download `index.global.js` once and change the one `<script src>` line.


2.2 Colour tokens

Design tokens (CSS)

```css
:root {
  --bg: #0d1117;
  --panel: #0f172a;
  --panel-2: #131c31;
  --line: #1e293b;
  --line-2: #2a3a55;
  --text: #e2e8f0;
  --muted: #8b9bb4;
  --accent: #22d3ee;
  --crit: #ff2e63;   /* neon red / magenta */
  --high: #ff8a1f;   /* orange */
  --med:  #facc15;   /* yellow */
  --low:  #38bdf8;   /* blue */
  --ok:   #22c55e;   /* green */
  --font-sans: 'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, 'Cascadia Mono', Consolas, Menlo, monospace;
}
```

The four severities are not just colours. Each has a text label, a left border on the table row, and (for Critical) a glow and a faint row tint. A colour-blind analyst, or a printout in greyscale, still reads the severity correctly.


2.3 Density without clutter

- Base font 12px, table cells 4px vertical padding, uppercase 10px column headers: about 40 queue rows fit on one 1080p screen next to the health panel.
- Secondary information (relative time "4s ago", host IP, tactic name) sits under the primary value in muted 10px text instead of taking a column.
- Monospace font for anything an analyst copies: IDs, IPs, timestamps, hashes.
- The page is a CSS grid; on an ultrawide or multi-monitor setup the 12 columns simply get wider, and below 640px everything stacks.


2.4 Safe by construction

- Every dynamic string written into HTML passes through `esc()` (escapes & < > " '). The test suite types an `<img onerror>` payload into the search box and asserts nothing is injected.
- External links use `rel="noopener noreferrer"`.
- Source IPs come from RFC 5737 documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and ASNs from the RFC 5398 documentation range (AS64496-AS64511), so no real address or network is ever shown as malicious.
- localStorage access is wrapped in try/catch (`store.get/set`) because it throws in private windows and sandboxed iframes.
- Modal has role="dialog", aria-modal, a Tab focus trap, Escape to close, and returns focus to the button that opened it. `prefers-reduced-motion` disables animations.

Modal open/close with focus restore

```js
function openModal(id) {
  const a = state.alerts.find(x => x.id === id); if (!a) return;
  state.openId = id; renderModal(a);
  $('#overlay').classList.add('open'); state.opener = document.activeElement; $('#mClose').focus();
}
function closeModal() { $('#overlay').classList.remove('open'); state.openId = null; if (state.opener && state.opener.focus) state.opener.focus(); }
```


3. Architecture

The script is one IIFE in strict mode, split into eleven commented sections. Data flows one way: **model > simulation > derived metrics > renderers**. Renderers never change the model; only the simulation and analyst actions do.

Data flow

```text
  +------------------+      +--------------------+      +----------------+      +---------------+
  | 2. Environment   |      | 4. State + alert   |      | 7. metrics()   |      | 8. renderers  |
  |  HOSTS, IPS,     | ---> |    factory         | ---> |  window, open, | ---> |  KPIs, funnel |
  |  ANALYSTS        |      |  createAlert()     |      |  MTTA, MTTR,   |      |  queue, hosts |
  +------------------+      +---------^----------+      |  funnel counts |      |  IPs, health  |
  +------------------+                |                 +----------------+      +-------+-------+
  | 3. CATALOG       | ---------------+                                                 |
  |  20 detections   |      +---------+----------+      +----------------+              v
  +------------------+      | 6. Simulation      |      | 9. Modal       | <---- click Investigate
  +------------------+      |  tick() every 3 s  |      |  buildRaw()    |
  | 5. SOURCES       | <--- |  addLiveAlert()    |      |  applyAction() |
  |  health model    |      |  every 3.5-8 s     |      +----------------+
  +------------------+      +--------------------+
```

|  | Section | Responsibility |
|---|---|---|
| 1 | Utilities | `$`, `esc`, random helpers (`rint`, `pick`, weighted `wpick`, exponential `expo`), formatters (`fmtCompact`, `fmtDur`), safe `store` |
| 2 | Environment model | 10 monitored hosts with per-minute logon rates, 5 extra assets, 10 threat IPs, 6 analysts, 6 hunters |
| 3 | Detection catalog | 20 detections: title, MITRE technique, tactic, severity pool, weight, Wazuh rule, raw-log builder and response playbook |
| 4 | State + alert factory | `state` object, `createAlert()`, `seedAlerts()` (210 historical alerts), `advanceTo()` |
| 5 | Log-source health | 10 sources with status, lag, EPS, uptime and a 24-point history |
| 6 | Simulation engine | `tick()` (3 s), `addLiveAlert()`, `stepStatuses()`, `tickHosts()`, `tickHealth()`, `tickHunters()` |
| 7 | Derived metrics | `metrics()` computes everything the UI shows from the alert list |
| 8 | Renderers | `renderKpis/Funnel/Queue/Hosts/Ips/Health/Threat`, `renderAll()` |
| 9 | Investigate modal | `buildRaw()`, `highlight()`, `renderModal()`, `applyAction()` |
| 10 | Toasts | Critical-alert pop-ups and action confirmations (max 3 stacked) |
| 11 | Events + boot | Listeners (event delegation), seeding, timers, test hook `window.__soc` |

Single source of truth. Every number on screen is derived from `state.alerts` plus a handful of simulation parameters (`state.eps`, `state.f1`, `state.f2`). That is why acknowledging an alert in the modal immediately changes Open Incidents, MTTA and the queue: they are all recomputed from the same list on the next `renderAll()`.


4. Step-by-step build


Step 1. Fix the visual language first

Before any HTML, the colour tokens and component classes were written (`.panel`, `.chip`, `.btn`, `.sev-*`, `.status`, `.kpi`, `.tile`). Building components before layout means every later section reuses the same badge, button and table styles, so the dashboard looks like one product. The severity badge is a good example: one class per level sets text colour, tinted background and border, and Critical adds a `box-shadow` glow.

Severity badge styles

```css
.sev { display: inline-block; min-width: 58px; text-align: center; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 800; letter-spacing: .06em; border: 1px solid; text-transform: uppercase; }
  .sev-Critical { color: #ff5c85; background: rgba(255,46,99,.14); border-color: rgba(255,46,99,.65); box-shadow: 0 0 10px rgba(255,46,99,.35); }
  .sev-High     { color: #ffa24d; background: rgba(255,138,31,.13); border-color: rgba(255,138,31,.6); }
  .sev-Medium   { color: #fde047; background: rgba(250,204,21,.11); border-color: rgba(250,204,21,.5); }
  .sev-Low      { color: #7dd3fc; background: rgba(56,189,248,.11); border-color: rgba(56,189,248,.5); }
```


Step 2. Lay out the page skeleton

The body is a header plus a 12-column grid (`grid grid-cols-12 gap-2`). Sections declare their span: KPIs and funnel take all 12, the queue takes 8 and the health panel 4 on wide screens (`xl:col-span-8/4`), the two intel panels take 6 each (`lg:col-span-6`). Empty containers carry the IDs the renderers fill (`#queueBody`, `#healthGrid`, `#funnelStages`).

Live queue markup

```html
<!-- ======================= LIVE QUEUE ======================= -->
  <section class="panel col-span-12 xl:col-span-8" id="queue" aria-label="Live alert queue">
    <div class="panel-h flex-wrap">
      <h2 class="panel-t m-0">Real-Time Live Alert Queue</h2>
      <span class="chip" id="queueCount">-</span>
      <div class="ml-auto flex flex-wrap items-center gap-1.5">
        <div class="flex gap-1" role="group" aria-label="Severity filter" id="sevFilters"></div>
        <input id="searchBox" type="search" class="field w-40" placeholder="Filter: id, host, IP, technique" aria-label="Filter alerts">
      </div>
    </div>
    <div class="scroll-q">
      <table aria-live="off">
        <thead>
          <tr>
            <th>Timestamp (UTC)</th><th>Incident ID</th><th>Severity</th><th>Detection</th><th>Source IP / Host</th>
            <th>MITRE ATT&amp;CK</th><th>Assignee</th><th>Status</th><th class="text-right">Action</th>
          </tr>
        </thead>
        <tbody id="queueBody"></tbody>
      </table>
    </div>
  </section>
```


Step 3. Model the environment

Realistic data makes the dashboard credible. Hosts are not random strings: a domain controller, a RADIUS server, an RDP jump host, Exchange, SQL, a file server and three workstations, each with a role, tier and baseline failed/successful logons per minute (`fpm`, `spm`). The RDP jump host and NPS get the highest failed-logon rates because that is where password guessing lands in real networks.

Monitored hosts (baseline rates per minute)

```js
const HOSTS = [   // monitored assets shown in the "Top Target Hosts" panel (fpm / spm = failed / successful logons per minute)
  { name: 'DC01',        ip: '10.20.1.10', os: 'Windows Server 2022', role: 'Domain Controller',   tier: 'Tier 0', fpm: 5.8, spm: 38, acct: 'Administrator' },
  { name: 'DC02',        ip: '10.20.1.11', os: 'Windows Server 2022', role: 'Domain Controller',   tier: 'Tier 0', fpm: 3.1, spm: 31, acct: 'svc_backup' },
  { name: 'NPS01',       ip: '10.20.0.5',  os: 'Windows Server 2019', role: 'RADIUS / VPN auth',   tier: 'Tier 0', fpm: 9.4, spm: 14, acct: 'j.mehta' },
  { name: 'SRV-RDP01',   ip: '10.20.4.21', os: 'Windows Server 2022', role: 'RDP Jump Host',       tier: 'Tier 1', fpm: 12.2, spm: 9, acct: 'admin' },
  { name: 'EXCH01',      ip: '10.20.2.8',  os: 'Windows Server 2019', role: 'Exchange (OWA)',      tier: 'Tier 1', fpm: 5.1, spm: 44, acct: 'r.kapoor' },
  { name: 'SRV-SQL02',   ip: '10.20.5.12', os: 'Windows Server 2022', role: 'Database',            tier: 'Tier 1', fpm: 2.2, spm: 19, acct: 'svc_sql' },
  { name: 'SRV-FILE01',  ip: '10.20.5.30', os: 'Windows Server 2019', role: 'File Server',         tier: 'Tier 1', fpm: 1.9, spm: 52, acct: 'a.nair' },
  { name: 'WS-FIN-014',  ip: '10.30.8.14', os: 'Windows 11 Pro',      role: 'Finance workstation', tier: 'Tier 2', fpm: 0.8, spm: 6,  acct: 'p.deshmukh' },
  { name: 'WS-HR-007',   ip: '10.30.9.7',  os: 'Windows 11 Pro',      role: 'HR workstation',      tier: 'Tier 2', fpm: 0.6, spm: 5,  acct: 'helpdesk' },
  { name: 'WS-DEV-033',  ip: '10.30.6.33', os: 'Windows 11 Pro',      role: 'Developer workstation', tier: 'Tier 2', fpm: 1.1, spm: 7, acct: 'guest' },
];
```


Step 4. Build the detection catalog

Each of the 20 detections is one object that carries everything the UI needs, so adding a detection means adding one entry and nothing else. Fields: `title`, MITRE `tech`/`tn`/`tactic`, a `sev` pool (repeating a value weights it, e.g. Brute Force is High, High, Critical), a selection weight `w`, the Wazuh rule id/level/groups, a `data(c)` function that builds the raw log body, and a four-step `play` playbook.

| Key | Detection | MITRE | Tactic | Severity pool | Weight |
|---|---|---|---|---|---|
| `brute` | Brute Force Attack Detected | `T1110.001` | Credential Access | High, Critical | 14 |
| `spray` | Password Spraying Detected | `T1110.003` | Credential Access | High, Medium | 8 |
| `phish` | Phishing Link Clicked | `T1566.002` | Initial Access | Medium, High | 12 |
| `mimi` | Mimikatz Process Execution | `T1003.001` | Credential Access | Critical | 6 |
| `ps` | Suspicious PowerShell Encoded Command | `T1059.001` | Execution | High, Medium | 11 |
| `ransom` | Ransomware Behaviour: Mass File Rename | `T1486` | Impact | Critical | 3 |
| `c2` | C2 Beaconing Detected (Cobalt Strike profile) | `T1071.001` | Command and Control | Critical, High | 5 |
| `psexec` | Lateral Movement via PsExec Service Install | `T1021.002` | Lateral Movement | High | 6 |
| `newadmin` | New Local Administrator Account Created | `T1136.001` | Persistence | Medium, High | 6 |
| `scan` | Port Scan Detected | `T1046` | Discovery | Low, Medium | 14 |
| `tor` | Outbound Traffic to Tor Exit Node | `T1090.003` | Command and Control | Medium | 6 |
| `schtask` | Scheduled Task Persistence Created | `T1053.005` | Persistence | Medium, High | 7 |
| `travel` | Impossible Travel Sign-in | `T1078` | Initial Access | Medium, High | 7 |
| `exfil` | Large Data Exfiltration to Cloud Storage | `T1567.002` | Exfiltration | High, Critical | 4 |
| `usb` | USB Mass Storage Device Connected | `T1091` | Initial Access | Low, Medium | 8 |
| `logclear` | Security Event Log Cleared | `T1070.001` | Defense Evasion | Critical, High | 3 |
| `kerb` | Kerberoasting: Anomalous TGS-REQ (RC4) | `T1558.003` | Credential Access | High, Medium | 6 |
| `dns` | DNS Tunnelling Suspected | `T1071.004` | Command and Control | Medium, High | 5 |
| `edr` | EDR: Malware Detected & Quarantined | `T1204.002` | Execution | Low, Medium | 12 |
| `srcoff` | Log Source Silent / Offline | `T1562.006` | Defense Evasion | Medium | 0 |

One catalog entry: Mimikatz (Sysmon EID 1 plus related EID 10 access to lsass.exe)

```js
{ k: 'mimi', title: 'Mimikatz Process Execution', tech: 'T1003.001', tn: 'LSASS Memory', tactic: 'Credential Access', sev: ['Critical'], w: 6, origin: 'int',
    rule: { id: '100410', lvl: 15, groups: ['sysmon', 'credential_dumping', 'sysmon_event1'] }, loc: 'EventChannel', dec: 'windows_eventchannel', hostPool: 'any',
    pre: 'Encoded PowerShell spawned from Office child process', post: 'Check for lateral movement (4624 type 3 / PsExec) using dumped credentials within 15 minutes',
    play: ['Isolate the host via EDR immediately', 'Collect memory image and the dropped binary; hash and detonate', 'Treat every account that logged onto the host as compromised: reset + revoke Kerberos tickets', 'Hunt the same command line / hash across the fleet'],
    data: c => ({ win: { system: winSys(1, c.host, { providerName: 'Microsoft-Windows-Sysmon' }, 'Microsoft-Windows-Sysmon/Operational', 'Microsoft-Windows-Sysmon'),
      eventdata: { utcTime: new Date(c.ts).toISOString().replace('T', ' ').replace('Z', ''), processGuid: `{${guid()}}`, processId: String(rint(2000, 9000)), image: 'C:\\Users\\Public\\Downloads\\mimikatz.exe', originalFileName: 'mimikatz.exe',
        commandLine: 'mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" "exit"', currentDirectory: 'C:\\Users\\Public\\Downloads\\', user: `CORP\\${c.user}`, integrityLevel: 'High',
        hashes: `SHA256=${sha().toUpperCase()}`, parentImage: 'C:\\Windows\\System32\\cmd.exe', parentCommandLine: 'cmd.exe /c C:\\Users\\Public\\Downloads\\run.bat' } },
      related: { sysmon_event_10: { sourceImage: 'mimikatz.exe', targetImage: 'C:\\Windows\\System32\\lsass.exe', grantedAccess: '0x1010' } } }) }
```

`Log Source Silent / Offline` has weight 0: it is never drawn randomly, only raised by the health model when a source actually goes offline. This keeps the queue consistent with the health panel.


Step 5. Turn the catalog into alerts

`createAlert()` picks a detection by weight, a host from the right pool (domain controllers for Kerberoasting, workstations for phishing), and decides what the "Source IP / Host" column shows: the attacker IP for external attacks, the affected host for internal ones. Critical and High alerts have a chance of being born already escalated.

Alert factory

```js
function createAlert(ts, forceKey, srcName) {
  const t = forceKey ? CAT[forceKey] : wpick(CATALOG, c => c.w);
  const host = pickHost(t.hostPool);
  const src = t.origin === 'int' ? pick(WORKSTATIONS.filter(w => w !== host)) : { name: 'external', ip: pick(IPS).ip };
  const ext = pick(IPS).ip;   // external / threat-intel IP associated with this alert
  const a = {
    id: `INC-${state.seq++}`, ts, type: t.k, title: t.title, sev: pick(t.sev), host, src, ext, user: pick(USERS), srcName,
    status: 'New', assignee: null, escalated: false, ackMin: null, resMin: null, raw: null, confidence: rint(62, 98),
  };
  // "Source IP / Host" column: external detections show the attacker IP; internal ones show the affected host.
  a.srcLabel = (t.origin === 'ext' || t.origin === 'cloud') ? a.ext : host.name;
  a.srcSub = t.origin === 'ext' ? `→ ${host.name}`
           : t.origin === 'cloud' ? `${a.user}@corp.example`
           : (t.k === 'psexec' || t.k === 'kerb') ? `from ${src.name} → ${host.name}`
           : host.ip;
  if (t.k === 'srcoff') { a.srcLabel = srcName || host.name; a.srcSub = 'log pipeline'; }
  a.escalated = a.sev === 'Critical' ? rnd() < 0.6 : a.sev === 'High' ? rnd() < 0.2 : false;
  if (a.escalated) a.status = 'Escalated';
  return a;
}
```

`seedAlerts()` creates 210 historical alerts over 24 h, biased toward recent times (`Math.pow(rnd(), 2.2)`), and ages them: old alerts are mostly Resolved, recent ones mostly New. Incident IDs are renumbered chronologically so they increase with time like a real ticket system.

Seeding history

```js
function seedAlerts() {
  const now = Date.now();
  for (let i = 0; i < 210; i++) {
    const ts = now - Math.pow(rnd(), 2.2) * 24 * 3600e3 - 4000;
    const a = createAlert(ts);
    const ageMin = (now - ts) / 60000, pFinal = Math.min(0.95, ageMin / 110);
    if (rnd() < pFinal) { advanceTo(a, rnd() < 0.18 ? 'False Positive' : 'Resolved'); }
    else if (rnd() < Math.min(0.9, ageMin / 20)) { advanceTo(a, rnd() < 0.55 ? 'Investigating' : 'Acknowledged'); }
    state.alerts.push(a);
  }
  state.seq = 48210 + 210;
  // renumber chronologically so IDs increase with time
  state.alerts.sort((x, y) => x.ts - y.ts).forEach((a, i) => { a.id = `INC-${48000 + i}`; });
  state.seq = 48000 + state.alerts.length;
}
```


Step 6. Model log-source health

Ten sources start Healthy except two seeded problems: Azure AD / M365 is Lagging (142 s) and Linux auditd (DMZ) is Offline with 11 minutes of silence, so the panel is never boring on first load. Each tick a Healthy source has a 1.2% chance of starting to lag; a Lagging one recovers (20%) or goes Offline (3%), and going Offline raises a "Log Source Silent" alert, which links the health panel to the queue.

Health state machine

```js
function tickHealth() {
  SOURCES.forEach(s => {
    const base = s.eps;
    if (s.status === 'Healthy') {
      if (rnd() < 0.012) { s.status = 'Lagging'; s.lag = rint(45, 240); }
      else s.lag = +clamp(s.lag + (rnd() - 0.5) * 0.6, 0.3, 4.5).toFixed(1);
    } else if (s.status === 'Lagging') {
      s.lag = clamp(s.lag + rint(-20, 14), 20, 400);
      if (rnd() < 0.2) { s.status = 'Healthy'; s.lag = 1.2; }
      else if (rnd() < 0.03) { s.status = 'Offline'; s.lastSeen = 0; addLiveAlert('srcoff', s.name); }
    } else {
      s.lastSeen += 3;
      if (rnd() < 0.08) { s.status = 'Lagging'; s.lag = 180; }
    }
    const f = s.status === 'Offline' ? 0 : s.status === 'Lagging' ? 0.55 : 1;
    s.hist.push((0.8 + rnd() * 0.4) * f); s.hist.shift();
    s.cur = Math.round(base * f * (0.9 + rnd() * 0.2));
    if (s.agents && s.status === 'Healthy') s.agents[0] = clamp(s.agents[0] + rint(-2, 2), s.agents[1] - 18, s.agents[1]);
    s.uptime = +clamp(s.uptime + (s.status === 'Healthy' ? 0.0005 : -0.004), 97.5, 99.99).toFixed(3);
  });
}
```


Step 7. Write the simulation engine

Two clocks run: a 3-second `tick()` that evolves the world, and a randomised 3.5-8 s timer that adds a new alert. Keeping them separate makes arrivals bursty rather than metronomic. `tick()` random-walks events-per-second with a slow sine wave, nudges the funnel ratios, advances alert statuses (biased to older open items), makes hosts surge into brute-force bursts, toggles hunters and purges alerts older than 24 h.

Simulation tick and status progression

```js
function tick() {
  state.tick++;
  state.eps = clamp(state.eps + (rnd() - 0.5) * 90 + Math.sin(state.tick / 18) * 14, 760, 1900);
  state.f1 = clamp(state.f1 + (rnd() - 0.5) * 0.002, 0.036, 0.052);
  state.f2 = clamp(state.f2 + (rnd() - 0.5) * 0.4, 6.5, 9.5);
  stepStatuses(); tickHosts(); tickHealth(); tickHunters();
  // purge >24h
  const cutoff = Date.now() - 24 * 3600e3; state.alerts = state.alerts.filter(a => a.ts >= cutoff);
}

function stepStatuses() {
  const open = state.alerts.filter(a => !isFinal(a));
  if (!open.length) return;
  const n = rint(1, 3);
  for (let i = 0; i < n; i++) {
    // bias toward older open items
    const a = open.sort((x, y) => x.ts - y.ts)[Math.floor(Math.pow(rnd(), 1.6) * open.length)];
    if (!a || isFinal(a)) continue;
    if (a.status === 'New') advanceTo(a, 'Acknowledged');
    else if (a.status === 'Acknowledged') advanceTo(a, rnd() < 0.8 ? 'Investigating' : 'Acknowledged');
    else if (a.status === 'Escalated') { if (rnd() < 0.2) advanceTo(a, rnd() < 0.1 ? 'False Positive' : 'Resolved'); }
    else if (a.status === 'Investigating') {
      const r = rnd();
      if (r < 0.1 && a.sev !== 'Low') { a.escalated = true; a.status = 'Escalated'; }
      else if (r < 0.5) advanceTo(a, rnd() < 0.2 ? 'False Positive' : 'Resolved');
    }
  }
}
```

Status transitions record MTTA and MTTR samples

```js
function advanceTo(a, status) {
  const crit = a.sev === 'Critical';
  if (a.ackMin == null) { a.ackMin = clamp(0.6 + expo(crit ? 2.4 : 4.8), 0.3, 38); a.assignee = pick(crit ? ANALYSTS.filter(x => x.t === 'T2') : ANALYSTS).n; }
  if (status === 'Resolved' || status === 'False Positive') { if (a.resMin == null) a.resMin = a.ackMin + 10 + expo(crit ? 120 : 62); }
  a.status = status;
}
```

Acknowledge and resolve times are drawn from an exponential distribution (`expo`), the usual model for waiting times: most alerts are handled quickly, a few take very long. Critical alerts are assigned to Tier-2 analysts and acknowledged faster.


Step 8. Derive the metrics

`metrics()` filters alerts to the selected time window and computes open count, mean time to acknowledge, mean time to resolve (needs at least 3 samples, otherwise falls back to all data), and the four funnel numbers. Raw logs are `EPS x seconds in window`; filtered events are raw times `f1` (about 4.3%); triaged alerts are the window alert count times `f2` (about 7.6 rule hits per incident); escalated incidents are counted for real.

Derived metrics

```js
function metrics() {
  const now = Date.now();
  const win = state.alerts.filter(a => inRange(a, now));
  const open = win.filter(a => !isFinal(a));
  const mean = (arr, f) => arr.length >= 3 ? arr.reduce((s, a) => s + f(a), 0) / arr.length : NaN;
  const all = state.alerts;
  let mtta = mean(win.filter(a => a.ackMin != null), a => a.ackMin); if (isNaN(mtta)) mtta = mean(all.filter(a => a.ackMin != null), a => a.ackMin);
  let mttr = mean(win.filter(a => a.resMin != null), a => a.resMin); if (isNaN(mttr)) mttr = mean(all.filter(a => a.resMin != null), a => a.resMin);
  const raw = state.eps * state.range * 60;
  const filtered = raw * state.f1;
  const escalated = win.filter(a => a.escalated || a.status === 'Escalated').length;
  const triaged = Math.max(win.length * state.f2, escalated + 1);
  return { win, open, mtta, mttr, raw, filtered, triaged, escalated, hunters: HUNTERS.filter(h => h.on),
    crit: open.filter(a => a.sev === 'Critical').length, high: open.filter(a => a.sev === 'High').length };
}
```


Step 9. Render the panels

KPIs. Each card shows value, a context line (SLA status against a 5-minute MTTA and 4-hour MTTR target) and an SVG sparkline built from the last 40 samples. Threat level is derived from the number of open Critical incidents (0-1 Guarded, 2-4 Elevated, 5+ Severe).

Sparkline generator (inline SVG, no chart library)

```js
function spark(el, data, color) {
  const v = data.slice(-40); if (v.length < 2) return;
  const mn = Math.min(...v), mx = Math.max(...v), r = mx - mn || 1;
  const pts = v.map((y, i) => `${(i / (v.length - 1) * 100).toFixed(1)},${(30 - ((y - mn) / r) * 26).toFixed(1)}`).join(' ');
  el.innerHTML = `<defs><linearGradient id="g${el.id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
    <polygon points="0,34 ${pts} 100,34" fill="url(#g${el.id})"/><polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.6" vector-effect="non-scaling-stroke" stroke-linejoin="round"/>`;
}
```

Funnel. Raw logs are millions and escalated incidents are tens, a ratio of about 1:2,500,000, so a linear shape would show one fat bar and three slivers. The funnel therefore scales each stage by `log10`, mapping the largest to 100% height and the smallest to 20%, and draws four trapezoids that join edge to edge. The text under each stage shows the real number and the percentage dropped.

Log-scaled alert funnel

```js
function renderFunnel(m) {
  const vals = [m.raw, m.filtered, m.triaged, Math.max(1, m.escalated)];
  const labels = [['Raw Logs', 'all sources ingested'], ['Filtered Events', 'after normalisation & dedup'], ['Triaged Alerts', 'rules + TI matches'], ['Escalated Incidents', 'to Tier-2 / IR']];
  const colors = ['#22d3ee', '#3b82f6', '#f59e0b', '#ff2e63'];
  const lg = vals.map(Math.log10), top = lg[0], bot = lg[3];
  const H = lg.map(l => 20 + 80 * ((l - bot) / (top - bot || 1)));
  const half = h => h / 2;
  let polys = '';
  for (let i = 0; i < 4; i++) {
    const h1 = H[i], h2 = i < 3 ? H[i + 1] : H[3] * 0.82;
    const x0 = i * 250, x1 = x0 + 250;
    polys += `<polygon points="${x0},${50 - half(h1)} ${x1},${50 - half(h2)} ${x1},${50 + half(h2)} ${x0},${50 + half(h1)}" fill="${colors[i]}" fill-opacity="${0.12 + i * 0.04}" stroke="${colors[i]}" stroke-opacity=".55" stroke-width="1" vector-effect="non-scaling-stroke"/>`;
  }
  $('#funnelSvg').innerHTML = polys;
  $('#funnelStages').innerHTML = vals.map((v, i) => {
    const pct = i === 0 ? '' : `<span class="chip" style="color:${colors[i]};border-color:${colors[i]}55">&#9660; ${(100 - (v / vals[i - 1]) * 100).toFixed(i === 1 ? 1 : 2)}% dropped</span>`;
    return `<div class="px-3 flex flex-col justify-center min-w-0"><div class="muted text-[10px] font-bold tracking-wider uppercase truncate">${i + 1}. ${labels[i][0]}</div>
      <div class="mono text-[22px] font-bold leading-tight" style="color:${colors[i]}">${i === 3 ? fmtInt(v) : fmtCompact(v)}</div>
      <div class="flex items-center gap-2 text-[10.5px] muted min-w-0"><span class="truncate">${labels[i][1]}</span>${pct}</div></div>`;
  }).join('');
  $('#funnelRange').textContent = RANGE_LABEL[state.range];
  $('#funnelReduction').innerHTML = `Noise reduction <b class="c-ok mono">${(100 - (vals[3] / vals[0]) * 100).toFixed(4)}%</b> &middot; 1 incident per <b class="mono">${fmtCompact(vals[0] / vals[3])}</b> raw events`;
}
```

Queue. The newest 40 alerts matching the severity buttons and search text are rendered as one HTML string. A single click listener on `<tbody>` handles every Investigate button (event delegation), so re-rendering every few seconds does not leak listeners. The scroll position is saved and restored across re-renders so the analyst is not thrown back to the top mid-read.

Live alert queue

```js
function renderQueue(m) {
  const now = Date.now(), list = filteredQueue(m), shown = list.slice(0, 40);
  $('#queueCount').textContent = `Showing ${shown.length} of ${list.length} · ${RANGE_LABEL[state.range]}`;
  const body = $('#queueBody');
  if (!shown.length) { body.innerHTML = `<tr><td colspan="9" class="text-center muted py-6">No incidents match the current filters.</td></tr>`; return; }
  body.innerHTML = shown.map(a => {
    const t = CAT[a.type], stCls = 'st-' + a.status.replace(' ', '');
    return `<tr class="row r-${a.sev} ${isFinal(a) ? 'final' : ''} ${state.flash.has(a.id) ? 'flash' : ''}" data-id="${esc(a.id)}">
      <td class="mono whitespace-nowrap"><time datetime="${new Date(a.ts).toISOString()}" title="${new Date(a.ts).toISOString()}">${hhmmss(a.ts)}</time><div class="muted text-[10px]">${ago(now - a.ts)}</div></td>
      <td class="mono font-semibold whitespace-nowrap">${esc(a.id)}</td>
      <td><span class="sev sev-${a.sev}">${a.sev}</span></td>
      <td class="font-medium" style="min-width:190px">${esc(a.title)}</td>
      <td class="mono whitespace-nowrap">${esc(a.srcLabel)}<div class="muted text-[10px]">${esc(a.srcSub)}</div></td>
      <td style="min-width:170px"><a class="chip mono" style="color:#67e8f9" target="_blank" rel="noopener noreferrer" href="https://attack.mitre.org/techniques/${t.tech.replace('.', '/')}/" title="Open ${esc(t.tech)} on attack.mitre.org">${esc(t.tech)}</a>
          <div class="muted text-[10px]">${esc(t.tn)} · ${esc(t.tactic)}</div></td>
      <td class="whitespace-nowrap">${a.assignee ? esc(a.assignee) : '<span class="muted">Unassigned</span>'}</td>
      <td><span class="status ${stCls}">${esc(a.status)}</span></td>
      <td class="text-right"><button class="btn btn-primary" data-inv="${esc(a.id)}" aria-label="Investigate ${esc(a.id)}">&#128269; Investigate</button></td></tr>`;
  }).join('');
  state.flash.clear();
}
```

Hosts and IPs. Failed logons are `fpm x minutes x surge multiplier x noise`, so changing the time range scales every number consistently. A host in a surge shows "Active burst"; one flagged compromised shows "4624 after 4625 burst", the classic signature of a successful brute force. The Block button on an IP simulates a firewall push (hits drop 96%).

Top target hosts (4625 / 4624)

```js
function renderHosts() {
  const R = state.range;
  const rows = HOSTS.map(h => {
    const f = Math.round(h.fpm * R * h.mult * h.noise), s = Math.round(h.spm * R * h.noise2);
    return { h, f, s, ratio: f / (f + s) };
  }).sort((a, b) => b.f - a.f);
  $('#hostsRange').textContent = RANGE_LABEL[R];
  $('#hostsBody').innerHTML = rows.map(({ h, f, s, ratio }) => {
    const sev = ratio > 0.55 ? 'crit' : ratio > 0.3 ? 'high' : ratio > 0.12 ? 'med' : 'low';
    const signal = h.surge > 0 && h.compromised ? `<span class="sev sev-Critical" style="min-width:0" title="A successful 4624 followed a 4625 burst from the same source: possible compromise">4624 after 4625 burst</span>`
      : h.surge > 0 ? `<span class="sev sev-High" style="min-width:0">Active burst</span>` : '<span class="muted">Baseline</span>';
    return `<tr><td class="mono font-semibold whitespace-nowrap">${h.name}<div class="muted text-[10px]">${h.ip}</div></td><td class="whitespace-nowrap">${h.role}<div class="muted text-[10px]">${h.tier}</div></td>
      <td class="mono text-right c-${sev} font-semibold">${fmtInt(f)}</td><td class="mono text-right">${fmtInt(s)}</td>
  /* ... remaining lines omitted in this report ... */
}
```


Step 10. Build the Investigate drill-down

`buildRaw()` assembles a Wazuh-style alert: timestamp, `rule` with MITRE mapping, `agent`, `decoder`, the detection-specific `data` from the catalog, and a `soc` block with asset context and threat-intel enrichment. The JSON is cached on the alert, so reopening shows identical data. `highlight()` colours keys, strings, numbers and booleans with one regular expression and escapes every token.

Raw log builder

```js
function buildRaw(a) {
  if (a.raw) return a.raw;
  const t = CAT[a.type], h = a.host;
  const c = { ts: a.ts, host: h, src: a.src, ext: a.ext, user: a.user, srcName: a.srcName };
  const geo = IPS.find(i => i.ip === a.ext);
  a.raw = {
    timestamp: wzTime(a.ts),
    rule: { level: t.rule.lvl, description: t.title, id: t.rule.id, mitre: { id: [t.tech], tactic: [t.tactic], technique: [t.tn] }, firedtimes: rint(1, 60), mail: t.rule.lvl >= 12, groups: t.rule.groups },
    agent: { id: pad(ALL_HOSTS.indexOf(h) + 1, 3), name: h.name, ip: h.ip },
    manager: { name: 'wazuh-mgr-01' },
    id: `${Math.floor(a.ts / 1000)}.${rint(100000, 999999)}`,
    decoder: { name: t.dec },
    data: t.data(c),
    location: t.loc,
    soc: { incident_id: a.id, severity: a.sev, confidence: a.confidence / 100, asset: { hostname: h.name, os: h.os, role: h.role, tier: h.tier || 'Tier 2' },
      ti: geo ? { ioc: geo.ip, matched: true, reputation: geo.rep, tags: geo.tags, geoip: { country: geo.cc, city: geo.city, asn: geo.asn, org: geo.org } } : { matched: false }, siem_index: `wazuh-alerts-4.x-${new Date(a.ts).toISOString().slice(0, 10).replace(/-/g, '.')}` },
  };
  return a.raw;
}
```

The modal also shows an incident summary, a four-point timeline (precursor, rule fired, enrichment, what to hunt next) and the recommended playbook. Five analyst actions (Acknowledge, Assign to me, Escalate to T2, False positive, Resolve) update the same alert object, so the KPIs react immediately.

Analyst actions

```js
function applyAction(act) {
  const a = state.alerts.find(x => x.id === state.openId); if (!a) return;
  if (act === 'ack') { a.ackMin = a.ackMin ?? clamp((Date.now() - a.ts) / 60000, 0.2, 60); a.assignee = a.assignee || ME; a.status = 'Acknowledged'; }
  if (act === 'assign') { a.assignee = ME; if (a.status === 'New') { a.ackMin = a.ackMin ?? (Date.now() - a.ts) / 60000; a.status = 'Acknowledged'; } }
  if (act === 'escalate') { a.escalated = true; a.status = 'Escalated'; a.ackMin = a.ackMin ?? (Date.now() - a.ts) / 60000; a.assignee = a.assignee || ME; }
  if (act === 'fp' || act === 'resolve') { a.ackMin = a.ackMin ?? (Date.now() - a.ts) / 60000; a.resMin = Math.max(a.ackMin, (Date.now() - a.ts) / 60000); a.assignee = a.assignee || ME; a.status = act === 'fp' ? 'False Positive' : 'Resolved'; }
  renderModal(a); renderAll(true);
  toast(`${a.id} → <b>${esc(a.status)}</b>`, null, true);
}
```


Step 11. Wire events and boot

Listeners use delegation (`#queueBody`, `#ipsBody`, `#mBody`, `#sevFilters`). Boot order matters: seed alerts, run one health tick, render everything, then start the clock, the 3-second tick and the alert scheduler. The last line exposes `window.__soc` for tests and debugging.

Boot sequence

```js
seedAlerts();
tickHealth();
renderAll();
setInterval(() => { $('#clock').textContent = new Date().toISOString().slice(11, 19); }, 1000);
$('#clock').textContent = new Date().toISOString().slice(11, 19);
setInterval(() => { if (state.paused) return; tick(); renderAll(); if (state.openId) { const a = state.alerts.find(x => x.id === state.openId); if (a) { const st = $('#mStatus'); st.className = `status ml-2 st-${a.status.replace(' ', '')}`; st.textContent = a.status; } } }, 3000);
scheduleNextAlert();
```


5. Testing and verification

Three layers were used. Static: the script is parsed with `new Function()` to catch syntax errors. Behavioural: `npm test` loads the page in jsdom and runs 42 assertions over hundreds of simulated ticks. Visual: the page was opened in headless Chromium at 1920x1080, 1366x768 and 390x844, checked for console errors and horizontal overflow, and photographed for this report.

| Area | What is asserted |
|---|---|
| Render | 210 seeded alerts with unique IDs; <= 40 queue rows of 9 columns; 5 KPIs, 4 funnel stages, 10 health tiles, 10 host rows, 10 IP rows |
| Funnel | Strictly narrows for every range (for example 107.1M > 4.6M > 1,596 > 27) |
| Time range | Each of 15m / 1h / 24h updates the KPI label and recomputes the funnel |
| Simulation | 300 ticks plus live alerts: alerts accumulate, >24 h alerts are purged, health states stay in the allowed set |
| Filters | Critical filter shows only Critical; search narrows rows; empty state appears; an HTML payload typed in search is not injected |
| Modal | All 20 detections open and their raw JSON parses with the right MITRE ID, host and incident ID |
| Correctness | Windows paths are single-escaped in JSON; Mimikatz is Sysmon EID 1 at Wazuh level 15 |
| Actions | Acknowledge, Escalate and False Positive change state; buttons disable once closed; resolve time >= acknowledge time; Escape closes |
| Controls | Block IP, Pause and Resume, threat-level badge, toast cap |


5.1 Defects found and fixed during verification

| Defect | Cause | Fix |
|---|---|---|
| Raw JSON showed `C:\\\\Users\\\\...` (doubled backslashes) | Paths were escaped once in the JavaScript source and again by `JSON.stringify` | Halved every backslash run inside the catalog; a test now asserts the parsed value equals `C:\Users\Public\Downloads\mimikatz.exe` |
| Resolve time could be earlier than acknowledge time | Acknowledge clamps MTTA to at least 0.2 min, Resolve did not | `resMin = Math.max(ackMin, elapsed)` |
| Page scrolled sideways by 21px on a phone | "% dropped" chips in four narrow funnel columns could not wrap | Chips hidden and numbers shrunk below 640px; funnel container clips overflow |
| Dead and duplicated code in `createAlert` | Leftover conditionals from iteration (`a.t === 'x'`, a ternary with identical branches) | Replaced by one commented rule for the Source column |
| Old tests and report described a different build | Earlier iteration used other element IDs and hooks | Tests rewritten against the current DOM; report regenerated from the code |

> Note. The build sandbox could not reach the Tailwind CDN, so for testing and screenshots the identical pinned build (4.1.11) was installed from npm and served in place of the CDN URL. Google Fonts were also unreachable, so screenshots use the fallback system fonts. On a normal internet connection the page loads Inter and JetBrains Mono.


5.2 Screenshots

![Figure 1. Full dashboard at 1920x1080 (Last 24h).](docs/screenshots/00-dashboard-full.png)
Figure 1. Full dashboard at 1920x1080 (Last 24h).*

![Figure 2. KPI banner: Total Events, Open Incidents, MTTA, MTTR, Active Threat Hunters.](docs/screenshots/01-kpi-banner.png)
Figure 2. KPI banner: Total Events, Open Incidents, MTTA, MTTR, Active Threat Hunters.*

![Figure 3. Alert funnel, log-scaled: Raw Logs > Filtered Events > Triaged Alerts > Escalated Incidents.](docs/screenshots/02-alert-funnel.png)
Figure 3. Alert funnel, log-scaled: Raw Logs > Filtered Events > Triaged Alerts > Escalated Incidents.*

![Figure 4. Real-time live alert queue with severity filters and search.](docs/screenshots/03-live-alert-queue.png)
Figure 4. Real-time live alert queue with severity filters and search.*

![Figure 5. Log ingestion health: Healthy, Lagging (Azure AD / M365) and Offline (Linux auditd).](docs/screenshots/04-log-health.png)
Figure 5. Log ingestion health: Healthy, Lagging (Azure AD / M365) and Offline (Linux auditd).*

![Figure 6. Top target hosts with Windows 4625 / 4624 counts.](docs/screenshots/05-top-hosts.png)
Figure 6. Top target hosts with Windows 4625 / 4624 counts.*

![Figure 7. Top malicious source IPs with geo, ASN, tags, reputation and Block action.](docs/screenshots/06-malicious-ips.png)
Figure 7. Top malicious source IPs with geo, ASN, tags, reputation and Block action.*

![Figure 8. Investigate drill-down for a Critical Mimikatz alert, with raw JSON log.](docs/screenshots/07-investigate-modal.png)
Figure 8. Investigate drill-down for a Critical Mimikatz alert, with raw JSON log.*

![Figure 9. Global time range set to Last 15m: KPIs, funnel and queue rescale.](docs/screenshots/08-range-15m.png)
Figure 9. Global time range set to Last 15m: KPIs, funnel and queue rescale.*

![Figure 10. Phone width (390px): panels stack, no horizontal scroll.](docs/screenshots/09-mobile.png)
Figure 10. Phone width (390px): panels stack, no horizontal scroll.*


6. Packaging and GitHub

1. The folder is named `SOC Dashboard` and holds `index.html`, `README.md`, `LICENSE` (MIT), `.gitignore`, `package.json`, `tests/`, `tools/`, `docs/screenshots/`, `.github/workflows/pages.yml` and both reports.
2. `git init -b main`, `git add -A`, `git commit` creates the local repository (already done in the delivered folder).
3. On github.com create a new empty repository (for example `soc-dashboard`), without a README or licence so the histories do not clash.
4. In the project folder run: `git remote add origin https://github.com/<your-user>/soc-dashboard.git` then `git push -u origin main`.
5. Optional live demo: in the repository go to Settings > Pages > Source: GitHub Actions. The included workflow publishes `index.html` and `docs/` on every push to `main`.
6. To regenerate these reports after changing the code: `pip install reportlab`, then `python3 tools/build_report.py`.


7. Limitations and next steps

- Simulated data. Nothing is read from a real SIEM. The numbers are plausible, not measured.
- Browser state only. Analyst actions (acknowledge, escalate, block) live in memory and are lost on reload; only the time range is remembered.
- Geo context is tabular. There is no map; coordinates were left out on purpose to keep the display dense.
- CDN dependency. Tailwind needs internet on first load unless you host the script locally.

Connecting real data** is a contained change. Replace `createAlert()` / `addLiveAlert()` with a fetch or WebSocket client for your platform (Wazuh API `/alerts`, Elastic or Splunk search, Sentinel), map each alert onto the `state.alerts` shape (`id, ts, title, sev, host, srcLabel, status, raw`), and keep the renderers unchanged. Then replace the health model with real agent and ingestion-lag queries, and send analyst actions back to your case-management API.

Further ideas: persist actions in IndexedDB, add sound for Critical alerts, a shift-handover export, per-analyst workload view, and a MITRE ATT&CK heat map built from `CAT[type].tech`.


Appendix A. Simulation parameters

| Parameter | Value | Meaning |
|---|---|---|
| World tick | 3 s | `setInterval` calling `tick()` then `renderAll()` |
| Alert arrival | 3.5-8 s random | `scheduleNextAlert()` |
| Seeded history | 210 alerts / 24 h | Biased toward recent times |
| Alert cap / retention | 600 alerts / 24 h | Oldest dropped first |
| Events per second | 760-1,900 (starts 1,240) | Random walk plus slow sine |
| Filter ratio f1 | 3.6-5.2% of raw | Raw logs to filtered events |
| Rule hits per incident f2 | 6.5-9.5 | Window alerts to triaged alerts |
| SLA targets | MTTA 5 min, MTTR 4 h | Green tick when met, orange arrow when not |
| Threat level | 0-1 / 2-4 / 5+ open Critical | Guarded / Elevated / Severe |
| Host surge | 3% chance per tick, 10-26 ticks, 3-8x | 30% of surges flagged compromised |
| Source health | 1.2% to Lagging; Lagging 20% recover, 3% Offline; Offline 8% to Lagging | Per 3 s tick |
| Queue rows shown | 40 newest matching | Count of all matches shown in header |


Appendix B. Glossary

| Term | Meaning |
|---|---|
| MTTA / MTTR | Mean time to acknowledge / resolve: average minutes from alert creation to first analyst action / to closure |
| EPS | Events per second ingested by the SIEM |
| Funnel | The reduction from raw logs to the few incidents a human must handle |
| 4625 / 4624 | Windows Security events: failed / successful logon |
| MITRE ATT&CK | Public knowledge base of adversary tactics and techniques (for example T1110 Brute Force) |
| Sysmon | Microsoft Sysinternals driver that logs process, network and registry activity (EID 1 process create, EID 10 process access) |
| Wazuh | Open-source XDR/SIEM whose alert JSON format this dashboard imitates |
| Kerberoasting | Requesting service tickets to crack service-account passwords offline (T1558.003) |
| RFC 5737 / 5398 | Standards reserving IP address blocks and AS numbers for documentation so examples never hit real networks |
| Tier 1 / Tier 2 | First-line triage analysts / deeper investigation and response analysts |


Appendix C. Project files

```text
SOC Dashboard/
|-- index.html                          the dashboard (open this)
|-- README.md                           quick start
|-- LICENSE                             MIT
|-- package.json  .gitignore            npm test script, ignore rules
|-- SOC_Dashboard_Project_Report.txt    this report, plain text
|-- SOC_Dashboard_Project_Report.pdf    this report, PDF with screenshots
|-- REPORT.md                           this report, Markdown (renders on GitHub)
|-- report/                             same report split into one file per chapter
|-- tests/dom-test.js                   42 behavioural assertions (jsdom)
|-- tools/build_report.py               regenerates both reports from index.html
|-- docs/screenshots/                   figures used in the PDF and README
`-- .github/workflows/pages.yml         optional GitHub Pages deployment
```
