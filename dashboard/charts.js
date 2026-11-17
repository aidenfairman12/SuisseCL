/* Charts for the audit dashboard: input time series (synced subplots), trust overlay, "this hour" popover,
   and the figures shown inside cards. Data: bundle/series_inputs.js and bundle/figures.js only.
   Loaded before app.js; uses the helpers app.js exposes as window.SCLui. Plotly is vendored (dashboard/vendor/). */
(function () {
  'use strict';
  const B = window.SCL || {};
  const SI = B.series_inputs, FD = B.figures || {};
  const U = () => window.SCLui;
  const NEUTRAL = ['#2d3748', '#718096', '#a0aec0', '#4a5568'];
  const FLAG_COLOURS = {neighbour_intensity_fallback_flag: '#dd6b20', gap_interpolated_flag: '#d53f8c', weather_missing: '#805ad5',
    beam_negative: '#e53e3e', gap_filled_flag: '#c53030'};
  const CFG = {displaylogo: false, responsive: true, modeBarButtonsToRemove: ['lasso2d', 'select2d']};
  const RS = B.results;
  let X = null, overlay = false, building = 'SFH-low', controller = 'ALG-003_basic_rbc', drillState = null;
  const REF = 'ALG-001_zero_action';
  const ROLE_IDX = () => Object.keys(SI.buildings).reduce((o, r, i) => (o[r] = i + 1, o), {});
  function traceOf(name) {
    if (!RS || !RS.traces[name]) return null;
    const t = RS.traces[name], src = t.same_as || name;
    const T = (window.SCL || {})['trace_' + src];
    return T ? T.arrays : null;
  }
  function loadTrace(name, cb) {
    if (!RS || !RS.traces[name]) { cb(); return; }
    const src = RS.traces[name].same_as || name;
    if ((window.SCL || {})['trace_' + src]) { cb(); return; }
    const sc = document.createElement('script');
    sc.src = `bundle/trace_${src}.js`;
    sc.onload = cb; sc.onerror = cb;
    document.head.appendChild(sc);
  }
  function weights() {   // R-001 default weights, read from the reward documentation table (provenance R-001.fields.terms)
    const r = U().N['R-001'], w = {};
    for (const t of (r && r.fields.terms) || []) w[t.Term] = parseFloat(t['Default weight']);
    return w;
  }

  function xs() {
    if (X) return X;
    const t0 = Date.parse(SI.start_utc);
    X = new Array(SI.n);
    for (let i = 0; i < SI.n; i++) X[i] = new Date(t0 + i * SI.step_s * 1000).toISOString().slice(0, 16).replace('T', ' ');
    return X;
  }
  function clsColour(cls, fallback) { return overlay ? (U().COLOURS[cls] || fallback) : fallback; }
  function idxWhere(a) { const o = []; for (let i = 0; i < a.length; i++) if (a[i]) o.push(i); return o; }
  function count(a) { let c = 0; for (const v of a) if (v) c++; return c; }
  function localLabel(i) {
    const d = new Date(Date.parse(SI.start_utc) + (i * SI.step_s + SI.utc_offset_h[i] * 3600) * 1000);
    return d.toISOString().slice(0, 16).replace('T', ' ') + ` (UTC+${SI.utc_offset_h[i]})`;
  }
  const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

  // ------------------------------------------------------------------ main time-series figure
  // rows: [panel title, ui key, y-axis title, trace builders]
  function buildingTraces(role, yaxis, opts) {
    const b = SI.buildings[role];
    const out = [];
    b.components.forEach((c, k) => {
      out.push({type: 'scatter', mode: 'lines', x: xs(), y: c.values, name: `${role}: ${c.label}`, stackgroup: (opts && opts.stack) || 'b', yaxis,
        line: {width: 0.6, color: clsColour(c.classification, NEUTRAL[k % NEUTRAL.length])}, hoverinfo: 'x+y+name',
        meta: {ui: b.ui, hour: true}});
    });
    return out;
  }
  function flagTrace(key, series, yaxis, label, ui) {
    const f = SI.flags[key] || {values: SI.buildings[building].gap_filled_flag};
    const idx = idxWhere(f.values);
    return {type: 'scattergl', mode: 'markers', x: idx.map((i) => xs()[i]), y: idx.map((i) => (series[i] == null ? null : series[i])),
      customdata: idx, name: `⚑ ${label} (${idx.length} h)`, yaxis, visible: overlay ? true : false,
      marker: {symbol: 'x', size: 7, color: FLAG_COLOURS[key] || '#c53030'}, meta: {ui, hour: true, flag: key}};
  }
  function runs(a) {   // consecutive flagged hours -> [start, end) index pairs
    const out = []; let s = -1;
    for (let i = 0; i <= a.length; i++) { if (i < a.length && a[i]) { if (s < 0) s = i; } else if (s >= 0) { out.push([s, i]); s = -1; } }
    return out;
  }
  function shade(a, yref, colour) {
    return runs(a).map(([s, e]) => ({type: 'rect', xref: 'x', yref: `${yref} domain`, x0: xs()[s], x1: xs()[Math.min(e, SI.n - 1)], y0: 0, y1: 1,
      fillcolor: colour, opacity: 0.18, line: {width: 0}, layer: 'below'}));
  }

  function mainFigure() {
    const S = SI.series, F = SI.flags;
    const traces = [], shapes = [], ann = [];
    const panels = [
      {title: 'Grid carbon intensity — MODELED (gCO2eq/kWh)', ui: 'series:carbon_intensity'},
      {title: 'Electricity price — EKZ tariff, excl. VAT (Rp/kWh)', ui: 'series:price'},
      {title: 'Outdoor temperature — Zurich/Kloten (°C)', ui: 'series:outdoor_temperature'},
      {title: 'Solar irradiance — Zurich/Kloten (W/m²)', ui: 'series:ghi'},
      {title: `Building electricity — ${building} (kWh/h)`, ui: 'series:building_electricity'},
      {title: `District net electricity — ${controller} vs ${REF} (kWh/h, simulated)`, ui: 'kpi:district_import_kwh'},
      {title: `Tank state of charge — ${building}, ${controller} (0–1)`, ui: 'card:tanks'},
      {title: `Reward R-001 terms — ${controller} (−w·term/scale per step)`, ui: 'card:reward'},
    ];
    const n = panels.length, gap = 0.035, h = (1 - gap * (n - 1)) / n;
    const layout = {height: 1550, margin: {l: 60, r: 20, t: 20, b: 40}, hovermode: 'x', showlegend: true,
      legend: {orientation: 'h', y: -0.04, font: {size: 11}}, xaxis: {type: 'date', anchor: `y${n}`, showspikes: true, spikemode: 'across', spikethickness: 1}};
    panels.forEach((p, k) => {
      const ax = k === 0 ? 'yaxis' : `yaxis${k + 1}`;
      const top = 1 - k * (h + gap);
      layout[ax] = {domain: [top - h, top], zeroline: false, fixedrange: false};
      ann.push({text: `<b>${p.title}</b> ⓘ`, x: 0, xref: 'paper', y: top, yref: 'paper', xanchor: 'left', yanchor: 'bottom', showarrow: false,
        font: {size: 12, color: '#2b6cb0'}, captureevents: true, meta: {ui: p.ui}});
    });
    const y = (k) => (k === 0 ? 'y' : `y${k + 1}`);
    const line = (key, k, colourIdx, extra) => Object.assign({type: 'scattergl', mode: 'lines', x: xs(), y: S[key].values, name: S[key].label, yaxis: y(k),
      line: {width: 1, color: clsColour(S[key].classification, NEUTRAL[colourIdx])}, meta: {ui: S[key].ui, hour: true}}, extra || {});
    traces.push(line('carbon', 0, 0));
    traces.push(line('carbon_domestic', 0, 2, {line: {width: 1, dash: 'dot', color: clsColour('modeled', NEUTRAL[2])}}));
    traces.push(flagTrace('neighbour_intensity_fallback_flag', S.carbon.values, y(0), 'carbon neighbour fallback', 'series:carbon_intensity'));
    // interpolated hours are NaN in the canonical series: mark them at the CityLearn-file value is not possible here, so on the domestic line
    traces.push(flagTrace('gap_interpolated_flag', S.carbon_domestic.values, y(0), 'carbon interpolated (missing in canonical)', 'series:carbon_intensity'));
    traces.push(line('price', 1, 0, {line: {width: 1, shape: 'hv', color: clsColour('measured', NEUTRAL[0])}}));
    traces.push(line('temp_c', 2, 0));
    traces.push(line('ghi', 3, 0));
    traces.push(line('diffuse', 3, 1));
    traces.push(line('beam', 3, 2));
    traces.push(flagTrace('weather_missing', S.ghi.values, y(3), 'weather missing', 'series:diffuse'));
    traces.push(flagTrace('beam_negative', S.beam.values, y(3), 'beam < 0', 'series:beam'));
    buildingTraces(building, y(4)).forEach((t) => traces.push(t));
    const gapF = SI.buildings[building].gap_filled_flag;
    const tot = SI.n ? xs().map((_, i) => SI.buildings[building].components.reduce((a, c) => a + (c.values[i] || 0), 0)) : [];
    traces.push(Object.assign(flagTrace('gap_filled_flag', tot, y(4), `${building} gap-filled (SYNTHETIC)`, 'series:building_electricity'),
      {x: idxWhere(gapF).map((i) => xs()[i]), y: idxWhere(gapF).map((i) => tot[i]), customdata: idxWhere(gapF), name: `⚑ ${building} gap-filled, synthetic (${count(gapF)} h)`}));
    if (overlay) {
      shapes.push(...shade(F.neighbour_intensity_fallback_flag.values, 'y', FLAG_COLOURS.neighbour_intensity_fallback_flag));
      shapes.push(...shade(F.gap_interpolated_flag.values, 'y', FLAG_COLOURS.gap_interpolated_flag));
      shapes.push(...shade(F.weather_missing.values, 'y4', FLAG_COLOURS.weather_missing));
      shapes.push(...shade(F.beam_negative.values, 'y4', FLAG_COLOURS.beam_negative));
      shapes.push(...shade(gapF, 'y5', FLAG_COLOURS.gap_filled_flag));
    }
    const T = traceOf(controller), T0 = traceOf(REF), bi = ROLE_IDX()[building];
    if (T && T0) {
      const tx = xs().slice(0, T.district_net_kwh.length);
      traces.push({type: 'scattergl', mode: 'lines', x: tx, y: T0.district_net_kwh, name: `${REF} district net`, yaxis: y(5), line: {width: 1, color: '#a0aec0'}, meta: {ui: 'ALG-001', hour: true}});
      traces.push({type: 'scattergl', mode: 'lines', x: tx, y: T.district_net_kwh, name: `${controller} district net`, yaxis: y(5), line: {width: 1, color: '#2d3748'}, meta: {ui: controller.split('_')[0], hour: true}});
      traces.push({type: 'scattergl', mode: 'lines', x: tx, y: T[`b${bi}_heating_storage_soc`], name: `${building} heating tank SOC`, yaxis: y(6), line: {width: 1, color: overlay ? U().COLOURS.synthetic : '#2b6cb0'}, meta: {ui: 'card:tanks', hour: true}});
      traces.push({type: 'scattergl', mode: 'lines', x: tx, y: T[`b${bi}_dhw_storage_soc`], name: `${building} DHW tank SOC`, yaxis: y(6), line: {width: 1, color: overlay ? '#feb2b2' : '#dd6b20'}, meta: {ui: 'card:tanks', hour: true}});
      const w = weights(), sc = RS.reward_scales, col = {cost: '#2b6cb0', peak: '#c53030', ramp: '#dd6b20', carbon: '#b7791f'};
      for (const k of ['cost', 'peak', 'ramp', 'carbon']) {
        if (!w[k]) continue;
        traces.push({type: 'scattergl', mode: 'lines', x: tx, y: T['term_' + k].map((v) => (v == null ? null : -w[k] * v / sc[k])), name: `reward term ${k} (weight ${w[k]})`, yaxis: y(7), line: {width: 1, color: col[k]}, meta: {ui: 'card:reward', hour: true}});
      }
    } else {
      [5, 6, 7].forEach((k) => ann.push({text: RS ? 'loading run trace…' : 'no run traces in the bundle (run run_baselines.py --traces, then build_bundle.py)', xref: 'paper', yref: `${y(k)} domain`, x: 0.5, y: 0.5, showarrow: false, font: {color: '#a0aec0'}}));
    }
    if (drillState) {
      for (const i of drillState.hours) shapes.push({type: 'rect', xref: 'x', yref: 'paper', x0: xs()[i], x1: xs()[Math.min(i + 1, SI.n - 1)], y0: 0, y1: 1, fillcolor: '#d69e2e', opacity: 0.35, line: {width: 1, color: '#d69e2e'}});
      ann.push({text: `<b>drill-down:</b> ${drillState.label} (${drillState.hours.length} h highlighted)`, xref: 'paper', yref: 'paper', x: 1, y: 1.005, xanchor: 'right', yanchor: 'bottom', showarrow: false, font: {size: 11, color: '#975a16'}});
    }
    layout.annotations = ann; layout.shapes = shapes;
    return {traces, layout};
  }

  function drawMain() {
    const el = document.getElementById('tsplot');
    if (!el || !SI || !window.Plotly) return;
    const {traces, layout} = mainFigure();
    const keep = el.layout && el.layout.xaxis && el.layout.xaxis.range && !el.layout.xaxis.autorange ? el.layout.xaxis.range : null;
    if (keep) { layout.xaxis.range = keep; layout.xaxis.autorange = false; }
    Plotly.react(el, traces, layout, CFG);
    if (!el._scl) {
      el._scl = true;
      el.on('plotly_legendclick', (ev) => { const m = ev.data[ev.curveNumber].meta; if (m && m.ui) SCLopen(m.ui); return false; });
      el.on('plotly_legenddoubleclick', () => false);
      el.on('plotly_clickannotation', (ev) => { const m = ev.annotation.meta; if (m && m.ui) SCLopen(m.ui); });
      el.on('plotly_click', (ev) => {
        const p = ev.points[0];
        if (!p) return;
        const i = p.customdata != null && p.data.meta && p.data.meta.flag ? p.customdata : p.pointIndex;
        hourPopover(i, ev.event, p.data.meta && p.data.meta.ui);
      });
    }
    legendCounts();
  }

  function legendCounts() {
    const el = document.getElementById('trustlegend');
    if (!el) return;
    if (!overlay) { el.innerHTML = '<span class="muted small">Trust overlay off: series in neutral colours, flagged hours hidden.</span>'; return; }
    const F = SI.flags, u = U();
    const items = Object.entries(F).map(([k, f]) => `<span class="flagkey"><i style="background:${FLAG_COLOURS[k]}"></i>${u.esc(f.label)}: <b>${count(f.values)}</b> h</span>`);
    for (const [role, b] of Object.entries(SI.buildings)) { const c = count(b.gap_filled_flag); if (c) items.push(`<span class="flagkey"><i style="background:${FLAG_COLOURS.gap_filled_flag}"></i>${role} gap-filled (synthetic): <b>${c}</b> h</span>`); }
    el.innerHTML = `<span class="small">Series coloured by classification ${Object.keys(u.COLOURS).map(u.badge).join(' ')} · flagged hours shaded and marked ⚑:</span> ${items.join(' ')}`;
  }

  // ------------------------------------------------------------------ "this hour" popover
  function hourPopover(i, ev, fromUi) {
    const u = U(), S = SI.series, F = SI.flags;
    const row = (label, v, unit, cls, ui, flagsTxt) => `<tr><td>${ui ? `<a href="#node=${encodeURIComponent(ui)}">${u.esc(label)}</a>` : u.esc(label)}</td><td class="num">${v == null ? '<span class="warnc">missing</span>' : u.esc(v)} ${u.esc(unit || '')}</td><td>${u.badge(cls)}</td><td class="small warnc">${flagsTxt || ''}</td></tr>`;
    const fl = (keys) => keys.filter((k) => F[k] && F[k].values[i]).map((k) => '⚑ ' + u.esc(F[k].label)).join('<br>');
    let h = `<div class="pophead"><b>${xs()[i]} UTC</b> · local ${localLabel(i)} · ${WD[SI.weekday[i]]} · step ${i} <button class="popx">✕</button></div><table class="kv pop">`;
    h += row(S.carbon.label, S.carbon.values[i], S.carbon.unit, 'modeled', S.carbon.ui, fl(['neighbour_intensity_fallback_flag', 'gap_interpolated_flag']));
    h += row(S.carbon_domestic.label, S.carbon_domestic.values[i], S.carbon_domestic.unit, 'modeled', S.carbon_domestic.ui);
    h += row(S.price.label, S.price.values[i], S.price.unit, 'measured', S.price.ui, SI.tier_high[i] ? 'high tariff' : 'low tariff');
    h += row(S.temp_c.label, S.temp_c.values[i], S.temp_c.unit, 'measured', S.temp_c.ui, fl(['weather_missing']));
    h += row(S.ghi.label, S.ghi.values[i], S.ghi.unit, 'measured', S.ghi.ui);
    h += row(S.diffuse.label, S.diffuse.values[i], S.diffuse.unit, 'measured', S.diffuse.ui, fl(['weather_missing']));
    h += row(S.beam.label, S.beam.values[i], S.beam.unit, 'derived', S.beam.ui, fl(['beam_negative']));
    for (const [role, b] of Object.entries(SI.buildings)) {
      const g = b.gap_filled_flag[i] ? '⚑ gap-filled: SYNTHETIC' : '';
      for (const c of b.components) h += row(`${role} ${c.label}`, c.values[i], 'kWh', b.gap_filled_flag[i] ? 'synthetic' : c.classification, b.ui, g);
    }
    const T = traceOf(controller);
    if (T && i < T.district_net_kwh.length) {
      h += `<tr><th colspan="4">Simulation, ${u.esc(controller)} (step ${i})</th></tr>`;
      h += row('district net electricity', T.district_net_kwh[i], 'kWh', null, 'kpi:district_import_kwh');
      h += row('reward R-001', T.reward[i], '', null, 'card:reward');
      for (const k of ['cost', 'peak', 'ramp', 'carbon']) h += row(`term ${k} (unscaled)`, T['term_' + k][i], '', null, 'card:reward');
      for (const [role, bi] of Object.entries(ROLE_IDX())) {
        const a = [T[`b${bi}_action_heating_storage`], T[`b${bi}_action_dhw_storage`]].map((x) => (x ? x[i] : null));
        h += row(`${role} net / SOC heat / SOC DHW / actions`, `${T[`b${bi}_net_kwh`][i]} kWh · ${T[`b${bi}_heating_storage_soc`][i]} · ${T[`b${bi}_dhw_storage_soc`][i]} · ${a.join(' / ')}`, '', 'synthetic', 'card:tanks');
      }
    }
    h += '</table><p class="small muted">Inputs from the canonical files listed on each card; simulation values from the run trace (classification of tank values: synthetic, D-017a). Clicking a name opens its card.</p>';
    const pop = document.getElementById('hourpop');
    pop.innerHTML = h;
    pop.style.display = 'block';
    const W = window.innerWidth, H = window.innerHeight;
    pop.style.left = Math.max(8, Math.min((ev ? ev.clientX : 100) + 12, W - 520)) + 'px';
    pop.style.top = Math.max(8, Math.min((ev ? ev.clientY : 100) - 40, H - pop.offsetHeight - 8)) + 'px';
    pop.querySelector('.popx').onclick = () => { pop.style.display = 'none'; };
  }

  // ------------------------------------------------------------------ card figures
  const FIGS = {
    ts_temp: {title: 'Hourly outdoor temperature 2023', draw: (el) => line1(el, [['temp_c', 0]], '°C')},
    ts_irradiance: {title: 'Hourly irradiance 2023 (beam = global − diffuse)', draw: (el) => line1(el, [['ghi', 0], ['diffuse', 1], ['beam', 2]], 'W/m²')},
    ghi_vs_diffuse: {title: 'Diffuse vs global irradiance (each point = one hour)', draw: ghiVsDiffuse},
    klo_vs_heapo: {title: 'KLO temperature vs HEAPO station 8jB (timestamp check, D-009)', draw: kloVsHeapo, table: true},
    price_heatmap: {title: 'Mean price by local hour and weekday (two tiers)', draw: priceHeatmap},
    carbon_cons_vs_dom: {title: 'Consumption-based vs domestic-generation carbon intensity, with flagged hours', draw: carbonConsDom},
    building_daily: {title: 'Daily electricity per building, stacked by component (gap-filled day marked)', draw: buildingDaily},
    selection_pools: {title: 'Candidate pools and the six picks (nearest to stratum median)', draw: selectionPools},
    cop_curves: {title: 'COP vs outdoor temperature per building (M-001, calibrated η and supply temperature)', draw: copCurves},
    spf_check: {title: 'Annual SPF: literature target vs implied by the derived heat', draw: spfCheck},
    hp_split_monthly: {title: 'Monthly HP electricity split: warm-day baseline (→ DHW demand, A-005) vs space heating', draw: hpSplit},
    hp_sizing: {title: 'Heat-pump nominal power vs peak electricity of the mode (TR-009 rule: 1.1 × peak)', draw: hpSizing},
    tank_sizes: {title: 'Tank capacities (kWh_th) in the main dataset and the sensitivity variants', draw: tankSizes},
    carbon_import_stack: {title: 'Daily Swiss generation and imports by neighbour (MWh), with daily mean carbon intensity', draw: carbonImportStack},
    epfl_monthly: {title: 'Method check: monthly mean intensity, this model vs EPFL (2016, 2017)', draw: epflMonthly},
    epfl_diurnal: {title: 'Method check: mean by hour of day, this model vs EPFL', draw: epflDiurnal},
    epfl_table: {title: 'Method check: agreement statistics (from carbon_epfl_comparison.json)', draw: epflTable, table: true},
    sensitivity_bars: {title: 'Change against the uncontrolled run of each variant', draw: (el) => sensBars(el)},
    reward_year: {title: 'R-001 contributions per day for the selected controller (from the run trace)', draw: rewardYear},
    action_map: {title: 'ALG-004 action map by local hour (from run_baselines.py::tariff_map)', draw: actionMap},
    env_interface: {title: 'CityLearn interface configured in schema.json', draw: envInterface, table: true},
    backtest: {title: 'Gap-fill backtest: method A (mean of neighbouring days, used) vs B (same weekday ±7 days)', draw: backtest},
  };
  const QCR = (id) => (U().N[id] || {}).results || {};
  const ROLE_COL = {'SFH-low': '#2b6cb0', 'SFH-mid': '#3182ce', 'SFH-high': '#90cdf4', 'MFH-small': '#2f855a', 'MFH-medium': '#48bb78', 'MFH-large': '#9ae6b4'};
  function copCurves(el) {
    const c = FD.cop_curves, tr = [];
    for (const [role, b] of Object.entries(c.buildings)) {
      tr.push({type: 'scatter', mode: 'lines', x: c.t_out_c, y: b.cop_sh, name: `${role} space heating (η ${b.eta_sh.toFixed(3)}, T_sup ${b.T_sup_sh_c} °C)`, line: {color: ROLE_COL[role], width: 2}});
      tr.push({type: 'scatter', mode: 'lines', x: c.t_out_c, y: b.cop_dhw, name: `${role} DHW (η ${b.eta_dhw.toFixed(3)}, ${b.T_sup_dhw_c} °C)`, line: {color: ROLE_COL[role], width: 1, dash: 'dot'}, visible: 'legendonly'});
    }
    small(el, tr, {height: 380, xaxis: {title: 'outdoor temperature (°C), range of the 2023 KLO series'}, yaxis: {title: 'COP', range: [0, 21]},
      legend: {font: {size: 9}, orientation: 'v', x: 1.02, y: 1}, margin: {l: 45, r: 10, t: 10, b: 55}});
    const cap = Object.entries(c.buildings).map(([r, b]) => `${r}: ${b.hours_cop_sh_capped_at_20} h`).join(' · ');
    el.insertAdjacentHTML('afterend', `<div class="small">Hours in 2023 where the space-heating COP hits the cap of 20 (CityLearn form; T_out close to T_sup): ${U().esc(cap)}. DHW curves: click their legend entries.</div>`);
  }
  function spfCheck(el) {
    const q = QCR('QC:qc_thermal_2023'), roles = Object.keys(FD.cop_curves.buildings);
    const tgt = roles.map((r) => q[r].spf_target), sh = roles.map((r) => q[r].implied_spf_sh), comb = roles.map((r) => q[r].implied_spf_combined);
    small(el, [{type: 'bar', x: roles, y: tgt, name: 'target SPF (literature, D-014d)', marker: {color: '#a0aec0'}},
      {type: 'bar', x: roles, y: sh, name: 'implied SPF space heating', marker: {color: '#2b6cb0'}},
      {type: 'bar', x: roles, y: comb, name: 'implied SPF combined (SH + DHW)', marker: {color: '#2f855a'}}],
    {barmode: 'group', yaxis: {title: 'SPF'}, height: 280});
  }
  function hpSplit(el) {
    const s = FD.hp_split_monthly, roles = Object.keys(s.buildings), tr = [];
    const layout = {height: 120 * roles.length, grid: {rows: roles.length, columns: 1, pattern: 'independent'}, barmode: 'stack', margin: {l: 50, r: 10, t: 10, b: 30}, annotations: [], legend: {orientation: 'h', y: -0.06, font: {size: 10}}};
    roles.forEach((r, k) => {
      const ax = k ? String(k + 1) : '';
      tr.push({type: 'bar', x: s.months, y: s.buildings[r].e_hp_baseline_kwh, name: 'baseline (modeled as DHW demand)', marker: {color: '#dd6b20'}, xaxis: 'x' + ax, yaxis: 'y' + ax, showlegend: k === 0, legendgroup: 'b'});
      tr.push({type: 'bar', x: s.months, y: s.buildings[r].e_hp_space_heating_kwh, name: 'space heating', marker: {color: '#2b6cb0'}, xaxis: 'x' + ax, yaxis: 'y' + ax, showlegend: k === 0, legendgroup: 's'});
      layout.annotations.push({text: `<b>${r}</b>`, xref: 'x' + ax + ' domain', yref: 'y' + ax + ' domain', x: 0.5, y: 1, showarrow: false, font: {size: 10}});
      layout['yaxis' + ax] = {title: {text: 'kWh', font: {size: 9}}};
    });
    Plotly.newPlot(el, tr, layout, {displaylogo: false, responsive: true});
  }
  function hpSizing(el) {
    const r = FD.hp_sizing.rows, x = r.map((q) => `${q.building} ${q.role}`);
    small(el, [
      {type: 'bar', x, y: r.map((q) => q.peak_measured_hp_kwh), name: 'peak measured HP electricity (kWh/h)', marker: {color: '#a0aec0'}},
      {type: 'bar', x, y: r.map((q) => q.peak_sh_elec_kwh), name: 'peak space-heating part', marker: {color: '#90cdf4'}},
      {type: 'bar', x, y: r.map((q) => q.nominal_sh_kw), name: 'nominal power, heating device (kW)', marker: {color: '#2b6cb0'}},
      {type: 'bar', x, y: r.map((q) => q.peak_baseline_elec_kwh), name: 'peak baseline part', marker: {color: '#fbd38d'}},
      {type: 'bar', x, y: r.map((q) => q.nominal_dhw_kw), name: 'nominal power, DHW device (kW)', marker: {color: '#dd6b20'}},
    ], {barmode: 'group', height: 320, yaxis: {title: 'kW (= kWh per hour)'}});
  }
  function tankSizes(el) {
    const V = FD.tanks.variants, names = Object.keys(V), tr = [];
    names.forEach((v, k) => {
      const rows = V[v];
      tr.push({type: 'bar', x: rows.map((q) => q.role), y: rows.map((q) => q.heating_tank_kwh_th), name: `${v}: heating tank`, marker: {color: ['#2b6cb0', '#90cdf4', '#1a365d', '#a0aec0', '#cbd5e0'][k]}, legendgroup: v});
      tr.push({type: 'bar', x: rows.map((q) => q.role), y: rows.map((q) => q.dhw_tank_kwh_th), name: `${v}: DHW tank`, marker: {color: ['#c53030', '#feb2b2', '#742a2a', '#e2a0a0', '#fed7d7'][k]}, legendgroup: v, xaxis: 'x2', yaxis: 'y2'});
    });
    Plotly.newPlot(el, tr, {height: 420, barmode: 'group', grid: {rows: 2, columns: 1, pattern: 'independent'}, margin: {l: 50, r: 10, t: 20, b: 30}, font: {size: 10},
      yaxis: {title: 'heating kWh_th'}, yaxis2: {title: 'DHW kWh_th'}, legend: {orientation: 'h', y: -0.15, font: {size: 9}}}, {displaylogo: false, responsive: true});
    const eff = names.map((v) => `${v}: efficiency ${V[v][0].tank_efficiency}, loss ${V[v][0].loss_coefficient}/h`).join(' · ');
    el.insertAdjacentHTML('afterend', `<div class="small">${U().esc(eff)} (schema.json of each dataset). A DHW tank of 0 means no DHW tank.</div>`);
  }
  function carbonImportStack(el) {
    const d = FD.carbon_daily, cols = [['domestic_generation_excl_pumped_mwh', 'domestic generation (excl. pumped storage)', '#718096'],
      ['import_france_mwh', 'import France', '#2b6cb0'], ['import_germany_mwh', 'import Germany', '#c53030'], ['import_austria_mwh', 'import Austria', '#dd6b20'], ['import_italy_mwh', 'import Italy', '#2f855a']];
    const tr = cols.map(([k, n, c]) => ({type: 'scatter', mode: 'lines', stackgroup: 's', x: d.days, y: d.mwh[k], name: n, line: {width: 0.5, color: c}}));
    tr.push({type: 'scatter', mode: 'lines', x: d.days, y: d.mean_ci_consumption, name: 'daily mean carbon intensity (g/kWh, right axis)', yaxis: 'y2', line: {color: '#b7791f', width: 1.5}});
    small(el, tr, {height: 340, yaxis: {title: 'MWh/day'}, yaxis2: {title: 'g/kWh', overlaying: 'y', side: 'right'}, margin: {l: 55, r: 45, t: 10, b: 40}});
  }
  function epflMonthly(el) {
    const R = QCR('QC:carbon_epfl_comparison'), tr = [];
    const lab = (y) => [`Dec ${y - 1} (1 h)`, ...['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].map((m) => `${m} ${y}`)];
    for (const [y, dash] of [['2016', 'solid'], ['2017', 'dot']]) {
      const m = R[y].monthly_means, L = lab(+y);
      tr.push({type: 'scatter', mode: 'lines+markers', x: L, y: m.mine, name: `this model ${y}`, line: {color: U().COLOURS.modeled, dash}});
      tr.push({type: 'scatter', mode: 'lines+markers', x: L, y: m.epfl, name: `EPFL ${y}`, line: {color: '#2d3748', dash}});
    }
    small(el, tr, {height: 300, yaxis: {title: 'gCO2eq/kWh'}, xaxis: {tickangle: -45, tickfont: {size: 8}}, margin: {l: 50, r: 10, t: 10, b: 70}});
    el.insertAdjacentHTML('afterend', '<div class="small">The first bucket of each year holds only the 23:00 UTC hour of 31 December of the previous year (UTC monthly resampling of a CET year in compare_epfl_carbon.py).</div>');
  }
  function epflDiurnal(el) {
    const R = QCR('QC:carbon_epfl_comparison'), tr = [];
    for (const [y, dash] of [['2016', 'solid'], ['2017', 'dot']]) {
      const m = R[y].diurnal_means, h = m.mine.map((_, i) => i);
      tr.push({type: 'scatter', mode: 'lines', x: h, y: m.mine, name: `this model ${y}`, line: {color: U().COLOURS.modeled, dash}});
      tr.push({type: 'scatter', mode: 'lines', x: h, y: m.epfl, name: `EPFL ${y}`, line: {color: '#2d3748', dash}});
    }
    small(el, tr, {height: 260, xaxis: {title: 'hour of day (index of compare_epfl_carbon.py: Europe/Zurich local hour)', dtick: 2}, yaxis: {title: 'gCO2eq/kWh'}});
  }
  function epflTable(el) {
    const R = QCR('QC:carbon_epfl_comparison'), ys = Object.keys(R).filter((k) => R[k] && R[k].hourly_consumption_vs_epfl);
    const f = (v, d) => (v == null ? 'n/a' : (+v).toFixed(d));
    const rows = [
      ['hourly Pearson r', (y) => f(R[y].hourly_consumption_vs_epfl.pearson, 3)],
      ['hourly Spearman r', (y) => f(R[y].hourly_consumption_vs_epfl.spearman, 3)],
      ['monthly-mean r', (y) => f(R[y].monthly_corr, 3)], ['diurnal-profile r', (y) => f(R[y].diurnal_corr, 3)],
      ['mean, this model (g/kWh)', (y) => f(R[y].hourly_consumption_vs_epfl.mean_mine, 1)], ['mean, EPFL (g/kWh)', (y) => f(R[y].hourly_consumption_vs_epfl.mean_epfl, 1)],
      ['ratio of means', (y) => f(R[y].hourly_consumption_vs_epfl.ratio_mean, 3)], ['regression slope (model per EPFL)', (y) => f(R[y].hourly_consumption_vs_epfl.slope_mine_per_epfl, 3)],
      ['domestic-only vs EPFL, hourly r', (y) => f(R[y].hourly_domestic_vs_epfl.pearson, 3)],
      ['coefficient of variation model / EPFL', (y) => `${f(R[y].coefficient_of_variation.mine, 2)} / ${f(R[y].coefficient_of_variation.epfl, 2)}`],
      ['missing hours (model) / neighbour-fallback hours', (y) => `${R[y].missing_mine_hours} / ${R[y].neighbour_fallback_hours}`],
    ];
    el.innerHTML = `<table class="kv"><tr><th>statistic</th>${ys.map((y) => `<th>${y}</th>`).join('')}</tr>${rows.map(([l, g]) => `<tr><td>${l}</td>${ys.map((y) => `<td class="num">${g(y)}</td>`).join('')}</tr>`).join('')}</table>`;
  }
  function envInterface(el) {
    const e = FD.env_interface, u = U(), li = (a) => a.map((x) => `<code>${u.esc(x)}</code>`).join(', ');
    el.innerHTML = `<table class="kv"><tr><th>active observations (${e.observations_active.length})</th><td>${li(e.observations_active)}</td></tr>
      <tr><th>shared in central agent</th><td>${li(e.shared_in_central_agent)}</td></tr><tr><th>inactive observations</th><td>${li(e.observations_inactive)}</td></tr>
      <tr><th>active actions</th><td>${li(e.actions_active)}</td></tr><tr><th>inactive actions</th><td>${li(e.actions_inactive)}</td></tr>
      <tr><th>central agent</th><td>${e.central_agent}</td></tr><tr><th>time step</th><td>${e.seconds_per_time_step} s, last step index ${e.simulation_end_time_step}</td></tr>
      <tr><th>building class</th><td>${li(e.building_classes)}</td></tr><tr><th>device classes</th><td>${li(e.device_classes)}</td></tr></table>`;
  }
  function backtest(el) {
    const R = QCR('QC:backtest_gap_fill'), keys = Object.keys(R);
    const lab = keys.map((k) => k.replace(/\|/g, ' · ').replace('kwh_', ''));
    Plotly.newPlot(el, [
      {type: 'bar', x: lab, y: keys.map((k) => R[k].hourly_MAE_kWh_A_neighbour_days), name: 'A: neighbouring days (used, D-011)', marker: {color: '#2b6cb0'}},
      {type: 'bar', x: lab, y: keys.map((k) => R[k].hourly_MAE_kWh_B_same_weekday), name: 'B: same weekday ±7 d', marker: {color: '#a0aec0'}},
      {type: 'bar', x: lab, y: keys.map((k) => R[k].daily_MAPE_A), name: 'daily MAPE A', marker: {color: '#2f855a'}, xaxis: 'x2', yaxis: 'y2'},
      {type: 'bar', x: lab, y: keys.map((k) => R[k].daily_MAPE_B), name: 'daily MAPE B', marker: {color: '#c6f6d5'}, xaxis: 'x2', yaxis: 'y2'},
    ], {height: 480, barmode: 'group', grid: {rows: 2, columns: 1, pattern: 'independent'}, font: {size: 10}, margin: {l: 55, r: 10, t: 10, b: 110},
      yaxis: {title: 'hourly MAE (kWh)'}, yaxis2: {title: 'daily MAPE (fraction)'}, xaxis: {showticklabels: false}, xaxis2: {tickangle: -40},
      legend: {orientation: 'h', y: 1.08}}, {displaylogo: false, responsive: true});
    el.insertAdjacentHTML('afterend', `<div class="small">n days: ${keys.map((k) => `${U().esc(k)} = ${R[k].n_days}`).join('; ')}. MAPE values are fractions as stored in the JSON.</div>`);
  }
  function caption(name) {
    const f = {
      ts_temp: 'data/canonical/weather_klo_2023_hourly.csv: temp_c', ts_irradiance: 'data/canonical/weather_klo_2023_hourly.csv: ghi_wm2, diffuse_wm2, beam_horizontal_wm2',
      ghi_vs_diffuse: 'data/canonical/weather_klo_2023_hourly.csv', klo_vs_heapo: (FD.klo_vs_heapo_8jb || {}).files,
      price_heatmap: 'data/canonical/tariff_ekz_standard_2023_hourly.csv: total_rp_kwh; local time Europe/Zurich',
      carbon_cons_vs_dom: 'data/canonical/carbon_ch_2023_hourly.csv', building_daily: 'data/canonical/hourly/<role>_2023_hourly.csv (daily sum only where all 24 hours exist)',
      selection_pools: (FD.building_selection || {}).files,
      cop_curves: 'swiss/models/heat_pump.py::cop evaluated at build time with data/canonical/thermal/thermal_params.json',
      spf_check: 'docs/data/data_quality_reports/qc_thermal_2023.json', hp_split_monthly: 'data/canonical/thermal/<role>_2023_thermal_hourly.csv (local months)',
      hp_sizing: (FD.hp_sizing || {}).files, tank_sizes: 'swiss/datasets/<variant>/build_manifest.json and schema.json',
      carbon_import_stack: (FD.carbon_daily || {}).file, epfl_monthly: 'docs/data/data_quality_reports/carbon_epfl_comparison.json',
      epfl_diurnal: 'docs/data/data_quality_reports/carbon_epfl_comparison.json', epfl_table: 'docs/data/data_quality_reports/carbon_epfl_comparison.json',
      backtest: 'docs/data/data_quality_reports/backtest_gap_fill.json', env_interface: (FD.env_interface || {}).file,
      reward_year: 'swiss/experiments/results/traces/<controller>.csv.gz', sensitivity_bars: 'swiss/experiments/results/sensitivity_2023.csv', action_map: 'swiss/experiments/run_baselines.py::tariff_map (evaluated at build time)',
    }[name];
    return `Source: ${U().esc(Array.isArray(f) ? f.join(', ') : f)}`;
  }
  function small(el, traces, layout) {
    Plotly.newPlot(el, traces, Object.assign({height: 260, margin: {l: 50, r: 10, t: 10, b: 35}, legend: {orientation: 'h', y: -0.25, font: {size: 10}}, font: {size: 11}}, layout || {}), {displaylogo: false, responsive: true});
  }
  function line1(el, keys, unit) {
    small(el, keys.map(([k, c]) => ({type: 'scattergl', mode: 'lines', x: xs(), y: SI.series[k].values, name: SI.series[k].label,
      line: {width: 1, color: U().COLOURS[SI.series[k].classification] ? [U().COLOURS[SI.series[k].classification], '#90cdf4', '#68d391'][c] : NEUTRAL[c]}})), {yaxis: {title: unit}});
  }
  function ghiVsDiffuse(el) {
    const g = SI.series.ghi.values, d = SI.series.diffuse.values, neg = SI.flags.beam_negative.values;
    const ni = idxWhere(neg);
    small(el, [
      {type: 'scattergl', mode: 'markers', x: g, y: d, name: 'hours', marker: {size: 2, color: '#2b6cb0', opacity: 0.4}},
      {type: 'scatter', mode: 'lines', x: [0, 1150], y: [0, 1150], name: 'diffuse = global', line: {dash: 'dash', color: '#a0aec0'}},
      {type: 'scatter', mode: 'markers', x: ni.map((i) => g[i]), y: ni.map((i) => d[i]), name: `beam < 0 (${ni.length} h)`, marker: {size: 9, symbol: 'x', color: FLAG_COLOURS.beam_negative}},
    ], {xaxis: {title: 'global W/m²'}, yaxis: {title: 'diffuse W/m²'}, height: 300});
  }
  function kloVsHeapo(el) {
    const K = FD.klo_vs_heapo_8jb || {rows: [], note: ''}, r = K.rows;
    el.innerHTML = `<table class="kv"><tr><th>KLO hour t compared with HEAPO 8jB row</th><th>max |ΔT| (°C)</th><th>share identical</th><th>hours</th></tr>${r.map((x) => `<tr><td>t ${-x.shift_h > 0 ? '+ ' + -x.shift_h + ' h' : -x.shift_h < 0 ? '− ' + x.shift_h + ' h' : ''}</td><td class="num">${x.max_abs_diff_c.toFixed(2)}</td><td class="num">${(100 * x.share_identical).toFixed(1)} %</td><td class="num">${x.n}</td></tr>`).join('')}</table><p class="small">${U().esc(K.note)}</p>`;
  }
  function priceHeatmap(el) {
    const sum = Array.from({length: 24}, () => new Array(7).fill(0)), cnt = Array.from({length: 24}, () => new Array(7).fill(0));
    const p = SI.series.price.values;
    for (let i = 0; i < SI.n; i++) if (p[i] != null) { sum[SI.local_hour[i]][SI.weekday[i]] += p[i]; cnt[SI.local_hour[i]][SI.weekday[i]]++; }
    const z = sum.map((r, h) => r.map((v, d) => (cnt[h][d] ? v / cnt[h][d] : null)));
    small(el, [{type: 'heatmap', z, x: WD, y: Array.from({length: 24}, (_, h) => h), colorscale: [[0, '#ebf8ff'], [1, '#2b6cb0']],
      text: z.map((r) => r.map((v) => (v == null ? '' : v.toFixed(2)))), texttemplate: '%{text}', textfont: {size: 9}, colorbar: {title: 'Rp/kWh'},
      hovertemplate: '%{x} %{y}:00 local: %{z:.2f} Rp/kWh<extra></extra>'}],
    {height: 420, yaxis: {title: 'local hour', autorange: 'reversed', dtick: 1}, margin: {l: 50, r: 10, t: 10, b: 30}});
  }
  function carbonConsDom(el) {
    const S = SI.series, F = SI.flags;
    const fb = idxWhere(F.neighbour_intensity_fallback_flag.values), ip = idxWhere(F.gap_interpolated_flag.values);
    small(el, [
      {type: 'scattergl', mode: 'lines', x: xs(), y: S.carbon.values, name: S.carbon.label, line: {width: 1, color: U().COLOURS.modeled}},
      {type: 'scattergl', mode: 'lines', x: xs(), y: S.carbon_domestic.values, name: S.carbon_domestic.label, line: {width: 1, color: '#4a5568', dash: 'dot'}},
      {type: 'scattergl', mode: 'markers', x: fb.map((i) => xs()[i]), y: fb.map((i) => S.carbon.values[i]), name: `neighbour fallback (${fb.length} h)`, marker: {symbol: 'x', size: 6, color: FLAG_COLOURS.neighbour_intensity_fallback_flag}},
      {type: 'scattergl', mode: 'markers', x: ip.map((i) => xs()[i]), y: ip.map((i) => S.carbon_domestic.values[i]), name: `missing / interpolated (${ip.length} h, drawn on domestic line)`, marker: {symbol: 'diamond', size: 8, color: FLAG_COLOURS.gap_interpolated_flag}},
    ], {yaxis: {title: 'gCO2eq/kWh'}, height: 300});
  }
  function buildingDaily(el) {
    const roles = Object.keys(SI.buildings), traces = [], layout = {height: 150 * roles.length, margin: {l: 50, r: 10, t: 10, b: 30}, showlegend: true, legend: {orientation: 'h', y: -0.05, font: {size: 10}}, grid: {rows: roles.length, columns: 1, pattern: 'independent'}, annotations: []};
    const days = Math.floor(SI.n / 24), dx = [];
    for (let d = 0; d < days; d++) dx.push(xs()[d * 24].slice(0, 10));
    roles.forEach((role, r) => {
      const b = SI.buildings[role], ax = r === 0 ? '' : String(r + 1);
      b.components.forEach((c, k) => {
        const y = [];
        for (let d = 0; d < days; d++) { let s = 0, ok = true; for (let h = 0; h < 24; h++) { const v = c.values[d * 24 + h]; if (v == null) { ok = false; break; } s += v; } y.push(ok ? +s.toFixed(2) : null); }
        traces.push({type: 'bar', x: dx, y, name: c.label, legendgroup: c.key, showlegend: r === 0 || (r === 3 && k === 2), xaxis: 'x' + ax, yaxis: 'y' + ax,
          marker: {color: k === 0 ? '#2b6cb0' : c.classification === 'synthetic' ? U().COLOURS.synthetic : '#90cdf4'}});
      });
      const gd = new Set(idxWhere(b.gap_filled_flag).map((i) => xs()[i].slice(0, 10)));
      if (gd.size) layout.annotations.push({text: `gap-filled day (synthetic): ${[...gd].join(', ')}`, xref: 'x' + ax, yref: 'y' + ax + ' domain', x: [...gd][0], y: 1, showarrow: true, arrowhead: 2, ax: 0, ay: -12, font: {size: 10, color: '#c53030'}});
      layout.annotations.push({text: `<b>${role}</b>`, xref: 'x' + ax + ' domain', yref: 'y' + ax + ' domain', x: 0.01, y: 0.98, showarrow: false, xanchor: 'left', font: {size: 11}});
      layout['yaxis' + ax] = {title: {text: 'kWh/d', font: {size: 9}}};
    });
    layout.barmode = 'stack';
    Plotly.newPlot(el, traces, layout, {displaylogo: false, responsive: true});
  }
  function selectionPools(el) {
    const s = FD.building_selection;
    if (!s) { el.textContent = 'no data'; return; }
    const pickBy = (ids, vals, roles) => roles.map((p) => ({p, v: vals[ids.indexOf(p.id)]}));
    const sp = pickBy(s.sfh.ids, s.sfh.kwh_hp_2023, s.picks.filter((p) => p.role.startsWith('SFH')));
    const mp = pickBy(s.mfh.ids, s.mfh.kwh_per_unit_2023, s.picks.filter((p) => p.role.startsWith('MFH')));
    Plotly.newPlot(el, [
      {type: 'scatter', mode: 'markers', x: s.sfh.kwh_hp_2023, y: s.sfh.kwh_hp_2023.map(() => 'SFH pool'), name: `HEAPO SFH pool (${s.pool_sizes.sfh})`, marker: {size: 8, color: '#a0aec0'}},
      {type: 'scatter', mode: 'markers+text', x: sp.map((q) => q.v), y: sp.map(() => 'SFH pool'), text: sp.map((q) => q.p.role), textposition: sp.map((_, k) => (k % 2 ? 'bottom center' : 'top center')), name: 'SFH picks', marker: {size: 12, color: '#2b6cb0', symbol: 'diamond'}},
      {type: 'scatter', mode: 'markers', x: s.mfh.kwh_per_unit_2023, y: s.mfh.units.map((u) => `MFH pool (${u < 7 ? '4–6' : u <= 14 ? '7–14' : u >= 24 ? '≥24' : '15–23 (no stratum)'} units)`), name: `EKZ MFH pool (${s.pool_sizes.mfh})`, marker: {size: 8, color: '#a0aec0'}, xaxis: 'x2', yaxis: 'y2'},
      {type: 'scatter', mode: 'markers+text', x: mp.map((q) => q.v), y: mp.map((q) => `MFH pool (${q.p.units < 7 ? '4–6' : q.p.units <= 14 ? '7–14' : '≥24'} units)`), text: mp.map((q) => q.p.role), textposition: mp.map((_, k) => (k % 2 ? 'bottom center' : 'top center')), name: 'MFH picks', marker: {size: 12, color: '#2f855a', symbol: 'diamond'}, xaxis: 'x2', yaxis: 'y2'},
    ], {height: 380, margin: {l: 150, r: 10, t: 10, b: 40}, grid: {rows: 2, columns: 1, pattern: 'independent'}, font: {size: 11},
      xaxis: {title: {text: 'HP electricity 2023 (kWh)', font: {size: 10}}}, xaxis2: {title: {text: 'HP electricity 2023 per housing unit (kWh)', font: {size: 10}}},
      legend: {orientation: 'h', y: -0.3}}, {displaylogo: false, responsive: true});
  }

  // ------------------------------------------------------------------ CSV download of the series a card shows
  function csvFor(n) {
    const cols = [['timestamp_utc', xs().map((x) => x.replace(' ', 'T') + ':00Z')]];
    for (const [k, s] of Object.entries(SI.series)) if (s.ui === n.id) cols.push([`${s.column} (${s.file})`, s.values]);
    for (const [k, f] of Object.entries(SI.flags)) if (f.ui === n.id || (n.id === 'series:carbon_intensity' && f.ui === n.id)) cols.push([k, f.values]);
    if (n.id === 'series:building_electricity') for (const [role, b] of Object.entries(SI.buildings)) {
      for (const c of b.components) cols.push([`${role}.${c.column}`, c.values]);
      cols.push([`${role}.gap_filled_flag`, b.gap_filled_flag]);
    }
    if (cols.length === 1) return null;
    const lines = [cols.map((c) => `"${c[0]}"`).join(',')];
    for (let i = 0; i < SI.n; i++) lines.push(cols.map((c) => (c[1][i] == null ? '' : c[1][i])).join(','));
    return lines.join('\n');
  }

  // ------------------------------------------------------------------ KPIs (milestone 5)
  const DRILL = {   // which hours drive a KPI (display rule only; values come from the run trace)
    district_peak_kw: {type: 'max', of: 'net', label: 'peak hour of district net electricity'},
    kpi_all_time_peak_average: {type: 'max', of: 'net', label: 'peak hour of district net electricity'},
    mean_daily_peak_kw: {type: 'daily_max', of: 'net', label: 'daily peak hours'},
    kpi_daily_peak_average: {type: 'daily_max', of: 'net', label: 'daily peak hours'},
    cost_chf_excl_vat: {type: 'top', of: 'term_cost', label: 'top 1 % cost hours'},
    kpi_cost_total: {type: 'top', of: 'term_cost', label: 'top 1 % cost hours'},
    term_cost_sum: {type: 'top', of: 'term_cost', label: 'top 1 % cost hours'},
    district_import_kwh: {type: 'top', of: 'import', label: 'top 1 % import hours'},
    kpi_electricity_consumption_total: {type: 'top', of: 'import', label: 'top 1 % import hours'},
    ramping_sum_kw: {type: 'top', of: 'term_ramp', label: 'top 1 % ramps'},
    kpi_ramping_average: {type: 'top', of: 'term_ramp', label: 'top 1 % ramps'},
    term_ramp_sum: {type: 'top', of: 'term_ramp', label: 'top 1 % ramps'},
    term_peak_sum: {type: 'top', of: 'term_peak', label: 'top 1 % squared-peak hours'},
    term_carbon_sum: {type: 'top', of: 'term_carbon', label: 'top 1 % carbon-term hours'},
    kpi_carbon_emissions_total: {type: 'top', of: 'term_carbon', label: 'top 1 % carbon-term hours'},
    reward_return: {type: 'bottom', of: 'reward', label: 'top 1 % most negative reward steps'},
    high_tariff_import_share: {type: 'top', of: 'import', label: 'top 1 % import hours'},
  };
  function rowOf(name) { return RS.rows.find((r) => r.controller === name); }
  function drillHours(col) {
    const d = DRILL[col], T = traceOf(controller);
    if (!d || !T) return null;
    const n = T.district_net_kwh.length;
    let v;
    if (d.of === 'net') v = T.district_net_kwh;
    else if (d.of === 'import') { v = new Array(n).fill(0); for (const [, bi] of Object.entries(ROLE_IDX())) for (let i = 0; i < n; i++) v[i] += Math.max(T[`b${bi}_net_kwh`][i] || 0, 0); }
    else v = T[d.of];
    const idx = Array.from({length: n}, (_, i) => i);
    if (d.type === 'max') return {label: d.label, hours: [idx.reduce((a, b) => (v[b] > v[a] ? b : a), 0)]};
    if (d.type === 'daily_max') { const o = []; for (let s0 = 0; s0 < n; s0 += 24) { let b = s0; for (let i = s0; i < Math.min(s0 + 24, n); i++) if (v[i] > v[b]) b = i; o.push(b); } return {label: d.label, hours: o}; }
    const k = Math.max(1, Math.round(n * 0.01));
    idx.sort((a, b) => (d.type === 'bottom' ? v[a] - v[b] : v[b] - v[a]));
    return {label: d.label, hours: idx.slice(0, k).sort((a, b) => a - b)};
  }
  function fmtv(v, col) {
    if (v == null) return 'n/a';
    if (col.startsWith('kpi_') || col.endsWith('_share')) return (+v).toFixed(4);
    return Math.abs(v) >= 1000 ? Math.round(v).toLocaleString('en-US').replace(/,/g, '\u202f') : (+v).toFixed(2);
  }
  function drawKpis() {
    const el = document.getElementById('kpistrip');
    if (!el || !RS) return;
    const u = U(), r = rowOf(controller), r0 = rowOf(REF);
    const tile = (col) => {
      const n = u.N['kpi:' + col] || {}, v = r[col], v0 = r0[col];
      const na = v == null;
      const d = !na && v0 ? (v - v0) / Math.abs(v0) * 100 : null;
      const lower = !(col === 'reward_return');
      const good = d == null || controller === REF ? '' : ((lower ? d < 0 : d > 0) ? 'better' : (d === 0 ? '' : 'worse'));
      return `<div class="kt${na ? ' na' : ''}" data-ui="kpi:${col}" title="${u.esc(n.summary || '')}"><div class="kl">${u.esc((n.title || col).replace(' (CityLearn KPI)', ''))}</div>
        <div class="kv2">${na ? 'n/a' : fmtv(v, col)} <span class="ku">${u.esc((n.fields || {}).unit || '')}</span></div>
        <div class="kd ${good}">${na ? 'not applicable (D-018)' : controller === REF ? 'reference' : d == null ? `ALG-001: ${fmtv(v0, col)} (no % change)` : `${d >= 0 ? '+' : ''}${d.toFixed(2)} % vs ALG-001`}</div></div>`;
    };
    const cols = RS.columns.filter((c) => c !== 'controller' && c !== 'steps');
    const own = cols.filter((c) => !c.startsWith('kpi_')), cl = cols.filter((c) => c.startsWith('kpi_') && r[c] != null), na = cols.filter((c) => c.startsWith('kpi_') && r[c] == null);
    const exps = (RS.experiment_of[controller] || []).map((e) => u.idLink(e)).join(', ') || '<span class="warnc">no matching experiment row</span>';
    el.innerHTML = `<div class="small">Controller ${u.idLink(controller.split('_')[0])} <code>${u.esc(controller)}</code> · experiment ${exps} · results ${u.esc(RS.files[0])} (git ${u.esc(RS.meta.git_head)}) · lower is better except reward return; colours compare with ALG-001 (zero action).</div>
      <h4 class="kg">Our own computations</h4><div class="kts">${own.map(tile).join('')}</div>
      <h4 class="kg">CityLearn KPIs — normalised to CityLearn's conventional counterfactual (1.0 = counterfactual)</h4><div class="kts">${cl.map(tile).join('')}</div>
      <details><summary class="small">${na.length} CityLearn comfort/resilience KPIs are not applicable (no thermal dynamics, D-018)</summary><div class="kts">${na.map(tile).join('')}</div></details>`;
    el.querySelectorAll('[data-ui]').forEach((e) => e.addEventListener('click', () => SCLopen(e.dataset.ui)));
  }
  function kpiCardSection(n) {
    if (!RS || n.kind !== 'kpi') return '';
    const u = U(), col = n.id.slice(4);
    if (!RS.columns.includes(col)) return '';
    const rows = RS.rows.map((r) => `<tr${r.controller === controller ? ' class="selrow"' : ''}><td>${u.idLink(r.controller.split('_')[0])} <code>${u.esc(r.controller)}</code></td><td class="num">${r[col] == null ? 'n/a' : u.esc(String(r[col]))}</td><td>${(RS.experiment_of[r.controller] || []).map((e) => u.idLink(e)).join(', ')}</td></tr>`).join('');
    const origin = (n.fields || {}).origin === 'own' ? 'Our own computation in run_baselines.py::rollout (code below).'
      : `CityLearn district KPI from <code>env.evaluate()</code>, normalised to CityLearn's conventional counterfactual (same buildings without storage control; 1.0 = counterfactual, lower is better; HANDOFF §4.1). Stored as column <code>${u.esc(col)}</code>.`;
    let chk = '';
    const tc = RS.trace_checks[controller];
    if (tc && tc[col]) chk = `<p class="small">Run-trace check (${u.esc(controller)}): sum of per-step trace = ${u.esc(String(tc[col].trace))}, results = ${u.esc(String(tc[col].results))}, relative difference ${tc[col].rel_diff.toExponential(1)}.</p>`;
    const dr = DRILL[col] ? `<button class="drill" data-col="${u.esc(col)}">Show the hours that drive it (${u.esc(DRILL[col].label)}) for ${u.esc(controller)}</button>` : '';
    return u.section('Values by controller', `<p class="small">${origin}</p><table class="kv"><tr><th>controller</th><th>value</th><th>experiment</th></tr>${rows}</table>
      <p class="small muted">Experiment matched by: ${u.esc(RS.experiment_rule)}.</p>${chk}${dr}`);
  }
  function rewardYear(el) {
    const T = traceOf(controller);
    if (!T) { el.textContent = 'run trace not loaded'; return; }
    const w = weights(), sc = RS.reward_scales, days = Math.floor(T.reward.length / 24), dx = [], tr = [];
    for (let d = 0; d < days; d++) dx.push(xs()[d * 24].slice(0, 10));
    for (const [k, c] of [['cost', '#2b6cb0'], ['peak', '#c53030'], ['ramp', '#dd6b20'], ['carbon', '#b7791f']]) {
      const y = []; for (let d = 0; d < days; d++) { let s0 = 0; for (let h = 0; h < 24; h++) s0 += -(w[k] || 0) * (T['term_' + k][d * 24 + h] || 0) / sc[k]; y.push(+s0.toFixed(4)); }
      tr.push({type: 'bar', x: dx, y, name: `${k} (weight ${w[k]})`, marker: {color: c}});
    }
    small(el, tr, {barmode: 'relative', height: 300, yaxis: {title: 'reward per day'}});
    el.insertAdjacentHTML('afterend', `<div class="small">Controller ${U().esc(controller)} (change it in the header). Weights from the R-001 table; scales from reward_scales.json.</div>`);
  }
  function actionMap(el) {
    const A = FD.action_maps || {}, tr = Object.entries(A).map(([k, m], i) => ({type: 'bar', x: m.local_hour, y: m.action, name: `${k} (r = ${m.rate})`, marker: {color: ['#90cdf4', '#2b6cb0', '#1a365d'][i % 3]}}));
    small(el, tr, {barmode: 'group', height: 280, xaxis: {title: 'local hour (CityLearn hour − 1)', dtick: 1}, yaxis: {title: 'action (+ charge, − discharge)'}});
  }
  function identicalNote(n) {
    if (!RS || n.kind !== 'controller') return '';
    const mine = RS.rows.filter((r) => r.controller.startsWith(n.id + '_'));
    const out = [];
    for (const r of mine) for (const o of RS.rows) {
      if (o.controller === r.controller || o.controller.startsWith(n.id)) continue;
      const same = RS.columns.every((c) => c === 'controller' || r[c] === o[c]);
      if (same) out.push(`<code>${U().esc(r.controller)}</code> gives results identical to <code>${U().esc(o.controller)}</code> in every column of baselines_2023.csv${RS.traces[r.controller] && RS.traces[r.controller].same_as === o.controller ? ' and an identical run trace' : ''}.`);
    }
    return out.length ? `<div class="caveat">${out.join('<br>')} Expected for this district (see the registry limitations).</div>` : '';
  }

  // ------------------------------------------------------------------ milestone 6: map, sensitivity, validation, issues
  let scenario = 'reference';
  function colourMap() {
    const u = U();
    document.querySelectorAll('#sysmap .mbox').forEach((g) => {
      const n = u.N[g.dataset.ui], r = g.querySelector('rect');
      const c = n && n.classification ? u.COLOURS[n.classification] : null;
      if (c) { r.style.stroke = c; r.style.fill = c + '22'; }
      const t = document.createElementNS('http://www.w3.org/2000/svg', 'title');
      t.textContent = n ? `${n.title}${n.classification ? ' — ' + n.classification : ''}: ${n.summary || ''}` : g.dataset.ui;
      g.appendChild(t);
    });
  }
  const SENS_COLS = [['cost_vs_zero_pct', 'cost (%)'], ['import_vs_zero_pct', 'import (%)'], ['peak_vs_zero_pct', 'peak (%)'], ['high_tariff_share_pts_vs_zero', 'high-tariff share (points)']];
  function sensBars(el) {
    const rows = RS.sensitivity.filter((r) => r.controller !== 'zero_action'), ctrls = [...new Set(rows.map((r) => r.controller))];
    const variants = [...new Set(RS.sensitivity.map((r) => r.variant))], tr = [], lay = {height: 520, grid: {rows: 2, columns: 2, pattern: 'independent'}, barmode: 'group', margin: {l: 50, r: 10, t: 30, b: 60}, annotations: [], font: {size: 11}, legend: {orientation: 'h', y: -0.12}};
    SENS_COLS.forEach(([col, lab], k) => {
      const ax = k ? String(k + 1) : '';
      ctrls.forEach((c, j) => tr.push({type: 'bar', x: variants, y: variants.map((v) => (rows.find((r) => r.variant === v && r.controller === c) || {})[col]), name: c, legendgroup: c, showlegend: k === 0, xaxis: 'x' + ax, yaxis: 'y' + ax, marker: {color: ['#2b6cb0', '#dd6b20', '#2f855a'][j % 3]},
        hovertemplate: `%{x} · ${c}: %{y:.2f}<extra>${lab}</extra>`}));
      lay.annotations.push({text: `<b>${lab} vs uncontrolled</b>`, xref: `x${ax} domain`, yref: `y${ax} domain`, x: 0.5, y: 1.12, showarrow: false});
    });
    Plotly.newPlot(el, tr, lay, {displaylogo: false, responsive: true});
  }
  function drawSens() {
    const el = document.getElementById('sensplot');
    if (!el || !RS) return;
    const V = (FD.sensitivity_variants || {}).datasets || {};
    el.innerHTML = '<div class="sp"></div><div class="small">Datasets: ' + Object.entries(V).map(([k, d]) => `${U().esc(k)} = <code>swiss/datasets/${U().esc(d)}</code>`).join(' · ') +
      `. Source: ${U().esc(RS.files[2])}; variant definitions in ${U().esc((FD.sensitivity_variants || {}).source || '')}. <a href="#node=panel:sensitivity">Open the sensitivity card</a>.</div>`;
    sensBars(el.querySelector('.sp'));
  }
  function drawValid() {
    const el = document.getElementById('validtable');
    if (!el) return;
    const u = U(), vs = Object.values(u.N).filter((n) => n.kind === 'validation_check').sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true}));
    el.innerHTML = `<table class="kv vt"><tr><th>ID</th><th>Check</th><th>Result</th><th>Status</th><th>numbers</th></tr>${vs.map((n) => `<tr><td>${u.idLink(n.id)}</td><td>${u.esc(n.fields.Check)}</td><td>${u.esc(n.fields.Result)}</td><td class="${n.passed ? 'vpass' : 'vwarn'}">${u.esc(n.status)}</td><td class="small">${n.results ? `<a href="#node=${n.id}">${u.esc(n.results_key)}</a>` : '<span class="muted">none in JSON</span>'}</td></tr>`).join('')}</table><p class="small muted">Source: docs/experiments/validation_reports/validation_phase_a.md (table) and validation_phase_a.json (numbers).</p>`;
  }
  function drawIssues() {
    const el = document.getElementById('issuelist');
    if (!el) return;
    const u = U(), iss = Object.values(u.N).filter((n) => n.kind === 'issue' && n.open).sort((a, b) => a.id.localeCompare(b.id, undefined, {numeric: true}));
    const used = (id) => (u.N[id].backlinks || []).filter((b) => u.N[b.from] && u.N[b.from].ui).map((b) => u.idLink(b.from)).join(', ');
    el.innerHTML = `<input id="issf" type="search" placeholder="filter open issues"> <span class="small muted">${iss.length} open of ${Object.values(u.N).filter((n) => n.kind === 'issue').length}; open = rule shown on each issue card</span>
      <table class="kv vt" id="isst"><tr><th>ID</th><th>Issue (first sentence)</th><th>Affects</th><th>Status</th><th>Shown on</th></tr>${iss.map((n) => `<tr data-t="${u.esc((n.id + ' ' + n.summary + ' ' + n.fields.Affects).toLowerCase())}"><td>${u.idLink(n.id)}</td><td>${u.esc(n.summary)}</td><td>${u.esc(n.fields.Affects)}</td><td>${u.esc(n.status)}</td><td class="small">${used(n.id)}</td></tr>`).join('')}</table>`;
    el.querySelector('#issf').addEventListener('input', (e) => { const q = e.target.value.toLowerCase(); el.querySelectorAll('#isst tr[data-t]').forEach((tr) => { tr.style.display = tr.dataset.t.includes(q) ? '' : 'none'; }); });
  }
  function drawScenarioKpis() {
    const el = document.getElementById('kpistrip');
    if (scenario === 'reference') { drawKpis(); return; }
    const u = U(), rows = RS.sensitivity.filter((r) => r.variant === scenario);
    const V = (FD.sensitivity_variants || {}).datasets || {};
    el.innerHTML = `<div class="scenbox">Scenario <b>${u.esc(scenario)}</b> (dataset <code>swiss/datasets/${u.esc(V[scenario] || '?')}</code>): only aggregates exist for sensitivity variants (no run traces, no CityLearn KPIs). Values from ${u.esc(RS.files[2])}.</div>
      <table class="kv"><tr><th>controller</th><th>import kWh</th><th>peak kW</th><th>cost CHF</th><th>high-tariff share</th>${SENS_COLS.map(([, l]) => `<th>${l} vs uncontrolled</th>`).join('')}</tr>
      ${rows.map((r) => `<tr><td>${u.esc(r.controller)}</td><td class="num">${fmtv(r.import_kwh, 'x')}</td><td class="num">${(+r.peak_kw).toFixed(2)}</td><td class="num">${fmtv(r.cost_chf, 'x')}</td><td class="num">${(+r.high_tariff_share).toFixed(4)}</td>${SENS_COLS.map(([c]) => `<td class="num">${(+r[c]).toFixed(2)}</td>`).join('')}</tr>`).join('')}</table>
      <p class="small"><a href="#node=panel:sensitivity">Sensitivity card</a> · the hour-by-hour panels below still show the reference dataset.</p>`;
  }

  window.SCLcharts = {
    init() {
      if (!SI || !window.Plotly) return;
      const sel = document.getElementById('bsel');
      if (sel) {
        sel.innerHTML = Object.keys(SI.buildings).map((r) => `<option>${r}</option>`).join('');
        sel.addEventListener('change', () => { building = sel.value; drawMain(); });
      }
      const tog = document.getElementById('trust');
      if (tog) tog.addEventListener('change', () => { overlay = tog.checked; drawMain(); });
      document.getElementById('tsreset').addEventListener('click', () => Plotly.relayout('tsplot', {'xaxis.autorange': true}));
      document.querySelectorAll('[data-ui]').forEach((e) => e.addEventListener('click', () => SCLopen(e.dataset.ui)));
      const cs = document.getElementById('ctrl');
      if (cs && RS) {
        cs.innerHTML = RS.rows.map((r) => `<option value="${r.controller}"${r.controller === controller ? ' selected' : ''}>${r.controller}</option>`).join('');
        cs.addEventListener('change', () => { controller = cs.value; drillState = null; drawKpis(); loadTrace(controller, drawMain); });
      }
      document.addEventListener('click', (e) => {
        const b = e.target.closest('.drill');
        if (!b) return;
        drillState = drillHours(b.dataset.col);
        drawMain();
        if (drillState && drillState.hours.length) {
          const h = drillState.hours, a = Math.max(0, h[0] - 72), z = Math.min(SI.n - 1, h[h.length - 1] + 72);
          if (h.length <= 3) Plotly.relayout('tsplot', {'xaxis.range': [xs()[a], xs()[z]]});
          document.getElementById('ts').scrollIntoView({behavior: 'smooth'});
        }
      });
      const clr = document.getElementById('drillclear');
      if (clr) clr.addEventListener('click', () => { drillState = null; drawMain(); });
      const sc = document.getElementById('scen');
      if (sc && RS) {
        const vs = [...new Set(RS.sensitivity.map((r) => r.variant))];
        sc.innerHTML = vs.map((v) => `<option value="${v}">${v === 'reference' ? 'main (reference)' : v}</option>`).join('');
        sc.addEventListener('change', () => { scenario = sc.value; document.getElementById('ctrl').disabled = scenario !== 'reference'; drawScenarioKpis(); });
      }
      colourMap();
      drawKpis();
      drawMain();
      drawSens(); drawValid(); drawIssues();
      loadTrace(REF, () => loadTrace(controller, drawMain));
    },
    cardSection(n) {
      const extra = kpiCardSection(n) + (identicalNote(n) ? U().section('Results check', identicalNote(n)) : '');
      return extra + this.figSection(n);
    },
    figSection(n) {
      const figs = (n.figures || []).filter((f) => FIGS[f]);
      const hasCsv = SI && Object.values(SI.series).some((s) => s.ui === n.id) || n.id === 'series:building_electricity';
      if (!figs.length && !hasCsv) return '';
      const u = U();
      const body = figs.map((f) => `<figure class="cfig"><figcaption><b>${u.esc(FIGS[f].title)}</b></figcaption><div class="cfigplot" data-fig="${f}"></div><div class="small muted">${caption(f)}</div></figure>`).join('')
        + (hasCsv ? '<button class="csvbtn">Download CSV of the series shown (all hours, with flags)</button>' : '');
      return u.section('Figures and data', body);
    },
    afterCard(n, root) {
      const pop = document.getElementById('hourpop');
      if (pop) pop.style.display = 'none';
      if (!window.Plotly) return;
      root.querySelectorAll('.cfigplot').forEach((el) => { try { FIGS[el.dataset.fig].draw(el); } catch (e) { el.textContent = 'figure failed: ' + e.message; } });
      const b = root.querySelector('.csvbtn');
      if (b) b.onclick = () => {
        const csv = csvFor(n);
        if (!csv) return;
        const a = document.createElement('a');
        a.href = URL.createObjectURL(new Blob([csv], {type: 'text/csv'}));
        a.download = n.id.replace(/[^a-z0-9_]+/gi, '_') + '.csv';
        a.click();
      };
    },
  };
})();
