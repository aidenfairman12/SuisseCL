"""Model M-001: Carnot-fraction heat-pump COP in CityLearn's functional form, and electricity -> heat derivation.

COP(T_out) = eta * (T_sup + 273.15) / (T_sup - T_out), values < 0 or > 20 set to 20
(identical to citylearn.energy_model.HeatPump.get_cop(heating=True), verified by a test).
Heat output of a mode = electricity * COP(T_out).  eta is calibrated so that the annual
ratio sum(heat)/sum(electricity) equals a target SPF (literature value, see parameter_registry.csv).
All outputs are DERIVED (not measured).
"""
import numpy as np


def cop(t_out, eta, t_sup):
    t_out = np.asarray(t_out, dtype=float)
    with np.errstate(divide='ignore', invalid='ignore'):
        c = eta * (t_sup + 273.15) / (t_sup - t_out)
    c = np.where(c < 0, 20.0, c)
    c = np.where(c > 20, 20.0, c)
    return c


def calibrate_eta(elec, t_out, t_sup, spf_target, lo=0.05, hi=1.0):
    """eta such that sum(elec*cop)/sum(elec) = spf_target (bisection; monotone in eta)."""
    elec = np.asarray(elec, dtype=float)
    m = ~(np.isnan(elec) | np.isnan(t_out))
    e, t = elec[m], np.asarray(t_out)[m]
    f = lambda eta: (e * cop(t, eta, t_sup)).sum() / e.sum() - spf_target
    if f(lo) > 0 or f(hi) < 0:
        raise ValueError('spf_target not reachable within eta bounds')
    for _ in range(80):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if f(mid) < 0 else (lo, mid)
    return (lo + hi) / 2


def split_baseline(e_hp, local_hour, temp_c, warm_threshold_c=16.0):
    """Split hourly HP electricity into a non-space-heating baseline and space heating.

    Baseline per day B = mean daily electricity on days with mean T >= warm_threshold_c.
    Hourly shape p(h) = mean warm-day profile by local hour (normalised to sum 1).
    E_base(t) = min(E(t), B * p(hour(t))) ; E_sh = E - E_base.  Returns (e_base, e_sh, B_kwh_day).
    """
    import pandas as pd
    s = pd.Series(np.asarray(e_hp, dtype=float), index=e_hp.index)
    days = s.index.tz_convert('Europe/Zurich').floor('1D')
    tmean = pd.Series(np.asarray(temp_c, dtype=float), index=s.index).groupby(days).transform('mean')
    warm = (tmean >= warm_threshold_c).to_numpy()
    full = s.groupby(days).transform(lambda x: x.notna().all()).to_numpy().astype(bool)
    ok = warm & full
    B = float(s[ok].groupby(days[ok]).sum().mean())
    prof = s[ok].groupby(s.index.tz_convert('Europe/Zurich').hour[ok]).mean()
    prof = prof / prof.sum()
    hours = s.index.tz_convert('Europe/Zurich').hour
    base = np.minimum(s.to_numpy(), B * prof.reindex(hours).to_numpy())
    base = pd.Series(base, index=s.index)
    return base, s - base, B
