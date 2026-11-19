"""Climate impact metrics (Phase C proposal section 9): added consumption, PV mitigation and spill-over to the grid, per building and district.

Inputs per building are hourly (or any step) arrays in kWh per step, all >= 0 except the battery:
  base      household load (non-shiftable)                  dhw     DHW heat-pump electricity
  heat      space heating electricity                       cool    space cooling electricity
  pv        PV generation (positive here; CityLearn stores it negative)
  batt      battery net charge from the bus (+ charging, - discharging), battery losses stay inside the battery
  temp      indoor temperature at the end of each step (optional, for overheating degree-hours)
Balance: base + dhw + heat + cool + batt - pv = import - export (the net electricity consumption of CityLearn).

PV allocation (a bookkeeping rule, stated, not a physical fact; marginal attribution is not unique): in every step the PV generation serves the loads in a priority order
(default: base, dhw, heat, cool, battery charging; sensitivity 'hp_first': heat, cool, base, dhw, battery charging); battery discharge then serves the remaining load of the
four loads in proportion to what is left, the rest of the load is bought from the grid; unused PV and unused discharge are exported.
Run the tests: pytest swiss/tests/test_climate_metrics.py
"""
import numpy as np

LOADS = ('base', 'dhw', 'heat', 'cool')
PRIORITY = {'default': ('base', 'dhw', 'heat', 'cool', 'charge'), 'hp_first': ('heat', 'cool', 'base', 'dhw', 'charge')}
SUMMER_MONTHS = (6, 7, 8)


def allocate(base, dhw, heat, cool, pv, batt, priority='default'):
    """Step-wise allocation of PV and battery discharge. Returns dict of arrays: pv_to_<load>, batt_to_<load>, grid_<load> (+ grid_charge), export, imp."""
    a = {k: np.asarray(v, dtype=float) for k, v in dict(base=base, dhw=dhw, heat=heat, cool=cool, pv=pv, batt=batt).items()}
    n = len(a['base'])
    charge, discharge = np.maximum(a['batt'], 0.0), np.maximum(-a['batt'], 0.0)
    need = {'base': a['base'].copy(), 'dhw': a['dhw'].copy(), 'heat': a['heat'].copy(), 'cool': a['cool'].copy(), 'charge': charge.copy()}
    rest = a['pv'].copy()
    out = {}
    for k in PRIORITY[priority]:
        used = np.minimum(rest, need[k])
        out[f'pv_to_{k}'] = used
        need[k] = need[k] - used
        rest = rest - used
    pv_export = rest
    remaining = sum(need[k] for k in LOADS)
    used_dis = np.minimum(discharge, remaining)
    share = np.divide(used_dis, remaining, out=np.zeros(n), where=remaining > 1e-12)
    for k in LOADS:
        out[f'batt_to_{k}'] = need[k] * share
        out[f'grid_{k}'] = need[k] - out[f'batt_to_{k}']
    out['grid_charge'] = need['charge']
    out['pv_export'] = pv_export
    out['batt_export'] = discharge - used_dis
    out['export'] = pv_export + out['batt_export']
    out['imp'] = sum(out[f'grid_{k}'] for k in LOADS) + out['grid_charge']
    return out


def series_from_env(env, i0=0, i1=None):
    """Per-building series (kWh per step) from a CityLearn environment after a rollout, steps [i0, i1]."""
    sl = slice(i0, None if i1 is None else i1 + 1)
    out = []
    for b in env.buildings:
        g = lambda name: np.asarray(getattr(b, name), dtype=float)[sl]   # noqa: E731
        d = {'base': g('non_shiftable_load'), 'dhw': g('dhw_electricity_consumption'), 'heat': g('heating_electricity_consumption'),
             'cool': g('cooling_electricity_consumption'), 'pv': -g('solar_generation'), 'batt': g('electrical_storage_electricity_consumption'),
             'net': g('net_electricity_consumption')}
        dyn = getattr(b, 'dynamics', None)
        if dyn is not None and hasattr(dyn, 'area_eff'):
            d['temp'] = np.asarray(b.energy_simulation.indoor_dry_bulb_temperature, dtype=float)[sl]
            d['area'] = float(dyn.area_eff)
            if getattr(dyn, 'cooled_fraction', 1.0) < 1.0 and hasattr(b, 'zone_temperature'):     # archetype B (room units): the two zone temperatures
                d['temp_cooled'], d['temp_uncooled'], d['frac'] = b.zone_temperature[0][sl].copy(), b.zone_temperature[1][sl].copy(), float(dyn.cooled_fraction)
        out.append(d)
    return out


def degree_hours(s, limit=26.0, dt_h=1.0):
    """Degree-hours above `limit` of a building series: (building value, cooled zone, uncooled zone). Single-node buildings: the building value from `temp`, zones None.
    Room-unit buildings (archetype B): the building value is the area-weighted sum of the zone values, f x cooled zone + (1 - f) x uncooled zone."""
    if 'temp_cooled' in s:
        c = float(np.nansum(np.maximum(s['temp_cooled'] - limit, 0.0)) * dt_h); u = float(np.nansum(np.maximum(s['temp_uncooled'] - limit, 0.0)) * dt_h)      # nansum: the last step of a year has no zone value
        return s['frac'] * c + (1.0 - s['frac']) * u, c, u
    return float(np.maximum(s['temp'] - limit, 0.0).sum() * dt_h), None, None


def building_metrics(s, months, priority='default', temp_limit=26.0, dt_h=1.0, units=1.0):
    """Annual and summer metrics of one building from series dict `s` and the month number (1 to 12) of each step."""
    al = allocate(s['base'], s['dhw'], s['heat'], s['cool'], s['pv'], s['batt'], priority)
    months = np.asarray(months)
    summer = np.isin(months, SUMMER_MONTHS)
    net = s['base'] + s['dhw'] + s['heat'] + s['cool'] + s['batt'] - s['pv']
    res = {'balance_error_kwh': float(np.abs(net - (al['imp'] - al['export'])).max())}
    for tag, m in (('annual', np.ones_like(summer)), ('summer', summer)):
        r = {k: float(s[k][m].sum()) for k in ('base', 'dhw', 'heat', 'cool', 'pv')}
        r['import'] = float(al['imp'][m].sum()); r['export'] = float(al['export'][m].sum())
        cool = r['cool']
        r['pv_share_of_cooling'] = float(al['pv_to_cool'][m].sum() / cool) if cool > 1e-9 else None
        r['battery_share_of_cooling'] = float(al['batt_to_cool'][m].sum() / cool) if cool > 1e-9 else None
        r['grid_share_of_cooling'] = float(al['grid_cool'][m].sum() / cool) if cool > 1e-9 else None
        used_pv = r['pv'] - float(al['pv_export'][m].sum())
        r['pv_used_onsite'] = used_pv
        r['pv_self_consumption'] = used_pv / r['pv'] if r['pv'] > 1e-9 else None
        total = r['base'] + r['dhw'] + r['heat'] + r['cool']
        grid_loads = float(sum(al[f'grid_{k}'][m].sum() for k in LOADS))
        r['self_sufficiency'] = 1.0 - grid_loads / total if total > 1e-9 else None      # share of the four loads not bought from the grid
        res[tag] = r
    if 'temp' in s:
        res['degree_hours_above'], dh_c, dh_u = degree_hours(s, temp_limit, dt_h)
        if dh_c is not None:
            res['degree_hours_above_cooled_zone'], res['degree_hours_above_uncooled_zone'] = dh_c, dh_u
    res['peak_net_kw'] = float((net / dt_h).max())
    return res, al, net


def district_metrics(series, months, priority='default', temp_limit=26.0, dt_h=1.0, names=None, units=None):
    """District totals and peaks plus the per-building metrics. `series`: list of dicts as returned by series_from_env."""
    per, nets = [], []
    for s in series:
        m, al, net = building_metrics(s, months, priority, temp_limit, dt_h)
        per.append(m); nets.append(net)
    net_d = np.sum(nets, axis=0)
    summer = np.isin(np.asarray(months), SUMMER_MONTHS)
    d = {'peak_net_kw': float((net_d / dt_h).max()), 'summer_peak_net_kw': float((net_d[summer] / dt_h).max()) if summer.any() else None, 'peak_step': int(np.argmax(net_d)),
         'balance_error_kwh': float(max(p['balance_error_kwh'] for p in per))}
    for tag in ('annual', 'summer'):
        agg = {k: float(sum(p[tag][k] for p in per)) for k in ('base', 'dhw', 'heat', 'cool', 'pv', 'import', 'export', 'pv_used_onsite')}
        agg['pv_self_consumption'] = agg['pv_used_onsite'] / agg['pv'] if agg['pv'] > 1e-9 else None
        d[tag] = agg
    d['degree_hours_above'] = float(sum(p.get('degree_hours_above', 0.0) for p in per))
    d['buildings'] = per
    d['net_kwh_per_step'] = net_d
    return d


def difference(with_cooling, without_cooling):
    """Added consumption, import, export and peak of a cell against the same cell without cooling (difference method; same climate, same controller)."""
    out = {}
    for tag in ('annual', 'summer'):
        w, o = with_cooling[tag], without_cooling[tag]
        out[tag] = {k: w[k] - o[k] for k in ('heat', 'cool', 'import', 'export', 'pv_used_onsite')}
    out['peak_net_kw'] = with_cooling['peak_net_kw'] - without_cooling['peak_net_kw']
    out['summer_peak_net_kw'] = with_cooling['summer_peak_net_kw'] - without_cooling['summer_peak_net_kw']
    out['degree_hours_above'] = with_cooling['degree_hours_above'] - without_cooling['degree_hours_above']
    return out
