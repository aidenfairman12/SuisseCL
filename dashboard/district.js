/* District illustration: the six simulated buildings with their heat pumps, tanks, meters, the grid cable, the input
   feeds and the controller, connected by animated lines driven by the hourly data of the selected controller.
   Every number drawn comes from the bundle (figures.district, series_inputs, run traces). Shapes are illustrative:
   building height scales with housing units, nothing else about the geometry is data. */
(function () {
  'use strict';
  const B = window.SCL || {};
  const FD = B.figures || {}, SI = B.series_inputs, RS = B.results;
  const NS = 'http://www.w3.org/2000/svg';
  const UI = {   // clickable parts -> ui_map keys (lint checks these exist)
    district: 'card:district', house: 'series:building_electricity', hp: 'card:cop_model', hpsize: 'card:hp_nominal_power',
    tank: 'card:tanks', meter: 'kpi:district_import_kwh', grid: 'card:environment', controller: 'card:controllers',
    weather: 'series:outdoor_temperature', tariff: 'series:price', carbon: 'series:carbon_intensity', selection: 'card:building_selection',
    reward: 'card:reward',
  };
  const C = {elec: '#f59f00', heat: '#e8590c', dhw: '#1098ad', ctrl: '#7048e8', feed: '#868e96', synth: '#e03131'};
  const W = 1280, H = 720, GROUND = 530, BUS_Y = 572, TH = 58;
  let hour = 0, playing = null, built = false;
  const els = {buildings: []};

  const U = () => window.SCLui;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const fmt = (v, d) => (v == null || isNaN(v) ? '–' : (+v).toFixed(d));
  const ctrlName = () => (document.getElementById('ctrl') || {}).value || 'ALG-003_basic_rbc';
  const trace = () => (window.SCLcharts && window.SCLcharts.traceOf ? window.SCLcharts.traceOf(ctrlName()) : null);

  function slotX(i) { return 160 + i * 185; }   // left edge of building i (0-based)
  function floorsOf(b) { return b.type === 'SFH' ? 1 : Math.max(3, Math.round(Math.sqrt(b.units) * 1.25)); }

  // ------------------------------------------------------------------ static drawing
  function defs() {
    return `<defs>
      <linearGradient id="dsky" x1="0" y1="0" x2="0" y2="1"><stop id="dsky0" offset="0" stop-color="#cfe8ff"/><stop id="dsky1" offset="1" stop-color="#f4f9ff"/></linearGradient>
      <linearGradient id="dgrass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b7dfa1"/><stop offset="1" stop-color="#8cc47a"/></linearGradient>
      <linearGradient id="dwallS" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fffaf0"/><stop offset="1" stop-color="#f3e7d3"/></linearGradient>
      <linearGradient id="dwallM" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f1f3f5"/><stop offset="1" stop-color="#dee2e6"/></linearGradient>
      <linearGradient id="dheat" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#d9480f"/><stop offset="1" stop-color="#ff922b"/></linearGradient>
      <linearGradient id="ddhw" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#0b7285"/><stop offset="1" stop-color="#3bc9db"/></linearGradient>
      <linearGradient id="dtankbody" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ced4da"/><stop offset=".45" stop-color="#f8f9fa"/><stop offset="1" stop-color="#adb5bd"/></linearGradient>
      <radialGradient id="dsun"><stop offset="0" stop-color="#fff3bf"/><stop offset=".6" stop-color="#ffd43b"/><stop offset="1" stop-color="#fab005" stop-opacity="0"/></radialGradient>
      <filter id="dshadow" x="-20%" y="-20%" width="140%" height="140%"><feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-opacity=".18"/></filter>
      <filter id="dglow"><feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
      <marker id="darr" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,1 L9,5 L0,9 z" fill="${C.ctrl}"/></marker>
      <pattern id="dsynth" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="#fff5f5"/><line x1="0" y1="0" x2="0" y2="6" stroke="#ffc9c9" stroke-width="3"/></pattern>
    </defs>`;
  }

  function sky() {
    let stars = '';
    for (let i = 0; i < 40; i++) {   // fixed pseudo-random star field (decorative)
      const x = (i * 263) % W, y = 12 + ((i * 97) % 300);
      stars += `<circle cx="${x}" cy="${y}" r="${(i % 3) * 0.5 + 0.6}" fill="#fff"/>`;
    }
    return `<rect width="${W}" height="${GROUND}" fill="url(#dsky)"/>
      <g id="dstars" opacity="0">${stars}</g>
      <circle id="dsunc" cx="900" cy="140" r="38" fill="url(#dsun)"/>
      <g id="dmoon" opacity="0"><circle cx="1000" cy="80" r="16" fill="#f1f3f5"/><circle cx="1007" cy="75" r="14" fill="#1c2b4a" id="dmoonshade"/></g>
      <g opacity=".55"><path d="M0,${GROUND} L120,400 L260,440 L420,380 L560,430 L720,370 L900,425 L1060,385 L1280,430 L1280,${GROUND} Z" fill="#a5c8a0"/></g>
      <rect y="${GROUND}" width="${W}" height="${H - GROUND}" fill="url(#dgrass)"/>
      <rect y="${BUS_Y - 16}" width="${W}" height="24" fill="#e9ecef"/><line x1="0" x2="${W}" y1="${BUS_Y - 16}" y2="${BUS_Y - 16}" stroke="#ced4da"/>
      <rect y="${BUS_Y + 8}" width="${W}" height="58" fill="#495057"/>
      <rect y="${BUS_Y + 66}" width="${W}" height="${H - BUS_Y - 66}" fill="#ced4da"/>
      <line x1="0" x2="${W}" y1="${BUS_Y + 37}" y2="${BUS_Y + 37}" stroke="#f8f9fa" stroke-width="2.5" stroke-dasharray="26 22"/>`;
  }

  function card(x, y, w, h, ui, icon, title, idText) {
    return `<g class="dclick" data-ui="${ui}" transform="translate(${x},${y})" filter="url(#dshadow)">
      <rect width="${w}" height="${h}" rx="12" fill="#fff" fill-opacity=".94" stroke="#dee2e6"/>
      <g transform="translate(14,${h / 2})">${icon}</g>
      <text x="52" y="22" class="dt1">${esc(title)}</text>
      <text x="52" y="38" class="dt2" id="${idText}">–</text>
      <text x="52" y="53" class="dt3" id="${idText}b"></text></g>`;
  }
  const ICON = {
    weather: '<g><circle r="9" fill="#fcc419"/><path d="M-2,4 a8,8 0 0 1 14,-2 a6,6 0 0 1 2,12 h-14 a6,6 0 0 1 -2,-10z" fill="#e9ecef" stroke="#adb5bd"/></g>',
    tariff: '<g><circle r="13" fill="#fff4e6" stroke="#f59f00" stroke-width="2"/><text y="5" text-anchor="middle" font-size="13" font-weight="700" fill="#e67700">Rp</text></g>',
    carbon: '<g><path d="M-10,8 C-14,-2 -4,-12 2,-8 C6,-14 16,-8 12,0 C18,4 12,12 6,10 Z" fill="#e9ecef" stroke="#b7791f" stroke-width="1.6"/><text x="1" y="4" text-anchor="middle" font-size="8" font-weight="700" fill="#b7791f">CO₂</text></g>',
    ctrl: '<g><rect x="-12" y="-12" width="24" height="24" rx="4" fill="#f3f0ff" stroke="#7048e8" stroke-width="2"/><rect x="-5" y="-5" width="10" height="10" fill="#7048e8"/><path d="M-12,-6h-4M-12,0h-4M-12,6h-4M12,-6h4M12,0h4M12,6h4M-6,-12v-4M0,-12v-4M6,-12v-4M-6,12v4M0,12v4M6,12v4" stroke="#7048e8" stroke-width="1.6"/></g>',
  };

  function substation() {
    return `<g class="dclick" data-ui="${UI.grid}" transform="translate(18,${GROUND - 130})">
      <path d="M30,0 L18,130 M30,0 L42,130 M21,95 L39,95 M23,70 L37,70 M25,45 L35,45 M10,18 L50,18 M14,34 L46,34" stroke="#495057" stroke-width="2.4" fill="none"/>
      <circle cx="10" cy="18" r="2.5" fill="#495057"/><circle cx="50" cy="18" r="2.5" fill="#495057"/>
      <g transform="translate(52,82)" filter="url(#dshadow)"><rect width="66" height="48" rx="6" fill="#e9ecef" stroke="#868e96"/>
        <path d="M14,24 l6,-9 l6,18 l6,-18 l6,18 l6,-18 l6,9" stroke="${C.elec}" stroke-width="2.4" fill="none"/></g>
      <text x="68" y="148" class="dlbl">Grid · EKZ area</text></g>`;
  }

  function building(b, i) {
    const x = slotX(i), sfh = b.type === 'SFH';
    const w = sfh ? 128 : 144, fl = floorsOf(b), fh = 34;
    const h = sfh ? 122 : fl * fh + 32, top = GROUND - h;
    const g = [];
    const ui = UI.house;
    // body + roof
    if (sfh) {
      g.push(`<path d="M${x - 10},${top + 2} L${x + w / 2},${top - 62} L${x + w + 10},${top + 2} Z" fill="#c92a2a" opacity=".88"/>`);
      g.push(`<path d="M${x - 10},${top + 2} L${x + w / 2},${top - 62} L${x + w + 10},${top + 2}" fill="none" stroke="#862e2e" stroke-width="3" stroke-linejoin="round"/>`);
      g.push(`<rect x="${x + w - 34}" y="${top - 40}" width="14" height="26" fill="#a61e4d" opacity=".9"/>`);
    } else {
      g.push(`<rect x="${x - 6}" y="${top - 10}" width="${w + 12}" height="12" rx="2" fill="#495057"/>`);
    }
    g.push(`<rect class="dclick" data-ui="${ui}" x="${x}" y="${top}" width="${w}" height="${h}" fill="url(#${sfh ? 'dwallS' : 'dwallM'})" stroke="#adb5bd" stroke-width="1.5" filter="url(#dshadow)"/>`);
    // windows (lit at night) — on upper floors for MFH, top half for SFH
    const win = [];
    if (sfh) {
      win.push([x + 16, top + 8, 28, 24], [x + w - 44, top + 8, 28, 24]);
    } else {
      for (let f = 0; f < fl - 1; f++) for (let k = 0; k < 4; k++) win.push([x + 13 + k * 33, top + 10 + f * fh, 21, 20]);
    }
    g.push(`<g class="dwin">${win.map(([a, c, d, e]) => `<rect x="${a}" y="${c}" width="${d}" height="${e}" rx="2"/>`).join('')}</g>`);
    // ground-floor cutaway: plant room with tanks and the heat emitter
    const cy = GROUND - 80;
    g.push(`<rect x="${x + 6}" y="${cy - 4}" width="${w - 12}" height="80" rx="5" fill="#fff" fill-opacity=".86" stroke="#ced4da" stroke-dasharray="3 2"/>`);
    // household / apartment load
    const lx = x + w - 32, ly = cy + 8;
    if (b.apartments_synthetic) {
      g.push(`<g class="dclick" data-ui="${ui}"><rect x="${lx - 10}" y="${ly - 2}" width="30" height="26" rx="4" fill="url(#dsynth)" stroke="${C.synth}" stroke-dasharray="3 2"/>
        <text x="${lx + 5}" y="${ly + 10}" text-anchor="middle" font-size="7.5" font-weight="700" fill="${C.synth}">apts</text><text x="${lx + 5}" y="${ly + 19}" text-anchor="middle" font-size="6.5" fill="${C.synth}">synthetic</text>
        <title>Apartment load is SYNTHETIC: drawn from other EKZ apartment meters, not this building (D-006, D-015).</title></g>`);
    } else {
      g.push(`<g class="dclick" data-ui="${ui}"><circle cx="${lx + 5}" cy="${ly + 10}" r="9" fill="#fff9db" stroke="#fab005"/><path d="M${lx + 2},${ly + 13} v4 h6 v-4" stroke="#868e96" fill="none"/><circle cx="${lx + 5}" cy="${ly + 8}" r="4" fill="#ffe066"/>
        <title>Household electricity (HEAPO, measured)</title></g>`);
    }
    // tanks
    const tank = (tx, kind, cap) => {
      const th = TH, tw = 22;
      if (!cap) return `<g class="dclick" data-ui="${UI.tank}"><rect x="${tx}" y="${cy + 6}" width="${tw}" height="${th}" rx="9" fill="none" stroke="#ced4da" stroke-dasharray="3 3"/><text x="${tx + tw / 2}" y="${cy + 38}" text-anchor="middle" font-size="8" fill="#adb5bd">none</text><title>No ${kind === 'dhw' ? 'hot-water' : 'heating'} tank in this building (D-017a rule).</title></g>`;
      return `<g class="dclick" data-ui="${UI.tank}">
        <rect x="${tx}" y="${cy + 6}" width="${tw}" height="${th}" rx="9" fill="url(#dtankbody)" stroke="#868e96"/>
        <clipPath id="dclip${kind}${i}"><rect x="${tx + 2}" y="${cy + 8}" width="${tw - 4}" height="${th - 4}" rx="7"/></clipPath>
        <rect id="dfill${kind}${i}" clip-path="url(#dclip${kind}${i})" x="${tx + 2}" y="${cy + 8 + th - 4}" width="${tw - 4}" height="0" fill="url(#${kind === 'dhw' ? 'ddhw' : 'dheat'})"/>
        <rect x="${tx}" y="${cy + 6}" width="${tw}" height="${th}" rx="9" fill="none" stroke="${C.synth}" stroke-width="1.2" stroke-dasharray="4 2" opacity=".75"/>
        <text x="${tx + tw / 2}" y="${cy + th + 15}" text-anchor="middle" font-size="8.5" font-weight="600" fill="#495057">${kind === 'dhw' ? 'DHW' : 'heat'}</text>
        <title id="dtt${kind}${i}">${kind === 'dhw' ? 'Hot-water' : 'Heating buffer'} tank ${fmt(cap, 2)} kWh_th (SYNTHETIC, D-017a)</title></g>`;
    };
    const t1 = x + 14, t2 = x + 42;
    g.push(tank(t1, 'heat', b.heating_tank_kwh_th));
    g.push(tank(t2, 'dhw', b.dhw_tank_kwh_th));
    // heat emitter (generic wavy pipe along the floor) and hot-water tap
    const ex = x + 72, ew = w - 112;
    let wave = `M${ex},${GROUND - 8}`;
    for (let k = 0; k <= ew; k += 8) wave += ` L${ex + k},${GROUND - 8 - ((k / 8) % 2 ? 6 : 0)}`;
    g.push(`<path class="dflow dheatflow" id="demit${i}" d="${wave}" stroke="${C.heat}" stroke-width="2.4" fill="none"/>`);
    g.push(`<path class="dflow dheatflow" id="dt2e${i}" d="M${t1 + 10},${cy + 6} V${cy - 1} H${ex} V${GROUND - 8}" stroke="${C.heat}" stroke-width="2.2" fill="none"/>`);
    if (b.dhw_tank_kwh_th) g.push(`<path class="dflow ddhwflow" id="dtap${i}" d="M${t2 + 10},${cy + 6} V${cy + 1} H${lx - 16} V${cy + 18}" stroke="${C.dhw}" stroke-width="2" fill="none"/><path d="M${lx - 20},${cy + 18} h8 v5" stroke="#495057" stroke-width="2" fill="none"/>`);
    // heat pump outdoors (right of the building)
    const hx = x + w + 6, hy = GROUND - 36;
    g.push(`<g class="dclick" data-ui="${UI.hp}" filter="url(#dshadow)"><rect x="${hx}" y="${hy}" width="30" height="32" rx="4" fill="#f8f9fa" stroke="#868e96"/>
      <circle cx="${hx + 15}" cy="${hy + 14}" r="10" fill="#e9ecef" stroke="#adb5bd"/>
      <g id="dfan${i}" class="dfan" style="transform-origin:${hx + 15}px ${hy + 14}px"><path d="M${hx + 15},${hy + 14} l0,-9 a4,4 0 0 1 4,4z M${hx + 15},${hy + 14} l9,0 a4,4 0 0 1 -4,4z M${hx + 15},${hy + 14} l0,9 a4,4 0 0 1 -4,-4z M${hx + 15},${hy + 14} l-9,0 a4,4 0 0 1 4,-4z" fill="#495057"/></g>
      <rect x="${hx + 4}" y="${hy + 27}" width="22" height="3" rx="1.5" fill="#dee2e6"/><rect id="dhpbar${i}" x="${hx + 4}" y="${hy + 27}" width="0" height="3" rx="1.5" fill="${C.elec}"/>
      <title id="dhptt${i}">Heat pump</title></g>`);
    g.push(`<text class="dclick dsmall" data-ui="${UI.hpsize}" x="${hx + 15}" y="${hy - 5}" text-anchor="middle">${fmt(b.hp_sh_nominal_kw, 1)} kW</text>`);
    // pipes HP -> tanks
    g.push(`<path class="dflow dheatflow" id="dhp2t${i}" d="M${hx},${hy + 8} H${x + w + 2} H${t1 + 10} V${cy + 6}" stroke="${C.heat}" stroke-width="2.6" fill="none" opacity=".95"/>`);
    if (b.dhw_tank_kwh_th) g.push(`<path class="dflow ddhwflow" id="dhp2d${i}" d="M${hx},${hy + 18} H${t2 + 11} V${cy + TH + 4}" stroke="${C.dhw}" stroke-width="2.2" fill="none"/>`);
    // meter + service cable from the bus
    const mx = x + w / 2 + 6;
    g.push(`<path class="dflow delecflow" id="dsvc${i}" d="M${mx},${BUS_Y} V${GROUND + 6}" stroke="${C.elec}" stroke-width="3" fill="none"/>`);
    g.push(`<g class="dclick" data-ui="${UI.meter}"><rect x="${mx - 11}" y="${GROUND - 4}" width="22" height="16" rx="3" fill="#212529"/><rect x="${mx - 8}" y="${GROUND - 1}" width="16" height="7" rx="1" fill="#69db7c" id="dmeterlcd${i}"/><title id="dmtt${i}">Electricity meter</title></g>`);
    // labels
    const lab = b.type === 'SFH' ? `${b.source} household${b.area_m2 ? ' · ' + fmt(b.area_m2, 0) + ' m²' : ''}` : `${b.source} · ${b.units} housing units`;
    g.push(`<g class="dclick" data-ui="${UI.selection}"><text x="${x + w / 2}" y="${(sfh ? top - 84 : top - 30)}" text-anchor="middle" class="dname">${esc(b.role)}</text>
      <text x="${x + w / 2}" y="${(sfh ? top - 84 : top - 30) + 14}" text-anchor="middle" class="dsub">${esc(b.building)} · ${esc(lab)}</text></g>`);
    g.push(`<g transform="translate(${mx},${BUS_Y + 30})"><rect x="-38" y="-11" width="76" height="20" rx="10" fill="#fff" fill-opacity=".95" stroke="${C.elec}"/><text id="dnet${i}" y="3" text-anchor="middle" class="dnet">–</text></g>`);
    els.buildings.push({b, x, w, top, hx, hy, t1, t2, cy, mx});
    return g.join('');
  }

  function feeds(bs) {
    const g = [];
    const env = FD.env_interface || {observations_active: []};
    const obs = new Set(env.observations_active);
    // weather -> each heat pump (COP depends on T_out) and -> controller if observed
    const wx = 1150, wy = 104;
    const yrail = 150;
    g.push(`<path class="dfeed" d="M${wx},${wy} V${yrail} H${slotX(0) + 150}" stroke="${C.feed}"/>`);
    for (const e of els.buildings) g.push(`<path class="dfeed" d="M${e.hx + 15},${yrail} V${e.hy}" stroke="${C.feed}"/>`);
    g.push(`<text x="${slotX(0) + 160}" y="${yrail - 5}" class="dfeedlbl">outdoor temperature → heat-pump COP (M-001)</text>`);
    if (obs.has('outdoor_dry_bulb_temperature')) g.push(`<path class="dfeed dobs" d="M${wx - 60},${wy - 40} H780" stroke="${C.ctrl}"/>`);
    // tariff -> grid and controller ; carbon -> grid (and controller only if observed)
    g.push(`<path class="dfeed" d="M48,${104} V${GROUND - 128}" stroke="${C.feed}"/>`);
    g.push(`<path class="dfeed" d="M100,${188} V${GROUND - 48}" stroke="${C.feed}"/>`);
    if (obs.has('electricity_pricing')) g.push(`<path class="dfeed dobs" d="M250,${62} H500" stroke="${C.ctrl}"/>`);
    if (obs.has('carbon_intensity')) g.push(`<path class="dfeed dobs" d="M250,${148} C400,148 450,80 500,70" stroke="${C.ctrl}"/>`);
    // controller -> tanks (actions)
    for (const [k, e] of els.buildings.entries()) {
      g.push(`<path class="dflow dctrlflow" id="dact${k}" d="M640,98 C640,${150 + k * 6} ${e.t1 + 10},${e.top - 20} ${e.t1 + 10},${e.cy + 2}" stroke="${C.ctrl}" stroke-width="1.3" fill="none" opacity=".4"/>`);
    }
    // observations: net consumption and tank SOC back to the controller (as one bundle line)
    g.push(`<path class="dfeed dobs" d="M${slotX(5) + 70},${GROUND - 8} C1240,300 900,90 780,70" stroke="${C.ctrl}" opacity=".35"/>`);
    // bus
    g.push(`<path class="dflow delecflow" id="dbus" d="M${18 + 118},${GROUND - 25} V${BUS_Y} H${W - 10}" stroke="${C.elec}" stroke-width="4" fill="none"/>`);
    return g.join('');
  }

  function legend() {
    const items = [[C.elec, 'electricity (import)', ''], [C.heat, 'space-heating water', ''], [C.dhw, 'hot water', ''], [C.ctrl, 'controller action', '6 4'], [C.feed, 'data feed', '2 4']];
    let x = 18;
    const g = items.map(([c, t, d]) => { const s = `<g transform="translate(${x},${H - 28})"><line x2="26" stroke="${c}" stroke-width="3" ${d ? `stroke-dasharray="${d}"` : ''}/><text x="32" y="4" class="dleg">${t}</text></g>`; x += 32 + t.length * 6.2 + 18; return s; });
    g.push(`<g transform="translate(${x},${H - 36})"><rect width="22" height="14" rx="3" fill="url(#dsynth)" stroke="${C.synth}" stroke-dasharray="3 2"/><text x="28" y="11" class="dleg">synthetic (tanks, apartment loads)</text></g>`);
    return `<rect y="${H - 58}" width="${W}" height="58" fill="#212529"/><g>${g.join('')}</g>`;
  }

  function build() {
    const host = document.getElementById('district');
    if (!host || !FD.district || !SI) return;
    const bs = FD.district.buildings;
    let svg = `<svg id="dsvg" viewBox="0 0 ${W} ${H}" xmlns="${NS}" role="img" aria-label="Six-building district">${defs()}${sky()}`;
    svg += substation();
    const bld = bs.map((b, i) => building(b, i)).join('');
    svg += `<g id="dfeeds">${feeds(bs)}</g>` + bld;
    svg += card(18, 30, 232, 74, UI.tariff, ICON.tariff, 'Electricity price', 'dtariff');
    svg += card(18, 114, 232, 74, UI.carbon, ICON.carbon, 'Grid carbon (modeled)', 'dcarbon');
    svg += card(1030, 30, 232, 74, UI.weather, ICON.weather, 'Weather · Zurich/Kloten', 'dweather');
    svg += card(500, 30, 280, 68, UI.controller, ICON.ctrl, 'Controller', 'dctrl');
    svg += `<g class="dclick" data-ui="${UI.reward}" transform="translate(790,44)"><rect width="150" height="40" rx="10" fill="#fff" fill-opacity=".9" stroke="#d0bfff"/><text x="12" y="17" class="dt1" font-size="11">Reward R-001</text><text x="12" y="32" class="dt2" id="dreward">–</text></g>`;
    const title = `<text class="dclick dtitle" data-ui="${UI.district}" x="${W - 18}" y="${H - 24}" text-anchor="end">Six-building district · 2023 · about this view ⓘ</text>`;
    svg += legend() + title + '</svg>';
    host.querySelector('.dstage').innerHTML = svg;
    host.querySelectorAll('.dclick').forEach((e) => e.addEventListener('click', (ev) => { ev.stopPropagation(); SCLopen(e.dataset.ui); }));
    built = true;
  }

  // ------------------------------------------------------------------ dynamic state for one hour
  const dur = (v, vmax) => (v > 1e-6 ? Math.max(0.35, 2.6 - 2.2 * Math.min(1, v / vmax)) : 0);
  function setFlow(id, v, vmax, wmin, wmax) {
    const e = document.getElementById(id);
    if (!e) return;
    const d = dur(v, vmax);
    e.style.animationDuration = d ? d + 's' : '0s';
    e.classList.toggle('dstill', !d);
    if (wmax) e.setAttribute('stroke-width', d ? wmin + (wmax - wmin) * Math.min(1, v / vmax) : wmin);
  }
  function localLabel(i) {
    const d = new Date(Date.parse(SI.start_utc) + (i * SI.step_s + SI.utc_offset_h[i] * 3600) * 1000);
    return d.toISOString().slice(0, 16).replace('T', ' ');
  }
  function update() {
    if (!built) return;
    const i = hour, T = trace(), S = SI.series;
    const ghi = S.ghi.values[i] || 0, night = ghi < 5;
    // sky: brightness follows measured GHI at this hour (decorative mapping)
    const k = Math.min(1, ghi / 700);
    const mix = (a, b) => a.map((x, j) => Math.round(x + (b[j] - x) * k));
    const top = night ? [16, 28, 58] : mix([150, 180, 210], [120, 190, 255]), bot = night ? [44, 62, 100] : mix([215, 225, 235], [235, 247, 255]);
    document.getElementById('dsky0').setAttribute('stop-color', `rgb(${top})`);
    document.getElementById('dsky1').setAttribute('stop-color', `rgb(${bot})`);
    document.getElementById('dstars').setAttribute('opacity', night ? 0.8 : 0);
    document.getElementById('dmoon').setAttribute('opacity', night ? 1 : 0);
    document.getElementById('dmoonshade').setAttribute('fill', `rgb(${top})`);
    const lh = SI.local_hour[i] + 0.5, sx = 200 + (lh - 5) / 16 * 900, sy = 330 - Math.sin(Math.max(0, Math.min(1, (lh - 5) / 16)) * Math.PI) * 220;
    const sun = document.getElementById('dsunc');
    sun.setAttribute('cx', sx); sun.setAttribute('cy', night ? 600 : sy); sun.setAttribute('r', 22 + 26 * k);
    document.getElementById('dsvg').classList.toggle('dnight', night);
    // feed cards
    const tier = SI.tier_high[i] ? 'high tariff' : 'low tariff';
    document.getElementById('dtariff').textContent = `${fmt(S.price.values[i], 2)} Rp/kWh · ${tier}`;
    document.getElementById('dtariffb').textContent = 'EKZ standard 2023, excl. VAT';
    document.getElementById('dcarbon').textContent = `${fmt(S.carbon.values[i], 1)} gCO2eq/kWh`;
    document.getElementById('dcarbonb').textContent = (SI.flags.neighbour_intensity_fallback_flag.values[i] ? '⚑ neighbour fallback · ' : SI.flags.gap_interpolated_flag.values[i] ? '⚑ missing hour · ' : '') + 'modeled, relative signal only';
    document.getElementById('dweather').textContent = `${fmt(S.temp_c.values[i], 1)} °C · GHI ${fmt(S.ghi.values[i], 0)} W/m²`;
    document.getElementById('dweatherb').textContent = 'measured, MeteoSwiss KLO';
    document.getElementById('dctrl').textContent = ctrlName();
    // per building
    const bs = els.buildings;
    let maxNet = 1, maxHp = 1;
    if (T) for (let b = 1; b <= bs.length; b++) { maxNet = Math.max(maxNet, maxOf(T, `b${b}_net_kwh`)); maxHp = Math.max(maxHp, maxOf(T, `b${b}_hp_kwh_el`)); }
    let dnet = 0;
    bs.forEach((e, j) => {
      const b = j + 1;
      const net = T ? T[`b${b}_net_kwh`][i] : null, hp = T ? T[`b${b}_hp_kwh_el`][i] : null;
      const sh = T ? T[`b${b}_heating_storage_soc`][i] : null, sd = T ? T[`b${b}_dhw_storage_soc`][i] : null;
      const ah = T && T[`b${b}_action_heating_storage`] ? T[`b${b}_action_heating_storage`][i] : 0;
      dnet += net || 0;
      document.getElementById(`dnet${j}`).textContent = net == null ? 'no trace' : `${fmt(net, 2)} kWh`;
      document.getElementById(`dmtt${j}`).textContent = `${e.b.role} net electricity this hour: ${fmt(net, 3)} kWh (${ctrlName()})`;
      setFlow(`dsvc${j}`, Math.max(net || 0, 0), maxNet, 2, 7);
      setFlow(`dhp2t${j}`, hp || 0, maxHp, 1.6, 5);
      setFlow(`dhp2d${j}`, hp || 0, maxHp, 1.4, 3.6);
      setFlow(`demit${j}`, hp || 0, maxHp);
      setFlow(`dt2e${j}`, (hp || 0) + Math.max(-(ah || 0), 0), maxHp);
      setFlow(`dtap${j}`, sd != null ? 0.3 : 0, 1);
      const fan = document.getElementById(`dfan${j}`), d = dur(hp || 0, maxHp);
      fan.style.animationDuration = d ? (d * 0.6) + 's' : '0s';
      fan.classList.toggle('dstill', !d);
      const bar = document.getElementById(`dhpbar${j}`);
      bar.setAttribute('width', 22 * Math.min(1, (hp || 0) / (e.b.hp_sh_nominal_kw + e.b.hp_dhw_nominal_kw)));
      document.getElementById(`dhptt${j}`).textContent = `${e.b.role} heat pump: ${fmt(hp, 3)} kWh electricity this hour; nominal ${fmt(e.b.hp_sh_nominal_kw, 2)} kW (heating) + ${fmt(e.b.hp_dhw_nominal_kw, 2)} kW (DHW); T_sup ${e.b.T_sup_sh_c} °C, η ${fmt(e.b.eta_sh, 3)}`;
      for (const [kind, soc, cap] of [['heat', sh, e.b.heating_tank_kwh_th], ['dhw', sd, e.b.dhw_tank_kwh_th]]) {
        const f = document.getElementById(`dfill${kind}${j}`);
        if (!f) continue;
        const hgt = (TH - 4) * Math.max(0, Math.min(1, soc || 0));
        f.setAttribute('height', hgt); f.setAttribute('y', e.cy + 8 + TH - 4 - hgt);
        const tt = document.getElementById(`dtt${kind}${j}`);
        if (tt) tt.textContent = `${kind === 'dhw' ? 'Hot-water' : 'Heating buffer'} tank ${fmt(cap, 2)} kWh_th, state of charge ${fmt(soc, 3)} (SYNTHETIC, D-017a)`;
      }
      const act = document.getElementById(`dact${j}`);
      act.classList.toggle('drev', (ah || 0) < 0);
      act.style.animationDuration = Math.abs(ah || 0) > 1e-6 ? '1.2s' : '0s';
      act.classList.toggle('dstill', Math.abs(ah || 0) < 1e-6);
      act.setAttribute('opacity', Math.abs(ah || 0) > 1e-6 ? 0.85 : 0.15);
      act.setAttribute('stroke-width', Math.abs(ah || 0) > 1e-6 ? 2 : 1.2);
      document.getElementById(`dmeterlcd${j}`).setAttribute('fill', (net || 0) > 0.01 ? '#69db7c' : '#2b8a3e');
    });
    setFlow('dbus', Math.max(dnet, 0), maxNet * bs.length, 3, 8);
    document.getElementById('dreward').textContent = T ? `${fmt(T.reward[i], 3)} this step` : 'no trace';
    const r = document.getElementById('dread');
    if (r) r.innerHTML = `<b>${localLabel(i)}</b> local · ${['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][SI.weekday[i]]} · step ${i} · district net <b>${T ? fmt(dnet, 2) + ' kWh' : '–'}</b> · ${esc(ctrlName())}`;
    const sl = document.getElementById('dhour');
    if (sl && +sl.value !== i) sl.value = i;
  }
  const _max = {};
  function maxOf(T, key) {
    const id = ctrlName() + key;
    if (!(id in _max)) { let m = 0; for (const v of T[key]) if (v > m) m = v; _max[id] = m; }
    return _max[id];
  }

  // ------------------------------------------------------------------ controls
  function argmax(a, sign) { let b = 0; for (let i = 0; i < a.length; i++) if (a[i] != null && sign * a[i] > sign * a[b]) b = i; return b; }
  function controls() {
    const host = document.getElementById('district');
    const n = (RS && RS.traces[ctrlName()]) ? RS.traces[ctrlName()].n : SI.n;
    host.querySelector('.dctl').innerHTML = `<button id="dplay" title="play / pause">▶</button>
      <select id="dspeed" title="speed"><option value="1">1 h/step</option><option value="3" selected>3 h/step</option><option value="24">1 day/step</option></select>
      <input id="dhour" type="range" min="0" max="${n - 1}" value="${hour}">
      <span class="djump"><button data-j="peak">district peak hour</button><button data-j="cold">coldest hour</button><button data-j="sun">sunniest hour</button><button data-j="night">a winter night</button></span>
      <div id="dread" class="small"></div>`;
    host.querySelector('#dhour').addEventListener('input', (e) => { hour = +e.target.value; update(); });
    host.querySelector('#dplay').addEventListener('click', () => {
      const b = host.querySelector('#dplay');
      if (playing) { clearInterval(playing); playing = null; b.textContent = '▶'; return; }
      b.textContent = '❚❚';
      playing = setInterval(() => { hour = (hour + +host.querySelector('#dspeed').value) % n; update(); }, 140);
    });
    host.querySelectorAll('.djump button').forEach((b) => b.addEventListener('click', () => {
      const T = trace(), j = b.dataset.j;
      if (j === 'peak' && T) hour = argmax(T.district_net_kwh, 1);
      if (j === 'cold') hour = argmax(SI.series.temp_c.values, -1);
      if (j === 'sun') hour = argmax(SI.series.ghi.values, 1);
      if (j === 'night') { const c = argmax(SI.series.temp_c.values, -1); hour = c - SI.local_hour[c] + 2 > 0 ? c - SI.local_hour[c] + 2 : c; }
      update();
    }));
  }

  function init() {
    build();
    if (!built) return;
    controls();
    const go = () => { const T = trace(); if (T && hour === 0) hour = argmax(T.district_net_kwh, 1); update(); };
    if (window.SCLcharts && window.SCLcharts.loadTrace) window.SCLcharts.loadTrace(ctrlName(), go); else go();
    const cs = document.getElementById('ctrl');
    if (cs) cs.addEventListener('change', () => window.SCLcharts.loadTrace(ctrlName(), update));
  }
  window.SCLdistrict = {init, update};
})();
