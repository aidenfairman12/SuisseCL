"""B9 metrics subset (Phase B step 2): scenario metrics computed from a rollout's arrays, independent of CityLearn.

Inputs are plain arrays of shape (T, B) = steps x buildings (a (T,) vector is treated as one building), energy in kWh per
step, prices in CHF/kWh. Sign convention (CityLearn 3.3.0 `net_electricity_consumption`): grid import positive, export
negative, per building and per step. Building energy balance used here:

    net = load + battery_charge - battery_discharge - pv

with `load` the end-use consumption (heat pump, tanks, other), `pv` the PV generation (>= 0) and `battery_charge` /
`battery_discharge` the grid-side battery energy (>= 0). `load` is derived from the other inputs when not given.

Definitions (all district values are sums over buildings unless stated):
  import_kwh, export_kwh            sum of max(net, 0) and max(-net, 0), netted per building and step, as CityLearn does
  peak_import_kw_coincident_gross   max over steps of the sum over buildings of import (no netting between buildings)
  peak_net_kw_coincident            max over steps of the sum over buildings of net (district meter with netting)
  peak_import_kw_building_sum       sum over buildings of each building's own maximum import (non coincident)
  pv_self_consumption               1 - export / pv generation, clipped to [0, 1]; None without PV
  self_sufficiency                  1 - import / load, clipped to [0, 1]
  import_cost_chf, export_revenue_chf, bill_chf   bill = import cost - export revenue; revenue None without export price
  battery_equivalent_cycles         (charge + discharge) / 2 / capacity, summed over buildings with a battery; None without
  comfort_violation_steps, comfort_degree_hours   indoor temperature outside [lower, upper]; None until a thermal model exists
`None` means absent, never 0 (data contract rule).
"""
import numpy as np


def _a(x, name, shape=None):
    if x is None:
        return None
    a = np.asarray(x, dtype=float)
    if a.ndim == 1:
        a = a[:, None]
    if a.ndim != 2:
        raise ValueError(f'{name} must be 1-D or 2-D')
    if shape is not None and a.shape != shape:
        raise ValueError(f'{name} has shape {a.shape}, expected {shape}')
    return a


def _price(p, shape, name):
    if p is None:
        return None
    a = np.asarray(p, dtype=float)
    if a.ndim == 0:
        a = np.full(shape, float(a))
    elif a.ndim == 1:
        if a.shape[0] != shape[0]:
            raise ValueError(f'{name} length {a.shape[0]} != steps {shape[0]}')
        a = np.repeat(a[:, None], shape[1], axis=1)
    elif a.shape != shape:
        raise ValueError(f'{name} has shape {a.shape}, expected {shape}')
    return a


def compute_metrics(net_kwh, price_import, step_hours=1.0, pv_kwh=None, battery_charge_kwh=None,
                    battery_discharge_kwh=None, battery_capacity_kwh=None, price_export=None,
                    load_kwh=None, indoor_temp=None, comfort_lower=None, comfort_upper=None):
    net = _a(net_kwh, 'net_kwh')
    T, B = net.shape
    sh = (T, B)
    pv = _a(pv_kwh, 'pv_kwh', sh)
    ch = _a(battery_charge_kwh, 'battery_charge_kwh', sh)
    dis = _a(battery_discharge_kwh, 'battery_discharge_kwh', sh)
    if pv is not None and (pv < -1e-12).any():
        raise ValueError('pv_kwh must be >= 0 (generation as a positive number)')
    for nm, v in (('battery_charge_kwh', ch), ('battery_discharge_kwh', dis)):
        if v is not None and (v < -1e-12).any():
            raise ValueError(f'{nm} must be >= 0')
    pv0 = np.zeros(sh) if pv is None else pv
    bat0 = (0.0 if ch is None else ch) - (0.0 if dis is None else dis)
    load = _a(load_kwh, 'load_kwh', sh)
    if load is None:
        load = net + pv0 - bat0
    imp = np.maximum(net, 0.0)
    exp = np.maximum(-net, 0.0)
    pi = _price(price_import, sh, 'price_import')
    pe = _price(price_export, sh, 'price_export')
    out = {'steps': int(T), 'buildings': int(B), 'step_hours': float(step_hours),
           'import_kwh': float(imp.sum()), 'export_kwh': float(exp.sum()), 'load_kwh': float(load.sum()),
           'peak_import_kw_coincident_gross': float(imp.sum(axis=1).max() / step_hours),
           'peak_net_kw_coincident': float(net.sum(axis=1).max() / step_hours),
           'peak_import_kw_building_sum': float(imp.max(axis=0).sum() / step_hours)}
    out['import_cost_chf'] = float((imp * pi).sum())
    out['export_revenue_chf'] = None if pe is None else float((exp * pe).sum())
    out['bill_chf'] = out['import_cost_chf'] - (out['export_revenue_chf'] or 0.0)
    pv_tot = float(pv0.sum())
    out['pv_generation_kwh'] = None if pv is None else pv_tot
    out['pv_self_consumption'] = None if (pv is None or pv_tot <= 0) else float(np.clip(1.0 - exp.sum() / pv_tot, 0.0, 1.0))
    ld = float(load.sum())
    out['self_sufficiency'] = None if ld <= 0 else float(np.clip(1.0 - imp.sum() / ld, 0.0, 1.0))
    if ch is None and dis is None:
        out['battery_equivalent_cycles'] = None
    else:
        cap = np.asarray(battery_capacity_kwh, dtype=float).reshape(-1) if battery_capacity_kwh is not None else None
        if cap is None or cap.shape[0] not in (1, B):
            raise ValueError('battery_capacity_kwh (scalar or per building) is required with battery energy')
        cap = np.broadcast_to(cap, (B,))
        thr = ((0.0 if ch is None else ch) + (0.0 if dis is None else dis)).sum(axis=0) / 2.0
        has = cap > 0
        out['battery_equivalent_cycles'] = float((thr[has] / cap[has]).sum()) if has.any() else None
    if indoor_temp is None:
        out['comfort_violation_steps'] = None
        out['comfort_degree_hours'] = None
    else:
        t = _a(indoor_temp, 'indoor_temp', sh)
        lo = np.broadcast_to(np.asarray(comfort_lower, dtype=float), sh)
        hi = np.broadcast_to(np.asarray(comfort_upper, dtype=float), sh)
        dev = np.maximum(lo - t, 0.0) + np.maximum(t - hi, 0.0)
        out['comfort_violation_steps'] = int((dev > 1e-12).sum())
        out['comfort_degree_hours'] = float(dev.sum() * step_hours)
    return out
