#!/usr/bin/env python3
"""
Builds the project report for the SOC Dashboard in two formats from one content model:
  - SOC_Dashboard_Project_Report.txt
  - SOC_Dashboard_Project_Report.pdf

Code excerpts are pulled live from index.html, so the report always matches the code.
Usage:  python3 tools/build_report.py        (from the project folder)
Needs:  reportlab  (pip install reportlab)
"""
import os, re, sys, textwrap, datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
HTML = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
JS = re.search(r'<script>\n\(\(\) =>(.*?)</script>', HTML, re.S).group(1)
CSS = re.search(r'<style>(.*?)</style>', HTML, re.S).group(1)
TODAY = datetime.date(2026, 11, 7).strftime('%d %B %Y')
LINES = HTML.count('\n') + 1
JS_LINES = JS.count('\n')


# ----------------------------------------------------------------- snippet helpers
def _match_brace(text, start):
    depth, i, n = 0, start, len(text)
    while i < n:
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    raise ValueError('unbalanced braces')


def fn(name, max_lines=None):
    m = re.search(r'^function\s+%s\s*\(' % re.escape(name), JS, re.M)
    if not m:
        raise KeyError('function not found: ' + name)
    end = _match_brace(JS, JS.index('{', m.start()))
    code = JS[m.start():end]
    lines = code.split('\n')
    if max_lines and len(lines) > max_lines:
        lines = lines[:max_lines - 1] + ['  /* ... remaining lines omitted in this report ... */', '}']
    return '\n'.join(lines)


def between(text, start_marker, end_marker, include_end=False):
    a = text.index(start_marker)
    b = text.index(end_marker, a)
    return text[a:b + (len(end_marker) if include_end else 0)].rstrip()


def template(key):
    a = JS.index("{ k: '%s'" % key)
    b = JS.index('\n\n', a)
    block = JS[a:b].rstrip().rstrip(',')
    return block


# ----------------------------------------------------------------- content model
B = []  # list of blocks


def H1(t): B.append(('h1', t))
def H2(t): B.append(('h2', t))
def P(t): B.append(('p', t))
def UL(items): B.append(('ul', items))
def OL(items): B.append(('ol', items))
def CODE(t, cap=None): B.append(('code', t, cap))
def NOTE(t): B.append(('note', t))
def TABLE(head, rows, widths): B.append(('table', head, rows, widths))
def IMG(path, cap, w=487): B.append(('img', path, cap, w))
def PB(): B.append(('pb',))


# ----------------------------------------------------------------- derived facts (read from index.html)
DET = re.findall(r"\{ k: '(\w+)', title: '([^']*)', tech: '([^']+)', tn: '([^']*)', tactic: '([^']*)', sev: \[([^\]]*)\], w: (\d+)", JS)
N_DET = len(DET)
def sevs(s): return ', '.join(dict.fromkeys(x.strip().strip("'") for x in s.split(',')))
SEED = re.search(r'for \(let i = 0; i < (\d+); i\+\+\) \{\s*const ts', JS).group(1)

# ===== 1. Purpose
H1('1. Purpose and scope')
P('This report explains, in the order the work was done, how the **SOC Command Center** dashboard was designed, built, tested and packaged. '
  'It is written so that a junior analyst or developer can read it next to the code and follow every decision. Every code excerpt is extracted from the real '
  '`index.html` when the report is generated, so the report and the code cannot drift apart.')
P('The deliverable is one self-contained file, `index.html` (%d lines, about %d of them JavaScript). It uses Tailwind CSS from a CDN and plain JavaScript with no framework and no build step: '
  'save the file, double-click it, and it runs. All data is generated in the browser by a simulation engine that stands in for a SIEM, so nothing is collected, stored or transmitted.' % (LINES, JS_LINES))
H2('1.1 Who the dashboard is for')
P('A Tier-1 analyst needs to answer three questions in seconds: *what is on fire, what should I take next, and can I trust my data?* A Tier-2 analyst needs the evidence behind an escalation. '
  'The layout follows that order: KPIs and funnel (health of the operation), the live queue (what to work), the intel and log panels (context), the ingestion monitor (trust), and a drill-down with raw JSON (evidence).'.replace('*', ''))
H2('1.2 Requirements traceability')
TABLE(['Requirement', 'How it is met', 'Where'], [
  ['Cyber-security dark mode (#0d1117 / #0f172a)', 'Design tokens `--bg:#0d1117`, `--panel:#0f172a`; panels use a subtle gradient and 1px hairlines', 'CSS :root, .panel'],
  ['Severity colour coding', 'Critical neon red/magenta `#ff2e63` with glow, High orange `#ff8a1f`, Medium yellow `#facc15`, Low blue `#38bdf8`, OK green `#22c55e`. Colour is backed by text labels and a left row border', '.sev-*, tr.row.r-*'],
  ['Tight, scannable layout', '12px base type, 4px row padding, monospace for IDs/IPs/times, 12-column grid, sticky table headers', 'body, td, .grid-cols-12'],
  ['Top KPI banner (5 cards)', 'Total Events, Open Incidents, MTTA, MTTR, Active Threat Hunters, each with a sparkline and SLA hint', 'renderKpis()'],
  ['Alert funnel', 'Raw Logs > Filtered Events > Triaged Alerts > Escalated Incidents, log-scaled taper with % dropped', 'renderFunnel()'],
  ['Live alert queue', 'Timestamp, Incident ID, Severity badge, Source IP/Host, MITRE technique, Assignee, Status, Investigate button; severity filters and free-text search', 'renderQueue()'],
  ['Top Target Hosts / Failed Logins (4625/4624)', 'Ten hosts ranked by failed logons, success count, fail ratio bar, targeted account, burst signal', 'renderHosts()'],
  ['Top Malicious Source IPs with geo', 'Ten IPs with country/city, ASN/org, tags, hits, reputation score and a Block button', 'renderIps()'],
  ['Log Ingestion Health', 'Ten sources (Wazuh, Sysmon, CrowdStrike, firewall, ...) with Healthy / Lagging / Offline state, lag, EPS, uptime and sparkline', 'renderHealth(), tickHealth()'],
  ['Global time-range selector', '15m / 1h / 24h dropdown re-scales events, queue window, funnel, hosts and IPs; remembered in localStorage', '#rangeSel'],
  ['Simulation engine', 'New alert every 3.5-8 s, statuses advance every 3 s, hosts surge, sources degrade and recover', 'section 6 of the script'],
  ['Investigate drill-down with raw JSON', 'Modal with summary, timeline, playbook, analyst actions and a syntax-highlighted Wazuh-style JSON log with Copy and Wrap', 'openModal(), renderModal()'],
  ['CDN only, runs by double-click', 'Tailwind 4.1.11 pinned on jsDelivr, fonts from Google Fonts with system fallbacks', '<head>'],
], [26, 52, 22])

# ===== 2. Design decisions
H1('2. Design decisions')
H2('2.1 One file, one dependency')
P('A SOC wall display is often a locked-down kiosk, so the dashboard avoids anything that needs installing. Tailwind is loaded with the browser build (`@tailwindcss/browser@4.1.11`, a pinned version so a CDN update cannot change the look). '
  'Everything bespoke (severity badges, table styling, modal, sparklines) lives in one `<style>` block driven by CSS variables, and Tailwind utilities are used only for layout and spacing.')
NOTE('Offline behaviour: if the Tailwind CDN is unreachable the grid utilities are lost and the page degrades to a single column, but the custom components still render and the JavaScript still runs. For an air-gapped SOC, download `index.global.js` once and change the one `<script src>` line.')
H2('2.2 Colour tokens')
CODE(between(CSS, ':root {', '}', True).replace('\n  ', '\n'), 'Design tokens (CSS)')
P('The four severities are not just colours. Each has a text label, a left border on the table row, and (for Critical) a glow and a faint row tint. A colour-blind analyst, or a printout in greyscale, still reads the severity correctly.')
H2('2.3 Density without clutter')
UL(['Base font 12px, table cells 4px vertical padding, uppercase 10px column headers: about 40 queue rows fit on one 1080p screen next to the health panel.',
    'Secondary information (relative time "4s ago", host IP, tactic name) sits under the primary value in muted 10px text instead of taking a column.',
    'Monospace font for anything an analyst copies: IDs, IPs, timestamps, hashes.',
    'The page is a CSS grid; on an ultrawide or multi-monitor setup the 12 columns simply get wider, and below 640px everything stacks.'])
H2('2.4 Safe by construction')
UL(['Every dynamic string written into HTML passes through `esc()` (escapes & < > " \'). The test suite types an `<img onerror>` payload into the search box and asserts nothing is injected.',
    'External links use `rel="noopener noreferrer"`.',
    'Source IPs come from RFC 5737 documentation ranges (192.0.2.0/24, 198.51.100.0/24, 203.0.113.0/24) and ASNs from the RFC 5398 documentation range (AS64496-AS64511), so no real address or network is ever shown as malicious.',
    'localStorage access is wrapped in try/catch (`store.get/set`) because it throws in private windows and sandboxed iframes.',
    'Modal has role="dialog", aria-modal, a Tab focus trap, Escape to close, and returns focus to the button that opened it. `prefers-reduced-motion` disables animations.'])
CODE(fn('openModal') + '\n' + fn('closeModal'), 'Modal open/close with focus restore')

# ===== 3. Architecture
H1('3. Architecture')
P('The script is one IIFE in strict mode, split into eleven commented sections. Data flows one way: **model > simulation > derived metrics > renderers**. Renderers never change the model; only the simulation and analyst actions do.')
CODE('''  +------------------+      +--------------------+      +----------------+      +---------------+
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
  +------------------+      +--------------------+''', 'Data flow')
TABLE(['#', 'Section', 'Responsibility'], [
  ['1', 'Utilities', '`$`, `esc`, seeded-free random helpers (`rint`, `pick`, weighted `wpick`, exponential `expo`), formatters (`fmtCompact`, `fmtDur`), safe `store`'],
  ['2', 'Environment model', '10 monitored hosts with per-minute logon rates, 5 extra assets, 10 threat IPs, 6 analysts, 6 hunters'],
  ['3', 'Detection catalog', '%d detections: title, MITRE technique, tactic, severity pool, weight, Wazuh rule, raw-log builder and response playbook' % N_DET],
  ['4', 'State + alert factory', '`state` object, `createAlert()`, `seedAlerts()` (%s historical alerts), `advanceTo()`' % SEED],
  ['5', 'Log-source health', '10 sources with status, lag, EPS, uptime and a 24-point history'],
  ['6', 'Simulation engine', '`tick()` (3 s), `addLiveAlert()`, `stepStatuses()`, `tickHosts()`, `tickHealth()`, `tickHunters()`'],
  ['7', 'Derived metrics', '`metrics()` computes everything the UI shows from the alert list'],
  ['8', 'Renderers', '`renderKpis/Funnel/Queue/Hosts/Ips/Health/Threat`, `renderAll()`'],
  ['9', 'Investigate modal', '`buildRaw()`, `highlight()`, `renderModal()`, `applyAction()`'],
  ['10', 'Toasts', 'Critical-alert pop-ups and action confirmations (max 3 stacked)'],
  ['11', 'Events + boot', 'Listeners (event delegation), seeding, timers, test hook `window.__soc`'],
], [5, 22, 73])
P('**Single source of truth.** Every number on screen is derived from `state.alerts` plus a handful of simulation parameters (`state.eps`, `state.f1`, `state.f2`). That is why acknowledging an alert in the modal immediately changes Open Incidents, MTTA and the queue: they are all recomputed from the same list on the next `renderAll()`.')

# ===== 4. Build steps
H1('4. Step-by-step build')
H2('Step 1. Fix the visual language first')
P('Before any HTML, the colour tokens and component classes were written (`.panel`, `.chip`, `.btn`, `.sev-*`, `.status`, `.kpi`, `.tile`). Building components before layout means every later section reuses the same badge, button and table styles, so the dashboard looks like one product. '
  'The severity badge is a good example: one class per level sets text colour, tinted background and border, and Critical adds a `box-shadow` glow.')
CODE(between(CSS, '.sev { display', '.c-crit {'), 'Severity badge styles')
H2('Step 2. Lay out the page skeleton')
P('The body is a header plus a 12-column grid (`grid grid-cols-12 gap-2`). Sections declare their span: KPIs and funnel take all 12, the queue takes 8 and the health panel 4 on wide screens (`xl:col-span-8/4`), the two intel panels take 6 each (`lg:col-span-6`). Empty containers carry the IDs the renderers fill (`#queueBody`, `#healthGrid`, `#funnelStages`).')
CODE(between(HTML, '<!-- ======================= LIVE QUEUE', '<!-- ======================= LOG HEALTH'), 'Live queue markup')
H2('Step 3. Model the environment')
P('Realistic data makes the dashboard credible. Hosts are not random strings: a domain controller, a RADIUS server, an RDP jump host, Exchange, SQL, a file server and three workstations, each with a role, tier and baseline failed/successful logons per minute (`fpm`, `spm`). The RDP jump host and NPS get the highest failed-logon rates because that is where password guessing lands in real networks.')
CODE(between(JS, 'const HOSTS = [', 'const EXTRA_HOSTS'), 'Monitored hosts (baseline rates per minute)')
H2('Step 4. Build the detection catalog')
P('Each of the %d detections is one object that carries everything the UI needs, so adding a detection means adding one entry and nothing else. Fields: `title`, MITRE `tech`/`tn`/`tactic`, a `sev` pool (repeating a value weights it, e.g. Brute Force is High, High, Critical), a selection weight `w`, the Wazuh rule id/level/groups, a `data(c)` function that builds the raw log body, and a four-step `play` playbook.' % N_DET)
TABLE(['Key', 'Detection', 'MITRE', 'Tactic', 'Severity pool', 'Weight'],
      [['`%s`' % k, t, '`%s`' % te, ta, sevs(s), w] for k, t, te, tn, ta, s, w in DET], [8, 32, 10, 20, 20, 10])
CODE(template('mimi'), 'One catalog entry: Mimikatz (Sysmon EID 1 plus related EID 10 access to lsass.exe)')
P('`Log Source Silent / Offline` has weight 0: it is never drawn randomly, only raised by the health model when a source actually goes offline. This keeps the queue consistent with the health panel.')
H2('Step 5. Turn the catalog into alerts')
P('`createAlert()` picks a detection by weight, a host from the right pool (domain controllers for Kerberoasting, workstations for phishing), and decides what the "Source IP / Host" column shows: the attacker IP for external attacks, the affected host for internal ones. Critical and High alerts have a chance of being born already escalated.')
CODE(fn('createAlert'), 'Alert factory')
P('`seedAlerts()` creates %s historical alerts over 24 h, biased toward recent times (`Math.pow(rnd(), 2.2)`), and ages them: old alerts are mostly Resolved, recent ones mostly New. Incident IDs are renumbered chronologically so they increase with time like a real ticket system.' % SEED)
CODE(fn('seedAlerts'), 'Seeding history')
H2('Step 6. Model log-source health')
P('Ten sources start Healthy except two seeded problems: Azure AD / M365 is Lagging (142 s) and Linux auditd (DMZ) is Offline with 11 minutes of silence, so the panel is never boring on first load. Each tick a Healthy source has a 1.2% chance of starting to lag; a Lagging one recovers (20%) or goes Offline (3%), and going Offline raises a "Log Source Silent" alert, which links the health panel to the queue.')
CODE(fn('tickHealth'), 'Health state machine')
H2('Step 7. Write the simulation engine')
P('Two clocks run: a 3-second `tick()` that evolves the world, and a randomised 3.5-8 s timer that adds a new alert. Keeping them separate makes arrivals bursty rather than metronomic. `tick()` random-walks events-per-second with a slow sine wave, nudges the funnel ratios, advances alert statuses (biased to older open items), makes hosts surge into brute-force bursts, toggles hunters and purges alerts older than 24 h.')
CODE(fn('tick') + '\n\n' + fn('stepStatuses'), 'Simulation tick and status progression')
CODE(fn('advanceTo'), 'Status transitions record MTTA and MTTR samples')
P('Acknowledge and resolve times are drawn from an exponential distribution (`expo`), the usual model for waiting times: most alerts are handled quickly, a few take very long. Critical alerts are assigned to Tier-2 analysts and acknowledged faster.')
H2('Step 8. Derive the metrics')
P('`metrics()` filters alerts to the selected time window and computes open count, mean time to acknowledge, mean time to resolve (needs at least 3 samples, otherwise falls back to all data), and the four funnel numbers. Raw logs are `EPS x seconds in window`; filtered events are raw times `f1` (about 4.3%); triaged alerts are the window alert count times `f2` (about 7.6 rule hits per incident); escalated incidents are counted for real.')
CODE(fn('metrics'), 'Derived metrics')
H2('Step 9. Render the panels')
P('**KPIs.** Each card shows value, a context line (SLA status against a 5-minute MTTA and 4-hour MTTR target) and an SVG sparkline built from the last 40 samples. **Threat level** is derived from the number of open Critical incidents (0-1 Guarded, 2-4 Elevated, 5+ Severe).')
CODE(fn('spark'), 'Sparkline generator (inline SVG, no chart library)')
P('**Funnel.** Raw logs are millions and escalated incidents are tens, a ratio of about 1:2,500,000, so a linear shape would show one fat bar and three slivers. The funnel therefore scales each stage by `log10`, mapping the largest to 100% height and the smallest to 20%, and draws four trapezoids that join edge to edge. The text under each stage shows the real number and the percentage dropped.')
CODE(fn('renderFunnel'), 'Log-scaled alert funnel')
P('**Queue.** The newest 40 alerts matching the severity buttons and search text are rendered as one HTML string. A single click listener on `<tbody>` handles every Investigate button (event delegation), so re-rendering every few seconds does not leak listeners. The scroll position is saved and restored across re-renders so the analyst is not thrown back to the top mid-read.')
CODE(fn('renderQueue'), 'Live alert queue')
P('**Hosts and IPs.** Failed logons are `fpm x minutes x surge multiplier x noise`, so changing the time range scales every number consistently. A host in a surge shows "Active burst"; one flagged compromised shows "4624 after 4625 burst", the classic signature of a successful brute force. The Block button on an IP simulates a firewall push (hits drop 96%).')
CODE(fn('renderHosts', 14), 'Top target hosts (4625 / 4624)')
H2('Step 10. Build the Investigate drill-down')
P('`buildRaw()` assembles a Wazuh-style alert: timestamp, `rule` with MITRE mapping, `agent`, `decoder`, the detection-specific `data` from the catalog, and a `soc` block with asset context and threat-intel enrichment. The JSON is cached on the alert, so reopening shows identical data. `highlight()` colours keys, strings, numbers and booleans with one regular expression and escapes every token.')
CODE(fn('buildRaw'), 'Raw log builder')
P('The modal also shows an incident summary, a four-point timeline (precursor, rule fired, enrichment, what to hunt next) and the recommended playbook. Five analyst actions (Acknowledge, Assign to me, Escalate to T2, False positive, Resolve) update the same alert object, so the KPIs react immediately.')
CODE(fn('applyAction'), 'Analyst actions')
H2('Step 11. Wire events and boot')
P('Listeners use delegation (`#queueBody`, `#ipsBody`, `#mBody`, `#sevFilters`). Boot order matters: seed alerts, run one health tick, render everything, then start the clock, the 3-second tick and the alert scheduler. The last line exposes `window.__soc` for tests and debugging.')
CODE(between(JS, 'seedAlerts();\ntickHealth();', 'window.__soc'), 'Boot sequence')

# ===== 5. Testing
H1('5. Testing and verification')
P('Three layers were used. **Static**: the script is parsed with `new Function()` to catch syntax errors. **Behavioural**: `npm test` loads the page in jsdom and runs 42 assertions over hundreds of simulated ticks. **Visual**: the page was opened in headless Chromium at 1920x1080, 1366x768 and 390x844, checked for console errors and horizontal overflow, and photographed for this report.')
TABLE(['Area', 'What is asserted'], [
  ['Render', '210 seeded alerts with unique IDs; <= 40 queue rows of 9 columns; 5 KPIs, 4 funnel stages, 10 health tiles, 10 host rows, 10 IP rows'],
  ['Funnel', 'Strictly narrows for every range (for example 107.1M > 4.6M > 1,596 > 27)'],
  ['Time range', 'Each of 15m / 1h / 24h updates the KPI label and recomputes the funnel'],
  ['Simulation', '300 ticks plus live alerts: alerts accumulate, >24 h alerts are purged, health states stay in the allowed set'],
  ['Filters', 'Critical filter shows only Critical; search narrows rows; empty state appears; an HTML payload typed in search is not injected'],
  ['Modal', 'All %d detections open and their raw JSON parses with the right MITRE ID, host and incident ID' % N_DET],
  ['Correctness', 'Windows paths are single-escaped in JSON; Mimikatz is Sysmon EID 1 at Wazuh level 15'],
  ['Actions', 'Acknowledge, Escalate and False Positive change state; buttons disable once closed; resolve time >= acknowledge time; Escape closes'],
  ['Controls', 'Block IP, Pause and Resume, threat-level badge, toast cap'],
], [16, 84])
H2('5.1 Defects found and fixed during verification')
TABLE(['Defect', 'Cause', 'Fix'], [
  ['Raw JSON showed `C:\\\\\\\\Users\\\\\\\\...` (doubled backslashes)', 'Paths were escaped once in the JavaScript source and again by `JSON.stringify`', 'Halved every backslash run inside the catalog; a test now asserts the parsed value equals `C:\\Users\\Public\\Downloads\\mimikatz.exe`'],
  ['Resolve time could be earlier than acknowledge time', 'Acknowledge clamps MTTA to at least 0.2 min, Resolve did not', '`resMin = Math.max(ackMin, elapsed)`'],
  ['Page scrolled sideways by 21px on a phone', '"% dropped" chips in four narrow funnel columns could not wrap', 'Chips hidden and numbers shrunk below 640px; funnel container clips overflow'],
  ['Dead and duplicated code in `createAlert`', 'Leftover conditionals from iteration (`a.t === \'x\'`, a ternary with identical branches)', 'Replaced by one commented rule for the Source column'],
  ['Old tests and report described a different build', 'Earlier iteration used other element IDs and hooks', 'Tests rewritten against the current DOM; report regenerated from the code'],
], [30, 34, 36])
NOTE('The build sandbox could not reach the Tailwind CDN, so for testing and screenshots the identical pinned build (4.1.11) was installed from npm and served in place of the CDN URL. Google Fonts were also unreachable, so screenshots use the fallback system fonts. On a normal internet connection the page loads Inter and JetBrains Mono.')
PB()
H2('5.2 Screenshots')
IMG('docs/screenshots/00-dashboard-full.png', 'Figure 1. Full dashboard at 1920x1080 (Last 24h).', 487)
IMG('docs/screenshots/01-kpi-banner.png', 'Figure 2. KPI banner: Total Events, Open Incidents, MTTA, MTTR, Active Threat Hunters.', 487)
IMG('docs/screenshots/02-alert-funnel.png', 'Figure 3. Alert funnel, log-scaled: Raw Logs > Filtered Events > Triaged Alerts > Escalated Incidents.', 487)
IMG('docs/screenshots/03-live-alert-queue.png', 'Figure 4. Real-time live alert queue with severity filters and search.', 487)
IMG('docs/screenshots/04-log-health.png', 'Figure 5. Log ingestion health: Healthy, Lagging (Azure AD / M365) and Offline (Linux auditd).', 400)
IMG('docs/screenshots/05-top-hosts.png', 'Figure 6. Top target hosts with Windows 4625 / 4624 counts.', 487)
IMG('docs/screenshots/06-malicious-ips.png', 'Figure 7. Top malicious source IPs with geo, ASN, tags, reputation and Block action.', 487)
IMG('docs/screenshots/07-investigate-modal.png', 'Figure 8. Investigate drill-down for a Critical Mimikatz alert, with raw JSON log.', 487)
IMG('docs/screenshots/08-range-15m.png', 'Figure 9. Global time range set to Last 15m: KPIs, funnel and queue rescale.', 487)
IMG('docs/screenshots/09-mobile.png', 'Figure 10. Phone width (390px): panels stack, no horizontal scroll.', 220)

# ===== 6. Packaging
H1('6. Packaging and GitHub')
OL(['The folder is named `SOC Dashboard` and holds `index.html`, `README.md`, `LICENSE` (MIT), `.gitignore`, `package.json`, `tests/`, `tools/`, `docs/screenshots/`, `.github/workflows/pages.yml` and both reports.',
    '`git init -b main`, `git add -A`, `git commit` creates the local repository (already done in the delivered folder).',
    'On github.com create a new empty repository (for example `soc-dashboard`), without a README or licence so the histories do not clash.',
    'In the project folder run: `git remote add origin https://github.com/<your-user>/soc-dashboard.git` then `git push -u origin main`.',
    'Optional live demo: in the repository go to Settings > Pages > Source: GitHub Actions. The included workflow publishes `index.html` and `docs/` on every push to `main`.',
    'To regenerate these reports after changing the code: `pip install reportlab`, then `python3 tools/build_report.py`.'])

# ===== 7. Limitations
H1('7. Limitations and next steps')
UL(['**Simulated data.** Nothing is read from a real SIEM. The numbers are plausible, not measured.',
    '**Browser state only.** Analyst actions (acknowledge, escalate, block) live in memory and are lost on reload; only the time range is remembered.',
    '**Geo context is tabular.** There is no map; coordinates were left out on purpose to keep the display dense.',
    '**CDN dependency.** Tailwind needs internet on first load unless you host the script locally.'])
P('**Connecting real data** is a contained change. Replace `createAlert()` / `addLiveAlert()` with a fetch or WebSocket client for your platform (Wazuh API `/alerts`, Elastic or Splunk search, Sentinel), map each alert onto the `state.alerts` shape (`id, ts, title, sev, host, srcLabel, status, raw`), and keep the renderers unchanged. Then replace the health model with real agent and ingestion-lag queries, and send analyst actions back to your case-management API.')
P('Further ideas: persist actions in IndexedDB, add sound for Critical alerts, a shift-handover export, per-analyst workload view, and a MITRE ATT&CK heat map built from `CAT[type].tech`.')

# ===== Appendices
H1('Appendix A. Simulation parameters')
TABLE(['Parameter', 'Value', 'Meaning'], [
  ['World tick', '3 s', '`setInterval` calling `tick()` then `renderAll()`'],
  ['Alert arrival', '3.5-8 s random', '`scheduleNextAlert()`'],
  ['Seeded history', '%s alerts / 24 h' % SEED, 'Biased toward recent times'],
  ['Alert cap / retention', '600 alerts / 24 h', 'Oldest dropped first'],
  ['Events per second', '760-1,900 (starts 1,240)', 'Random walk plus slow sine'],
  ['Filter ratio f1', '3.6-5.2% of raw', 'Raw logs to filtered events'],
  ['Rule hits per incident f2', '6.5-9.5', 'Window alerts to triaged alerts'],
  ['SLA targets', 'MTTA 5 min, MTTR 4 h', 'Green tick when met, orange arrow when not'],
  ['Threat level', '0-1 / 2-4 / 5+ open Critical', 'Guarded / Elevated / Severe'],
  ['Host surge', '3% chance per tick, 10-26 ticks, 3-8x', '30% of surges flagged compromised'],
  ['Source health', '1.2% to Lagging; Lagging 20% recover, 3% Offline; Offline 8% to Lagging', 'Per 3 s tick'],
  ['Queue rows shown', '40 newest matching', 'Count of all matches shown in header'],
], [28, 34, 38])
H1('Appendix B. Glossary')
TABLE(['Term', 'Meaning'], [
  ['MTTA / MTTR', 'Mean time to acknowledge / resolve: average minutes from alert creation to first analyst action / to closure'],
  ['EPS', 'Events per second ingested by the SIEM'],
  ['Funnel', 'The reduction from raw logs to the few incidents a human must handle'],
  ['4625 / 4624', 'Windows Security events: failed / successful logon'],
  ['MITRE ATT&CK', 'Public knowledge base of adversary tactics and techniques (for example T1110 Brute Force)'],
  ['Sysmon', 'Microsoft Sysinternals driver that logs process, network and registry activity (EID 1 process create, EID 10 process access)'],
  ['Wazuh', 'Open-source XDR/SIEM whose alert JSON format this dashboard imitates'],
  ['Kerberoasting', 'Requesting service tickets to crack service-account passwords offline (T1558.003)'],
  ['RFC 5737 / 5398', 'Standards reserving IP address blocks and AS numbers for documentation so examples never hit real networks'],
  ['Tier 1 / Tier 2', 'First-line triage analysts / deeper investigation and response analysts'],
], [20, 80])
H1('Appendix C. Project files')
CODE('''SOC Dashboard/
|-- index.html                          the dashboard (open this)
|-- README.md                           quick start
|-- LICENSE                             MIT
|-- package.json  .gitignore            npm test script, ignore rules
|-- SOC_Dashboard_Project_Report.txt    this report, plain text
|-- SOC_Dashboard_Project_Report.pdf    this report, PDF with screenshots
|-- tests/dom-test.js                   42 behavioural assertions (jsdom)
|-- tools/build_report.py               regenerates both reports from index.html
|-- docs/screenshots/                   figures used in the PDF and README
`-- .github/workflows/pages.yml         optional GitHub Pages deployment''')


# ----------------------------------------------------------------- TXT renderer
def strip_inline(t):
    t = re.sub(r'\*\*(.+?)\*\*', r'\1', t)
    return t.replace('`', '')


def wrap_code(code, width):
    out = []
    for line in code.split('\n'):
        line = line.rstrip('\n')
        while len(line) > width:
            out.append(line[:width])
            line = '    ' + line[width:]
        out.append(line)
    return out


def txt_table(head, rows, widths, total=96):
    s = float(sum(widths))
    cw = [max(8, int(total * w / s) - 3) for w in widths]
    def fmt_row(cells):
        wrapped = [textwrap.wrap(strip_inline(c), cw[i]) or [''] for i, c in enumerate(cells)]
        h = max(len(w) for w in wrapped)
        lines = []
        for k in range(h):
            lines.append(' | '.join((wrapped[i][k] if k < len(wrapped[i]) else '').ljust(cw[i]) for i in range(len(cells))))
        return lines
    sep = '-+-'.join('-' * w for w in cw)
    out = fmt_row(head) + [sep]
    for r in rows:
        out += fmt_row(r)
    return out


def render_txt():
    W = 96
    out = []
    out.append('=' * W)
    out.append('SOC COMMAND CENTER - PROJECT REPORT')
    out.append('Step-by-step analysis of how the dashboard was designed, built, tested and packaged')
    out.append('Prepared for: Rushikesh Kulkarni')
    out.append('Date: %s' % TODAY)
    out.append('Deliverable: index.html (single file, %d lines)' % LINES)
    out.append('=' * W)
    out.append('')
    out.append('CONTENTS')
    for b in B:
        if b[0] == 'h1':
            out.append('  ' + b[1])
    out.append('')
    for b in B:
        k = b[0]
        if k == 'h1':
            out += ['', '', '=' * W, b[1].upper(), '=' * W, '']
        elif k == 'h2':
            out += ['', b[1], '-' * len(b[1]), '']
        elif k == 'p':
            out += textwrap.wrap(strip_inline(b[1]), W) + ['']
        elif k == 'note':
            out += textwrap.wrap('NOTE: ' + strip_inline(b[1]), W - 4, initial_indent='  ', subsequent_indent='  ') + ['']
        elif k in ('ul', 'ol'):
            for i, it in enumerate(b[1], 1):
                mark = '  - ' if k == 'ul' else '  %d. ' % i
                out += textwrap.wrap(strip_inline(it), W, initial_indent=mark, subsequent_indent=' ' * len(mark))
            out.append('')
        elif k == 'code':
            if b[2]:
                out.append(b[2])
            out += ['    ' + l for l in wrap_code(b[1], W - 6)]
            out.append('')
        elif k == 'table':
            out += txt_table(b[1], b[2], b[3], W) + ['']
        elif k == 'img':
            out += ['[%s  (image: %s - see the PDF report or open the file)]' % (b[2], b[1]), '']
    return '\n'.join(out) + '\n'


# ----------------------------------------------------------------- PDF renderer
def render_pdf(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
                                    Preformatted, Image, PageBreak, KeepTogether, CondPageBreak, ListFlowable, ListItem)
    from reportlab.platypus.tableofcontents import TableOfContents
    from reportlab.lib.utils import ImageReader

    fdir = '/usr/share/fonts/truetype/dejavu/'
    pdfmetrics.registerFont(TTFont('Body', fdir + 'DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('Body-Bold', fdir + 'DejaVuSans-Bold.ttf'))
    pdfmetrics.registerFont(TTFont('Body-Italic', fdir + 'DejaVuSans-Oblique.ttf'))
    pdfmetrics.registerFont(TTFont('Mono', fdir + 'DejaVuSansMono.ttf'))
    pdfmetrics.registerFont(TTFont('Mono-Bold', fdir + 'DejaVuSansMono-Bold.ttf'))
    pdfmetrics.registerFontFamily('Body', normal='Body', bold='Body-Bold', italic='Body-Italic', boldItalic='Body-Bold')
    pdfmetrics.registerFontFamily('Mono', normal='Mono', bold='Mono-Bold', italic='Mono', boldItalic='Mono-Bold')

    NAVY, CYAN, GREY, LIGHT = colors.HexColor('#0f172a'), colors.HexColor('#0e7490'), colors.HexColor('#475569'), colors.HexColor('#f1f5f9')
    S = {
        'p': ParagraphStyle('p', fontName='Body', fontSize=9.2, leading=13.2, textColor=colors.HexColor('#1e293b'), spaceAfter=6),
        'h1': ParagraphStyle('h1', fontName='Body-Bold', fontSize=17, leading=21, textColor=NAVY, spaceBefore=10, spaceAfter=8, keepWithNext=1),
        'h2': ParagraphStyle('h2', fontName='Body-Bold', fontSize=11.5, leading=15, textColor=CYAN, spaceBefore=10, spaceAfter=4, keepWithNext=1),
        'cap': ParagraphStyle('cap', fontName='Body-Italic', fontSize=8, leading=10.5, textColor=GREY, spaceBefore=2, spaceAfter=8),
        'cell': ParagraphStyle('cell', fontName='Body', fontSize=7.9, leading=10.4, textColor=colors.HexColor('#1e293b')),
        'cellh': ParagraphStyle('cellh', fontName='Body-Bold', fontSize=7.9, leading=10.4, textColor=colors.white),
        'note': ParagraphStyle('note', fontName='Body', fontSize=8.6, leading=12, textColor=colors.HexColor('#7c2d12'),
                               backColor=colors.HexColor('#fff7ed'), borderColor=colors.HexColor('#fdba74'), borderWidth=0.6,
                               borderPadding=(5, 6, 5, 6), spaceBefore=4, spaceAfter=10, leftIndent=6, rightIndent=6),
        'code': ParagraphStyle('code', fontName='Mono', fontSize=6.7, leading=8.6, textColor=colors.HexColor('#0f172a'),
                               backColor=LIGHT, borderColor=colors.HexColor('#cbd5e1'), borderWidth=0.5, borderPadding=(4, 5, 4, 5),
                               leftIndent=5, rightIndent=5, spaceBefore=3, spaceAfter=2),
        'toc1': ParagraphStyle('toc1', fontName='Body', fontSize=9.5, leading=15, leftIndent=0),
    }

    def inline(t):
        t = t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        t = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', t)
        t = re.sub(r'`(.+?)`', r'<font name="Mono" size="7.6" color="#0f4c5c">\1</font>', t)
        return t

    class Doc(BaseDocTemplate):
        def afterFlowable(self, f):
            if isinstance(f, Paragraph) and f.style.name == 'h1':
                self.notify('TOCEntry', (0, f.getPlainText(), self.page))

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont('Body', 7.5)
        canvas.setFillColor(GREY)
        canvas.drawString(54, 30, 'SOC Command Center - Project Report')
        canvas.drawRightString(A4[0] - 54, 30, 'Page %d' % doc.page)
        canvas.setStrokeColor(colors.HexColor('#cbd5e1'))
        canvas.line(54, 42, A4[0] - 54, 42)
        canvas.restoreState()

    def cover_bg(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, A4[1] - 330, A4[0], 330, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#ff2e63'))
        canvas.rect(0, A4[1] - 334, A4[0], 4, fill=1, stroke=0)
        canvas.restoreState()

    doc = Doc(path, pagesize=A4, leftMargin=54, rightMargin=54, topMargin=54, bottomMargin=58,
              title='SOC Command Center - Project Report', author='Rushikesh Kulkarni',
              subject='Step-by-step analysis of how the dashboard was built')
    fw, fh = A4[0] - 108, A4[1] - 112
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[Frame(54, 54, fw, A4[1] - 108, id='c')], onPage=cover_bg),
        PageTemplate(id='body', frames=[Frame(54, 58, fw, fh, id='f')], onPage=footer)])

    from reportlab.platypus import NextPageTemplate
    st = []
    # cover
    st.append(Spacer(1, 70))
    st.append(Paragraph('SOC Command Center', ParagraphStyle('t', fontName='Body-Bold', fontSize=34, leading=40, textColor=colors.white)))
    st.append(Paragraph('Project Report', ParagraphStyle('t2', fontName='Body', fontSize=22, leading=28, textColor=colors.HexColor('#67e8f9'))))
    st.append(Spacer(1, 14))
    st.append(Paragraph('Step-by-step analysis of how the Tier 1 / Tier 2 SOC dashboard was designed, built, tested and packaged',
                        ParagraphStyle('t3', fontName='Body', fontSize=12, leading=17, textColor=colors.HexColor('#cbd5e1'))))
    st.append(Spacer(1, 150))
    facts = [['Date', TODAY], ['Deliverable', 'index.html, one self-contained file (%d lines)' % LINES],
             ['Technology', 'HTML, Tailwind CSS (CDN), vanilla JavaScript, no build step'],
             ['Data', 'Simulated in the browser; nothing is collected or transmitted'],
             ['Detections modelled', '%d, each mapped to MITRE ATT&CK with a response playbook' % N_DET],
             ['Verification', 'Syntax check, 42 DOM assertions, headless Chromium at 3 screen sizes']]
    ft = Table([[Paragraph('<b>%s</b>' % a, S['cell']), Paragraph(inline(b), S['cell'])] for a, b in facts], colWidths=[110, fw - 110])
    ft.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('TOPPADDING', (0, 0), (-1, -1), 5), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    st.append(ft)
    st.append(NextPageTemplate('body'))
    st.append(PageBreak())
    st.append(Paragraph('Contents', S['h1'].clone('ct', keepWithNext=0)))
    toc = TableOfContents()
    toc.levelStyles = [S['toc1']]
    toc.dotsMinLevel = 0
    st.append(toc)
    st.append(PageBreak())

    def wrap_for_pdf(code):
        return '\n'.join(wrap_code(code, 112))

    for b in B:
        k = b[0]
        if k == 'h1':
            st.append(CondPageBreak(150))
            st.append(Paragraph(inline(b[1]), S['h1']))
        elif k == 'h2':
            st.append(CondPageBreak(90))
            st.append(Paragraph(inline(b[1]), S['h2']))
        elif k == 'p':
            st.append(Paragraph(inline(b[1]), S['p']))
        elif k == 'note':
            st.append(Paragraph('<b>Note.</b> ' + inline(b[1]), S['note']))
        elif k in ('ul', 'ol'):
            items = [ListItem(Paragraph(inline(i), S['p'].clone('li', spaceAfter=2)), leftIndent=14) for i in b[1]]
            if k == 'ul':
                st.append(ListFlowable(items, bulletType='bullet', start='•', leftIndent=14, bulletFontSize=8))
            else:
                st.append(ListFlowable(items, bulletType='1', leftIndent=16, bulletFontName='Body-Bold', bulletFontSize=8.5))
            st.append(Spacer(1, 5))
        elif k == 'code':
            block = Preformatted(wrap_for_pdf(b[1]), S['code'])
            if b[2]:
                st.append(Paragraph(b[2], S['cap'].clone('capt', spaceBefore=6, spaceAfter=2, textColor=colors.HexColor('#0f172a'), keepWithNext=1)))
            st.append(block)
            st.append(Spacer(1, 8))
        elif k == 'table':
            head, rows, widths = b[1], b[2], b[3]
            tot = float(sum(widths))
            cw = [fw * w / tot for w in widths]
            data = [[Paragraph(inline(h), S['cellh']) for h in head]] + [[Paragraph(inline(c), S['cell']) for c in r] for r in rows]
            t = Table(data, colWidths=cw, repeatRows=1)
            style = [('BACKGROUND', (0, 0), (-1, 0), NAVY), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                     ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#cbd5e1')),
                     ('TOPPADDING', (0, 0), (-1, -1), 3), ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                     ('LEFTPADDING', (0, 0), (-1, -1), 4), ('RIGHTPADDING', (0, 0), (-1, -1), 4)]
            for i in range(2, len(data), 2):
                style.append(('BACKGROUND', (0, i), (-1, i), LIGHT))
            t.setStyle(TableStyle(style))
            st.append(t)
            st.append(Spacer(1, 9))
        elif k == 'img':
            p = os.path.join(ROOT, b[1])
            iw, ih = ImageReader(p).getSize()
            w = min(b[3], fw)
            h = w * ih / iw
            if h > fh - 70:
                h = fh - 70
                w = h * iw / ih
            st.append(KeepTogether([Image(p, width=w, height=h), Paragraph(b[2], S['cap'])]))
        elif k == 'pb':
            st.append(PageBreak())

    doc.multiBuild(st)


if __name__ == '__main__':
    txt_path = os.path.join(ROOT, 'SOC_Dashboard_Project_Report.txt')
    pdf_path = os.path.join(ROOT, 'SOC_Dashboard_Project_Report.pdf')
    open(txt_path, 'w', encoding='utf-8').write(render_txt())
    print('wrote', txt_path)
    render_pdf(pdf_path)
    print('wrote', pdf_path)
