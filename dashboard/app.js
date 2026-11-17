/* SuisseCL audit dashboard. Vanilla JS, no framework. Every value shown comes from bundle/*.js, which
   swiss/dashboard/build_bundle.py generates from the repo's registries, QC reports and results. */
(function () {
  'use strict';
  const B = window.SCL || {};
  const meta = B.meta, prov = B.provenance;
  const N = prov ? prov.nodes : {};
  const settings = (prov && prov.settings) || {};
  const COLOURS = settings.classification_colours || {};
  const $ = (s, el) => (el || document).querySelector(s);
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const REPO = '../';   // repo root relative to dashboard/index.html (works from file:// and from a server rooted at the repo)

  const KIND_LABEL = {
    source: 'Data source', derived_dataset: 'Derived dataset', transform: 'Transformation', model: 'Model',
    parameter: 'Parameter', decision: 'Decision', assumption: 'Assumption', issue: 'Issue', controller: 'Controller',
    reward: 'Reward', experiment: 'Experiment', kpi: 'KPI', validation_check: 'Validation check', qc_report: 'QC report',
    series: 'Series', card: 'Element', panel: 'Panel', figure: 'Figure', map_box: 'System-map box',
  };
  const REL_LABEL = {
    shows: 'built from', mentions: 'mentions', input: 'input', output: 'output', derived_from: 'derived from',
    decided_in: 'decided in', uses_model: 'uses model', uses_dataset: 'uses dataset', uses_controller: 'uses controller',
    uses_reward: 'uses reward', has_parameter: 'parameter', parameter_of: 'parameter of', qc: 'QC',
  };

  // ------------------------------------------------------------------ small helpers
  function badge(cls) {
    if (!cls) return '';
    const c = COLOURS[cls] || '#4a5568';
    return `<span class="cls" style="--c:${c}">${esc(cls)}</span>`;
  }
  function idLink(id, withTitle, rawId) {
    const n = N[id];
    if (!n) return `<span class="dangling" title="not in any registry">${esc(id)}</span>`;
    const open = n.kind === 'issue' && n.open;
    const t = withTitle ? ` <span class="lt">${esc(short(n.title, 90))}</span>` : '';
    return `<a class="idlink${open ? ' open-issue' : ''}" href="#node=${encodeURIComponent(id)}" title="${esc(n.title)}">${esc(rawId ? id : displayId(id))}</a>${t}`;
  }
  function displayId(id) { const n = N[id]; return n && n.ui ? n.title : id; }
  function short(s, k) { s = String(s || ''); return s.length > k ? s.slice(0, k - 1) + '…' : s; }
  function linkIds(text) {   // turn registry IDs in free text into links (IDs extracted at build time are the authority)
    return esc(text).replace(/\b((?:SRC|DER|TR|ISS|ALG|EXP|R|M|D|A)-\d{3}[a-z]?|V\d{1,2})\b/g, (m) => (N[m] ? idLink(m) : m));
  }
  function docLink(path) { return `<a href="${REPO}${esc(path)}" target="_blank" rel="noopener">${esc(path)}</a>`; }
  function section(title, body, cls) { return body ? `<section class="cs ${cls || ''}"><h4>${esc(title)}</h4>${body}</section>` : ''; }
  function fmt(v) {
    if (v === null || v === undefined) return '<span class="muted">n/a</span>';
    if (typeof v === 'number') return Number.isInteger(v) ? String(v) : String(+v.toPrecision(6));
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    return esc(v);
  }
  function flatten(obj, prefix, out, depth) {
    out = out || []; depth = depth || 0;
    if (obj !== null && typeof obj === 'object' && !Array.isArray(obj) && depth < 6) {
      for (const [k, v] of Object.entries(obj)) flatten(v, prefix ? prefix + ' › ' + k : k, out, depth + 1);
    } else if (Array.isArray(obj)) {
      if (obj.every((x) => x === null || typeof x !== 'object')) out.push([prefix, obj.map((x) => (typeof x === 'number' ? +x.toPrecision(6) : x)).join(', ')]);
      else obj.forEach((x, i) => flatten(x, prefix + ' › ' + i, out, depth + 1));
    } else out.push([prefix, obj]);
    return out;
  }
  function kvTable(rows, cls) {
    return `<table class="kv ${cls || ''}">${rows.map(([k, v]) => `<tr><th>${esc(k)}</th><td>${typeof v === 'string' ? linkIds(v) : fmt(v)}</td></tr>`).join('')}</table>`;
  }

  // ------------------------------------------------------------------ card sections
  function secHead(n) {
    const kind = KIND_LABEL[n.kind] || n.kind;
    const status = n.kind === 'issue' ? `<span class="st ${n.open ? 'st-open' : 'st-closed'}">${n.open ? 'open' : 'closed'}: ${esc(short(n.status, 80))}</span>`
      : n.kind === 'validation_check' ? `<span class="st ${n.passed ? 'st-pass' : 'st-warn'}">${esc(short(n.status, 100))}</span>`
      : n.status ? `<span class="st">${esc(short(n.status, 100))}</span>` : '';
    const origin = n.fields && n.fields.origin ? `<span class="st">${n.fields.origin === 'own' ? 'our own computation' : 'CityLearn KPI, normalised to the conventional counterfactual (1.0 = counterfactual, lower is better)'}</span>` : '';
    const na = n.fields && n.fields.not_applicable ? '<span class="st st-warn">not applicable by design</span>' : '';
    return `<div class="ch">
      <div class="ckind">${esc(kind)} · <code>${esc(n.id)}</code></div>
      <h3>${esc(n.title)} ${badge(n.classification)}</h3>
      ${n.classification_raw && n.classification_raw !== n.classification ? `<div class="muted small">classification in registry: ${esc(n.classification_raw)}</div>` : ''}
      <div class="sts">${status}${origin}${na}</div>
      ${n.summary ? `<p class="summary">${linkIds(n.summary)}</p>` : ''}
      ${(n.caveats || []).map((c) => `<div class="caveat">⚠ ${linkIds(c)}</div>`).join('')}
    </div>`;
  }

  function secNumbers(n) {
    if (!n.numbers || !n.numbers.length) return '';
    return section('Key numbers', `<div class="nums">${n.numbers.map((x) => `<div class="numtile"><div class="nv">${esc(x.value)} <span class="nu">${x.unit === "-" ? "" : esc(x.unit)}</span></div><div class="nl">${esc(x.label)}</div></div>`).join('')}</div>`);
  }

  function secLineage(n) {
    const tree = n.lineage_tree || {};
    if (!n.lineage || !n.lineage.length) return '';
    const seen = new Set();
    function render(id, depth) {
      const ups = tree[id] || [];
      const again = seen.has(id); seen.add(id);
      const node = N[id];
      const lbl = id === n.id ? `<b>${esc(displayId(id))}</b>` : idLink(id);
      const cls = node && node.classification ? badge(node.classification) : '';
      const kids = !again && ups.length && depth < 12 ? `<ul>${ups.map((u) => render(u, depth + 1)).join('')}</ul>` : '';
      return `<li>${lbl} ${node && id !== n.id ? `<span class="lk">${esc(KIND_LABEL[node.kind] || node.kind)}</span>` : ''} ${cls}${again && ups.length ? ' <span class="muted">(see above)</span>' : ''}${kids}</li>`;
    }
    // breadcrumbs: shortest upstream chain from this node to each SRC-* (or to the last node if no source is reached)
    const parent = {}, q = [n.id]; parent[n.id] = null;
    while (q.length) { const x = q.shift(); for (const u of tree[x] || []) if (!(u in parent)) { parent[u] = x; q.push(u); } }
    const ends = n.lineage.filter((x) => x.startsWith('SRC-'));
    const targets = ends.length ? ends : [n.lineage[n.lineage.length - 1]];
    const crumbs = targets.map((t) => {
      const chain = []; for (let x = t; x != null; x = parent[x]) chain.unshift(x);
      return `<div class="crumb">${chain.map((x) => (x === n.id ? `<b>${esc(displayId(x))}</b>` : idLink(x) + (N[x] && N[x].classification ? ' ' + badge(N[x].classification) : ''))).join(' <span class="arr">←</span> ')}</div>`;
    }).join('');
    const endNote = ends.length ? '' : `<p class="small warnc">No measured source upstream: the chain ends in ${idLink(targets[0])} (${esc(KIND_LABEL[N[targets[0]].kind] || '')}).</p>`;
    return section('Lineage (upstream)', `${crumbs}${endNote}<details class="small"><summary>full upstream tree (${n.lineage.length} nodes)</summary><ul class="tree">${render(n.id, 0)}</ul></details>`);
  }

  function secMethod(n) {
    let body = '';
    if (n.formula) body += `<div class="formula">${esc(n.formula)}</div>`;
    if (n.kind === 'reward' && n.fields) {
      if (n.fields.formula) body += `<div class="formula">${esc(n.fields.formula)}</div>`;
      if (n.fields.terms) body += `<table class="kv"><tr><th>Term</th><th>Definition</th><th>Unit</th><th>Weight</th><th>Scale</th></tr>${n.fields.terms.map((t) => `<tr><td>${esc(t.Term)}</td><td>${esc(t.Definition)}</td><td>${esc(t.Unit)}</td><td>${esc(t['Default weight'])}</td><td>${esc(t.Scale)}</td></tr>`).join('')}</table>`;
    }
    for (const c of n.code || []) {
      const where = `${c.file}${c.symbol ? '::' + c.symbol : ''}`;
      const commit = c.commit ? `commit <code>${esc(c.commit)}</code>` : '<span class="warnc">not committed</span>';
      const dirty = c.uncommitted_changes ? ' <span class="warnc">(file has uncommitted changes; excerpt is the working copy)</span>' : '';
      const lines = String(c.source || '').split('\n');
      const numbered = lines.map((l, i) => `<span class="ln">${(c.line || 1) + i}</span>${esc(l)}`).join('\n');
      const defs = c.defines && c.defines.length ? `<div class="small muted">defines: ${c.defines.map(esc).join(', ')}</div>` : '';
      body += `<details class="code"${(n.code || []).length === 1 ? ' open' : ''}><summary><code>${esc(where)}</code> · ${esc(c.kind || '')} · ${commit}${dirty}</summary>${defs}<pre>${numbered}</pre></details>`;
    }
    return section('Method and code', body);
  }

  function modelsOf(n) {
    const ms = new Set();
    if (n.kind === 'model') ms.add(n.id);
    for (const e of n.edges) if (e.to.startsWith('M-') && N[e.to]) ms.add(e.to);
    return [...ms];
  }
  function secParameters(n) {
    let params = [];
    if (n.kind === 'parameter') params = [n.id];
    for (const m of modelsOf(n)) for (const e of N[m].edges) if (e.rel === 'has_parameter') params.push(e.to);
    params = [...new Set(params)].filter((p) => N[p]);
    if (!params.length) return '';
    const rows = params.map((p) => {
      const f = N[p].fields;
      const proxy = /PROXY|judgement/i.test(f.source || '');
      return `<tr${proxy ? ' class="proxy" title="proxy or judgement, not a direct literature value"' : ''}><td><a href="#node=${encodeURIComponent(p)}">${esc(f.name)}</a></td><td><code>${esc(f.parameter)}</code></td><td class="num">${esc(f.value)}</td><td>${esc(f.unit)}</td><td class="cite">${linkIds(f.source_resolved || f.source)}${f.source_resolved ? `<div class="muted">registry text: "${esc(f.source)}" (resolved to the row above)</div>` : ''}</td><td>${esc(f.classification)}</td></tr>`;
    }).join('');
    return section(`Parameters (${modelsOf(n).join(', ') || n.fields.model_id})`, `<div class="scrollx"><table class="kv params"><tr><th>Name</th><th>Parameter</th><th>Value</th><th>Unit</th><th>Source / citation</th><th>Class</th></tr>${rows}</table></div>`);
  }

  function secQC(n) {
    let body = '';
    const qcs = new Set(n.qc || []);
    for (const e of n.edges) if (N[e.to] && N[e.to].kind === 'qc_report') qcs.add(e.to);
    if (n.kind === 'qc_report') {
      body += kvTable(flatten(n.results), 'qc');
    }
    for (const q of qcs) {
      const r = N[q];
      if (!r) continue;
      body += `<details class="qcd"><summary>${idLink(q)} ${esc(r.title)}</summary>${kvTable(flatten(r.results), 'qc')}</details>`;
    }
    const vs = n.kind === 'validation_check' ? [n.id] : n.edges.filter((e) => N[e.to] && N[e.to].kind === 'validation_check').map((e) => e.to);
    for (const v of vs) {
      const c = N[v];
      const head = `<b>${esc(v)}</b> ${esc(c.title)} — <span class="${c.passed ? 'okc' : 'warnc'}">${esc(c.status)}</span><div class="small">${linkIds(c.fields.Result)}</div>`;
      body += v === n.id ? head + (c.results ? `<details><summary>numbers (${esc(c.results_key)})</summary>${kvTable(flatten(c.results), 'qc')}</details>` : '<p class="muted small">no machine-readable numbers for this check in validation_phase_a.json</p>')
        : `<div class="vrow">${idLink(v)} ${head}</div>`;
    }
    return section('QC and validation', body);
  }

  function secRelated(n) {
    const groups = {decision: [], assumption: [], issue: [], other: [], used_by: []};
    const seen = new Set();
    const add = (id, rel, dir) => {
      const key = id + '|' + dir;
      if (!N[id] || seen.has(key) || id === n.id) return;
      seen.add(key);
      const k = N[id].kind;
      if (dir === 'in' && N[id].ui) groups.used_by.push([id, rel]);
      else if (k in groups && k !== 'other') groups[k].push([id, rel, dir]);
      else if (k !== 'qc_report' && k !== 'parameter') groups.other.push([id, rel, dir]);
    };
    for (const e of n.edges) add(e.to, e.rel, 'out');
    for (const b of n.backlinks || []) add(b.from, b.rel, 'in');
    const li = (arr) => arr.length ? `<ul class="rel">${arr.map(([id, rel, dir]) => `<li>${idLink(id, true)} <span class="rl">${esc(dir === 'in' ? '← ' + (REL_LABEL[rel] || rel) : REL_LABEL[rel] || rel)}</span></li>`).join('')}</ul>` : '';
    const issues = groups.issue.sort((a, b) => (N[b[0]].open ? 1 : 0) - (N[a[0]].open ? 1 : 0));
    let body = '';
    if (groups.decision.length) body += `<h5>Decisions</h5>${li(groups.decision)}`;
    if (groups.assumption.length) body += `<h5>Assumptions</h5>${li(groups.assumption)}`;
    if (issues.length) body += `<h5>Issues <span class="muted small">(open issues in red)</span></h5>${li(issues)}`;
    if (groups.other.length) body += `<h5>Other links</h5>${li(groups.other)}`;
    if (groups.used_by.length) body += `<h5>Shown in the dashboard as</h5>${li(groups.used_by)}`;
    return section('Related decisions, assumptions and issues', body);
  }

  function secRegistry(n) {
    let body = '';
    if (n.kind === 'issue' && n.history) {
      body += `<table class="kv hist"><tr><th>Date</th><th>Entry</th><th>Status</th></tr>${n.history.map((h) => `<tr><td>${esc(h.date)}</td><td>${linkIds(h.text)}${h.affects ? `<div class="small muted">affects: ${esc(h.affects)}</div>` : ''}${h.needs_user_approval ? `<div class="small muted">needs user approval: ${esc(h.needs_user_approval)}</div>` : ''}</td><td>${esc(h.status)}</td></tr>`).join('')}</table>`;
      body += `<p class="small muted">Open/closed is derived from the last non-empty Status cell; an update row starting with RESOLVED, Closed or Superseded closes the issue.</p>`;
    } else if (n.fields && Object.keys(n.fields).length && !n.ui && n.kind !== 'reward') {
      body += kvTable(Object.entries(n.fields).filter(([, v]) => v !== '' && v != null));
    }
    if (n.source_ref) {
      body += `<p class="small">Registry row: ${docLink(n.source_ref.file)} line ${esc(n.source_ref.line)}</p>`;
    }
    if (n.parse_warnings && n.parse_warnings.length) {
      body += `<div class="caveat">This registry row did not parse cleanly: ${n.parse_warnings.map(esc).join('; ')}. Raw line:</div><pre class="raw">${esc(n.source_ref ? n.source_ref.raw : '')}</pre>`;
    }
    return section(n.kind === 'issue' ? 'Issue history (verbatim)' : 'Registry entry (verbatim)', body);
  }

  function secDocs(n) {
    const docs = [...new Set(n.docs || [])];
    if (!docs.length) return '';
    return section('Reports and files', `<ul class="docs">${docs.map((d) => `<li>${docLink(d)}</li>`).join('')}</ul>`);
  }

  function renderCard(id) {
    const n = N[id];
    if (!n) return `<div class="ch"><h3>Not found: ${esc(id)}</h3><p>No node with this ID exists in the bundle.</p></div>`;
    const C = window.SCLcharts;
    const figs = C ? C.cardSection(n) : '';
    return [secHead(n), secNumbers(n), figs, secLineage(n), secMethod(n), secParameters(n), secQC(n), secRelated(n), secRegistry(n), secDocs(n)].join('');
  }

  // ------------------------------------------------------------------ drawer and deep links
  function currentNode() {
    const m = location.hash.match(/node=([^&]+)/);
    return m ? decodeURIComponent(m[1]) : null;
  }
  function onHash() {
    const id = currentNode();
    const dr = $('#drawer');
    if (!id) { dr.classList.remove('on'); return; }
    $('#card').innerHTML = renderCard(id);
    $('#card').scrollTop = 0;
    dr.classList.add('on');
    if (window.SCLcharts && N[id]) window.SCLcharts.afterCard(N[id], $('#card'));
    document.title = `${id} — SuisseCL audit`;
  }
  window.SCLopen = (id) => { location.hash = 'node=' + encodeURIComponent(id); };

  // ------------------------------------------------------------------ search
  const INDEX = Object.values(N).map((n) => ({id: n.id, kind: n.kind, title: n.title, ui: !!n.ui, text: (n.id + ' ' + n.title + ' ' + (n.summary || '')).toLowerCase()}));
  function search(q) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    const exact = INDEX.filter((x) => x.id.toLowerCase() === q);
    const pref = INDEX.filter((x) => x.id.toLowerCase().startsWith(q) && !exact.includes(x));
    const words = q.split(/\s+/);
    const rest = INDEX.filter((x) => !exact.includes(x) && !pref.includes(x) && words.every((w) => x.text.includes(w)));
    return exact.concat(pref.sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true})), rest).slice(0, 30);
  }
  function setupSearch() {
    const inp = $('#q'), box = $('#qres');
    let sel = 0, res = [];
    const draw = () => {
      box.innerHTML = res.map((r, i) => `<div class="qr${i === sel ? ' sel' : ''}" data-id="${esc(r.id)}"><code>${esc(r.ui ? r.title : r.id)}</code> <span class="lk">${esc(KIND_LABEL[r.kind] || r.kind)}</span> ${esc(short(r.title, 80))}</div>`).join('');
      box.style.display = res.length ? 'block' : 'none';
    };
    inp.addEventListener('input', () => { res = search(inp.value); sel = 0; draw(); });
    inp.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') { sel = Math.min(sel + 1, res.length - 1); draw(); e.preventDefault(); }
      else if (e.key === 'ArrowUp') { sel = Math.max(sel - 1, 0); draw(); e.preventDefault(); }
      else if (e.key === 'Enter' && res[sel]) { SCLopen(res[sel].id); box.style.display = 'none'; inp.blur(); }
      else if (e.key === 'Escape') { box.style.display = 'none'; }
    });
    box.addEventListener('mousedown', (e) => { const d = e.target.closest('.qr'); if (d) { SCLopen(d.dataset.id); box.style.display = 'none'; } });
    inp.addEventListener('blur', () => setTimeout(() => { box.style.display = 'none'; }, 150));
    document.addEventListener('keydown', (e) => { if (e.key === '/' && document.activeElement !== inp) { inp.focus(); e.preventDefault(); } });
  }

  // ------------------------------------------------------------------ registry browser (main page for now)
  const BROWSE_ORDER = ['series', 'card', 'kpi', 'panel', 'source', 'derived_dataset', 'transform', 'model', 'parameter', 'decision',
    'assumption', 'issue', 'controller', 'reward', 'experiment', 'validation_check', 'qc_report'];
  function setupBrowser() {
    const kinds = BROWSE_ORDER.filter((k) => meta.node_counts[k]);
    $('#bkind').innerHTML = kinds.map((k) => `<option value="${k}">${esc(KIND_LABEL[k] || k)} (${meta.node_counts[k]})</option>`).join('');
    const draw = () => {
      const k = $('#bkind').value, f = $('#bfilter').value.trim().toLowerCase(), onlyOpen = $('#bopen').checked;
      $('#bopenlbl').style.display = k === 'issue' ? '' : 'none';
      const rows = Object.values(N).filter((n) => n.kind === k && (!f || (n.id + ' ' + n.title + ' ' + (n.summary || '')).toLowerCase().includes(f)) && (!(onlyOpen && k === 'issue') || n.open));
      rows.sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true}));
      $('#blist').innerHTML = `<table class="tbl browse"><tr><th>ID</th><th>Title</th><th>Class / status</th></tr>${rows.map((n) => `<tr><td>${idLink(n.id, false, true)}</td><td>${esc(short(n.title, 140))}</td><td>${badge(n.classification)} ${n.kind === 'issue' ? `<span class="${n.open ? 'warnc' : 'muted'}">${n.open ? 'open' : 'closed'}</span>` : esc(short(n.status || '', 50))}${n.parse_warnings && n.parse_warnings.length ? ' <span class="warnc" title="registry row did not parse cleanly">⚠ row</span>' : ''}</td></tr>`).join('')}</table>`;
    };
    $('#bkind').addEventListener('change', draw); $('#bfilter').addEventListener('input', draw); $('#bopen').addEventListener('change', draw);
    draw();
  }

  // ------------------------------------------------------------------ header
  function snapshot() {
    if (!meta) { $('#snapshot').innerHTML = '<span class="badge bad">bundle missing: run swiss/dashboard/build_bundle.py</span>'; return; }
    const g = meta.git, m = meta.manifest;
    $('#snapshot').innerHTML = [
      `<span class="badge" title="bundle built ${esc(meta.built_utc)} from commit ${esc(g.commit_full)}">build <code>${esc(g.commit)}</code> · ${esc(meta.built_utc.replace('T', ' ').replace('Z', ' UTC'))}</span>`,
      g.dirty ? `<span class="badge bad" title="${esc(g.dirty_paths.join('\n'))}">⚠ built from uncommitted changes (${g.dirty_paths.length} paths)</span>` : '<span class="badge ok">clean git tree</span>',
      m.verified ? `<span class="badge ok" title="every file in data/canonical/MANIFEST.sha256 matched">MANIFEST ✓ ${m.files_listed} files</span>`
        : `<span class="badge bad" title="${esc(JSON.stringify(m.failures))}">⚠ MANIFEST does not verify (${m.failures.length})</span>`,
      meta.build_errors && meta.build_errors.length ? `<span class="badge bad">⚠ ${meta.build_errors.length} build errors</span>` : '',
    ].join(' ');
    $('#legend').innerHTML = Object.keys(COLOURS).map(badge).join(' ');
  }

  window.SCLui = {N, COLOURS, esc, badge, idLink, section, fmt, KIND_LABEL};
  snapshot();
  if (window.SCLcharts && prov) window.SCLcharts.init();
  if (prov) {
    setupSearch();
    setupBrowser();
    $('#dback').addEventListener('click', () => history.back());
    $('#dfwd').addEventListener('click', () => history.forward());
    $('#dclose').addEventListener('click', () => { history.pushState(null, '', location.pathname + location.search); onHash(); });
    $('#dlink').addEventListener('click', () => { const u = location.href; if (navigator.clipboard) navigator.clipboard.writeText(u); $('#dlink').textContent = 'link copied'; setTimeout(() => { $('#dlink').textContent = 'copy link'; }, 1200); });
    window.addEventListener('hashchange', onHash);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && document.activeElement !== $('#q')) $('#dclose').click(); });
    onHash();
  }
})();
