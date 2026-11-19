"""Phase C, WP1: hourly climate scenarios for Zurich/Kloten from CH2025 daily data (docs/phases/phase_c_proposal_updated.md section 3).

Inputs : data/raw/ch2025_klo/ogd-climate-scenarios-ch2025_klo_<var>_<level>.csv   (MeteoSwiss & ETH Zurich 2025, CC BY 4.0; daily, 365-day calendar,
         years 0001 to 0030 are anonymous model-years, several regional-climate-model chains per file, NA = missing; variables tas, tasmin, tasmax, rsds, hurs;
         levels ref91-20, gwl1.5, gwl2.0, gwl3.0)
         data/canonical/weather_klo_2023_hourly.csv                                  (observed 2023 hourly Kloten series, UTC; DER-007)
Outputs: data/canonical/climate/weather_klo_<scenario>_hourly.csv                    same columns as the 2023 file
         data/canonical/climate/pv_ac_w_per_kwp_<scenario>_hourly.csv                scenario PV per kWp (M-003 chain of swiss/models/pv.py)
         data/canonical/climate/heatwave_spells.json                                 chosen spells and severity distributions
         docs/experiments/validation_reports/climate_scenarios.md                    generated validation report (no hand-typed numbers)
Scenarios: `hist` is the 2023 file itself (not duplicated). gwl1.5, gwl2.0, gwl3.0 = typical warmed 2023 (delta change); hist_hw, gwl2.0_hw, gwl3.0_hw =
           the same with a hot spell from the CH2025 ensemble of that level replacing the 168 rows of the 2023 test week 29 (rows 4872 to 5039).

Method (assumptions are labelled A-C1 to A-C8 in the report and in docs/phases/phase_c_drafts/wp1_registry_draft.md):
 1. Typical warmed year. Per month m (local calendar month of the row): delta of the ensemble median (over chains, model-years and days of the month) of the level
    minus the reference 1991-2020 for tas, tasmin, tasmax (additive) and rsds, hurs (ratio). Hourly temperature: T' = T + dtas_m + (dtmax_m - dtmin_m) (s_d(h) - sbar_m)
    where s_d(h) is the observed normalised diurnal position of the hour in its local day ((T - Tmin_d) / (Tmax_d - Tmin_d), 0.5 on days with a range below 1 K) and
    sbar_m its monthly mean: the monthly mean warming equals dtas and the diurnal range changes by dtmax - dtmin. Radiation: global, direct-horizontal and diffuse of
    the hour are multiplied by min(ratio, cap / ghi), cap = max(Haurwitz clear-sky hourly mean, observed value of that hour). Humidity: rh x ratio, at most 100.
 2. Hot spells. All 7-day windows inside a model-year (any chain with valid tas, tasmin, tasmax, rsds, hurs on all seven days) are ranked by mean tasmax. The target is the
    PERCENTILE (default 95) of that distribution over ALL windows of the level's ensemble; the chosen spell is the window that starts between 1 June and 25 August (so it
    lies in JJA, as week 29 does) whose severity is closest to the target (ties: first chain, year, start). It is turned into hourly values with the observed 2023
    diurnal shape of hot days (hourly maximum >= 27 C): s' = s^gamma with gamma solved so that the hourly mean equals tas, minimum tasmin and maximum tasmax;
    radiation = Haurwitz clear-sky shape scaled to the daily mean rsds (scale capped at the 99.9th percentile of the 2023 hourly ghi / clear-sky ratio), diffuse share from
    the 2023 clearness-index relation; relative humidity: constant dew point per day solved to match the daily mean hurs. The temperature and humidity of the first and
    last RAMP (6) rows of the window are blended linearly with the base series (no 10 K jump in one hour); radiation is not blended.
Run: cl/bin/python -I swiss/pipeline/build_climate.py [--percentile 95]
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd
from pvlib import location

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.models.pv import PARAMS  # noqa: E402
from swiss.pipeline.build_pv import pv_ac_w_per_kwp  # noqa: E402

RAW = os.path.join(ROOT, 'data', 'raw', 'ch2025_klo')
CAN = os.path.join(ROOT, 'data', 'canonical')
OUT = os.path.join(CAN, 'climate')
REPORT = os.path.join(ROOT, 'docs', 'experiments', 'validation_reports', 'climate_scenarios.md')
VARS = ('tas', 'tasmin', 'tasmax', 'rsds', 'hurs')
LEVELS = ('gwl1.5', 'gwl2.0', 'gwl3.0')
REF = 'ref91-20'
WINDOW = 7
HOT_DAY_C = 27.0                 # hourly maximum of a local day that counts as a hot day for the diurnal shape (assumption A-C5)
WEEK29 = (4872, 5039)            # rows of the 2023 hourly file = rl.window(29) (steps of the CityLearn year); checked in the tests
RAMP = 6                         # rows blended at each end of the inserted window (temperature, humidity)
SUMMER_START, SUMMER_LAST_START = 151, 236     # day indices (0 = 1 Jan, 365-day calendar): 1 June, and the last start so that the window ends on 31 August
MONTH_STARTS = np.cumsum([0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


# ------------------------------------------------------------------------------------------------ CH2025 reading
def read_ch2025(var, level, raw=RAW):
    """Daily ensemble array (30 model-years, 365 days, chains) and chain names. NA -> NaN. Header lines are skipped up to the line starting with DATE;."""
    f = os.path.join(raw, f'ogd-climate-scenarios-ch2025_klo_{var}_{level}.csv')
    lines = open(f, encoding='utf-8-sig').read().splitlines()
    i = [k for k, l in enumerate(lines) if l.startswith('DATE;')][0]
    chains = [c for c in lines[i].split(';')[1:] if c]
    rows = [l.split(';') for l in lines[i + 1:] if l.strip()]
    assert len(rows) == 30 * 365, (f, len(rows))
    A = np.array([[np.nan if x in ('NA', '') else float(x) for x in r[1:1 + len(chains)]] for r in rows])
    return A.reshape(30, 365, len(chains)), chains


def month_of_day_index():
    return np.concatenate([np.full(n, m + 1) for m, n in enumerate(np.diff(MONTH_STARTS))])


def ensemble(level, raw=RAW):
    return {v: read_ch2025(v, level, raw) for v in VARS}


def monthly_stat(ens, var, fn=np.nanmedian):
    Y, _ = ens[var]
    mon = month_of_day_index()
    return np.array([fn(Y[:, mon == m, :]) for m in range(1, 13)])


def monthly_deltas(ens_level, ens_ref):
    """Ensemble-median deltas of a level against the reference by month: additive for tas, tasmin, tasmax; ratios for rsds, hurs (medians, and the mean-based ratio for comparison)."""
    d = {}
    for v in ('tas', 'tasmin', 'tasmax'):
        d[v] = monthly_stat(ens_level, v) - monthly_stat(ens_ref, v)
    for v in ('rsds', 'hurs'):
        d[v] = monthly_stat(ens_level, v) / monthly_stat(ens_ref, v)
        d[v + '_mean_ratio'] = monthly_stat(ens_level, v, np.nanmean) / monthly_stat(ens_ref, v, np.nanmean)
    d['chains'] = {v: len(ens_level[v][1]) for v in VARS}
    return d


# ------------------------------------------------------------------------------------------------ 2023 weather helpers
def load_2023(path=None):
    w = pd.read_csv(path or os.path.join(CAN, 'weather_klo_2023_hourly.csv'), parse_dates=['timestamp_utc'])
    return w


def local_index(w):
    loc = pd.DatetimeIndex(w.timestamp_utc).tz_convert('Europe/Zurich')
    return loc


def clearsky_hourly(ts_utc):
    """Haurwitz clear-sky global irradiance, mean of the four 15-minute midpoints of every hour starting at ts_utc (as the 15-minute pipeline, A-022)."""
    lc = location.Location(PARAMS['latitude_deg'], PARAMS['longitude_deg'], altitude=PARAMS['altitude_m'])
    ts = pd.DatetimeIndex(ts_utc)
    acc = np.zeros(len(ts))
    for off in (7.5, 22.5, 37.5, 52.5):
        acc += lc.get_clearsky(ts + pd.Timedelta(minutes=off), model='haurwitz')['ghi'].to_numpy()
    return acc / 4.0


def day_positions(w):
    """Observed normalised diurnal position of every hour in its local calendar day, plus the day keys and hours."""
    loc = local_index(w)
    day = pd.Series(loc.date, index=w.index)
    t = w.temp_c
    mn, mx = t.groupby(day).transform('min'), t.groupby(day).transform('max')
    rng = (mx - mn).to_numpy()
    s = np.where(rng >= 1.0, (t.to_numpy() - mn.to_numpy()) / np.where(rng >= 1.0, rng, 1.0), 0.5)
    return s, np.asarray(day), loc.hour.to_numpy(), loc.month.to_numpy(), rng


def hot_day_shape(w):
    """Mean normalised diurnal curve (local hours 0..23, scaled to minimum 0 and maximum 1) over local days with an hourly maximum >= HOT_DAY_C."""
    s, day, hour, _, rng = day_positions(w)
    dmax = w.temp_c.groupby(day).transform('max').to_numpy()
    ok = (dmax >= HOT_DAY_C) & (rng >= 5.0)
    prof = np.array([s[ok & (hour == h)].mean() for h in range(24)])
    shape = (prof - prof.min()) / (prof.max() - prof.min())
    return shape, int(len(np.unique(day[ok])))


def diffuse_fraction_table(w, cs):
    """Median diffuse share of global radiation by clearness index kt = ghi / clear-sky (2023 daytime hours): bin edges and medians."""
    ghi = w.ghi_wm2.to_numpy(float)
    dif = w.diffuse_wm2.to_numpy(float)
    ok = (cs > 50) & ~np.isnan(dif)
    kt = ghi[ok] / cs[ok]
    f = np.clip(dif[ok] / np.maximum(ghi[ok], 1.0), 0.0, 1.0)
    edges = np.array([0.0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1.05, 5.0])
    med = np.array([np.median(f[(kt >= a) & (kt < b)]) if ((kt >= a) & (kt < b)).any() else np.nan for a, b in zip(edges[:-1], edges[1:])])
    med = pd.Series(med).ffill().bfill().to_numpy()
    return edges, med


def diffuse_fraction(kt, table):
    edges, med = table
    return med[np.clip(np.searchsorted(edges, kt, side='right') - 1, 0, len(med) - 1)]


# ------------------------------------------------------------------------------------------------ typical warmed year
def apply_deltas(w, d, cs):
    """Typical warmed year from the 2023 frame `w` and monthly deltas `d` (arrays of length 12). Zero deltas (additive) and unit ratios return `w` unchanged."""
    s, day, hour, month, rng = day_positions(w)
    m = month - 1
    sbar = np.array([s[month == k].mean() for k in range(1, 13)])
    dT = d['tas'][m] + (d['tasmax'][m] - d['tasmin'][m]) * (s - sbar[m])
    out = w.copy()
    out['temp_c'] = np.round(w.temp_c.to_numpy() + dT, 2)
    r = d['rsds'][m]
    ghi = w.ghi_wm2.to_numpy(float)
    cap = np.maximum(cs, ghi)
    fac = np.where(ghi > 0.0, np.minimum(r, cap / np.maximum(ghi, 1e-9)), r)
    fac = np.where(r == 1.0, 1.0, fac)
    out['ghi_wm2'] = np.round(ghi * fac, 1)
    out['diffuse_wm2'] = np.round(w.diffuse_wm2.to_numpy(float) * fac, 1)
    out['beam_horizontal_wm2'] = np.round(w.beam_horizontal_wm2.to_numpy(float) * fac, 1)
    out['rh_pct'] = np.round(np.minimum(w.rh_pct.to_numpy(float) * d['hurs'][m], 100.0), 1)
    return out, int(((r > 1.0) & (fac < r - 1e-9) & (ghi > 0.0)).sum())


# ------------------------------------------------------------------------------------------------ hot spells
def spell_distribution(ens):
    """Severity (mean tasmax of 7 consecutive days) of every valid window over chains common to the five variables; returns arrays aligned with the windows."""
    common = [c for c in ens['tasmax'][1] if all(c in ens[v][1] for v in VARS)]
    A = {v: ens[v][0][:, :, [ens[v][1].index(c) for c in common]] for v in VARS}
    n = len(common)
    valid_day = np.all([~np.isnan(A[v]) for v in VARS], axis=0)
    tmx = np.nan_to_num(A['tasmax'])
    cs = np.concatenate([np.zeros((30, 1, n)), np.cumsum(tmx, axis=1)], axis=1)
    cv = np.concatenate([np.zeros((30, 1, n)), np.cumsum(~valid_day, axis=1)], axis=1)
    sev = (cs[:, WINDOW:, :] - cs[:, :-WINDOW, :]) / WINDOW
    bad = (cv[:, WINDOW:, :] - cv[:, :-WINDOW, :]) > 0
    sev = np.where(bad, np.nan, sev)
    return sev, A, common


def select_spell(ens, percentile=95.0):
    sev, A, common = spell_distribution(ens)
    allv = sev[~np.isnan(sev)]
    target = float(np.percentile(allv, percentile))
    summer = sev[:, SUMMER_START:SUMMER_LAST_START + 1, :]
    dist = np.where(np.isnan(summer), np.inf, np.abs(summer - target))
    k = np.unravel_index(np.argmin(dist), dist.shape)      # first minimum in (year, start, chain) order: deterministic
    y, st, c = int(k[0]), int(k[1]) + SUMMER_START, int(k[2])
    days = {v: A[v][y, st:st + WINDOW, c].tolist() for v in VARS}
    mon = month_of_day_index()
    return {'chain': common[c], 'model_year': y + 1, 'start_day_index': st, 'start_date_365': f'{int(mon[st]):02d}-{st - MONTH_STARTS[mon[st] - 1] + 1:02d}',
            'severity_mean_tasmax': float(sev[y, st, c]), 'percentile': percentile, 'target_severity': target,
            'daily': days, 'n_windows': int(len(allv)), 'n_chains_common': len(common),
            'severity_quantiles_all_windows': {str(q): float(np.percentile(allv, q)) for q in (50, 90, 95, 99, 100)},
            'severity_quantiles_summer_windows': {str(q): float(np.nanpercentile(summer, q)) for q in (50, 90, 95, 99, 100)}}


def solve_gamma(shape, target_mean):
    lo, hi = 0.05, 20.0
    for _ in range(80):
        g = np.sqrt(lo * hi)
        if (shape ** g).mean() > target_mean:
            lo = g
        else:
            hi = g
    return np.sqrt(lo * hi)


def day_temperature(tmin, tmax, tas, shape_by_hour, hours):
    """24 hourly temperatures with the given minimum, maximum and mean from a normalised curve defined by local hour (s' = s^gamma)."""
    s = shape_by_hour[np.asarray(hours) % 24]
    m = float(np.clip((tas - tmin) / max(tmax - tmin, 1e-6), 0.05, 0.95))
    g = solve_gamma(np.clip(s, 1e-6, 1.0), m)
    return tmin + (tmax - tmin) * np.clip(s, 1e-6, 1.0) ** g


def magnus_rh(T, Td):
    a, b = 17.625, 243.04
    return np.clip(100.0 * np.exp(a * Td / (b + Td) - a * T / (b + T)), 0.0, 100.0)


def day_humidity(T, rh_mean):
    lo, hi = -40.0, float(T.max())
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if magnus_rh(T, mid).mean() < rh_mean:
            lo = mid
        else:
            hi = mid
    return magnus_rh(T, 0.5 * (lo + hi))


def insert_spell(base, spell, shape, cs_all, table, kmax, loc_hours):
    """Replace WEEK29 of `base` by the hourly spell. Returns the new frame and the statistics (capped scale days)."""
    a, b = WEEK29
    out = base.copy()
    for c in ('ghi_wm2', 'sunshine_min'):
        out[c] = out[c].astype(float)
    n = b - a + 1
    assert n == 7 * 24
    temp = np.zeros(n); rh = np.zeros(n); ghi = np.zeros(n); dif = np.zeros(n)
    capped = 0
    for i in range(7):
        sl = slice(24 * i, 24 * i + 24)
        hours = loc_hours[a + 24 * i: a + 24 * i + 24]
        tmin, tmax, tas = spell['daily']['tasmin'][i], spell['daily']['tasmax'][i], spell['daily']['tas'][i]
        T = day_temperature(tmin, tmax, tas, shape, hours)
        temp[sl] = T
        rh[sl] = day_humidity(T, min(spell['daily']['hurs'][i], 100.0))
        cs = cs_all[a + 24 * i: a + 24 * i + 24]
        k = spell['daily']['rsds'][i] * 24.0 / max(cs.sum(), 1e-9)
        if k > kmax:
            k, capped = kmax, capped + 1
        g = k * cs
        g = np.where(cs > 5.0, g, 0.0)
        kt = np.where(cs > 50.0, g / np.maximum(cs, 1e-9), 0.0)
        ghi[sl] = g
        dif[sl] = g * diffuse_fraction(kt, table)
    ramp = np.ones(n)
    ramp[:RAMP] = (np.arange(RAMP) + 1.0) / (RAMP + 1.0)
    ramp[-RAMP:] = ramp[:RAMP][::-1]
    idx = np.arange(a, b + 1)
    out.loc[idx, 'temp_c'] = np.round((1 - ramp) * base.temp_c.to_numpy()[idx] + ramp * temp, 2)
    out.loc[idx, 'rh_pct'] = np.round(np.minimum((1 - ramp) * base.rh_pct.to_numpy()[idx] + ramp * rh, 100.0), 1)
    out.loc[idx, 'ghi_wm2'] = np.round(ghi, 1)
    out.loc[idx, 'diffuse_wm2'] = np.round(dif, 1)
    out.loc[idx, 'beam_horizontal_wm2'] = np.round(ghi - dif, 1)
    out.loc[idx, 'sunshine_min'] = np.round(60.0 * np.minimum(1.0, ghi / np.maximum(cs_all[idx], 1.0))).astype(int) * (cs_all[idx] > 50)
    return out, capped


# ------------------------------------------------------------------------------------------------ validation helpers
def reconstruction_validation(w, shape):
    """Rebuild every observed local day of 2023 from its own hourly minimum, maximum and mean and a diurnal shape that does not contain that day (leave-one-day-out mean
    shape of the same month; for hot days (hourly max >= HOT_DAY_C) the hot-day shape without the day). RMSE and bias per month, in K."""
    s, day, hour, month, rng = day_positions(w)
    df = pd.DataFrame({'T': w.temp_c.to_numpy(), 'day': day, 'hour': hour, 'month': month, 's': s})
    g = df.groupby('day')
    dmin, dmax, dmean = g['T'].transform('min'), g['T'].transform('max'), g['T'].transform('mean')
    df['dmax'], df['range'] = dmax, (dmax - dmin)
    err_all, err_hot = [], []
    days = sorted(df.day.unique())
    prof_m = {m: df[(df.month == m) & (df.range >= 1.0)].groupby('hour').s.agg(['sum', 'count']) for m in range(1, 13)}
    hot_days = df[(df.dmax >= HOT_DAY_C) & (df.range >= 5.0)]
    prof_h = hot_days.groupby('hour').s.agg(['sum', 'count'])
    bias_by_month = {m: [] for m in range(1, 13)}
    for d in days:
        x = df[df.day == d]
        if len(x) != 24:
            continue
        m = int(x.month.iloc[0])
        t = x['T'].to_numpy()
        tmin, tmax, tas = t.min(), t.max(), t.mean()
        if tmax - tmin < 1.0:
            continue
        mine = x.set_index('hour').s
        pm = prof_m[m]
        use = (pm['sum'] - mine.reindex(pm.index).fillna(0)) / (pm['count'] - (x.range.iloc[0] >= 1.0))
        shp = use.reindex(range(24)).to_numpy()
        shp = (shp - np.nanmin(shp)) / (np.nanmax(shp) - np.nanmin(shp))
        rec = day_temperature(tmin, tmax, tas, shp, x.hour.to_numpy())
        e = rec - t
        err_all.append(e); bias_by_month[m].append(e.mean())
        if tmax >= HOT_DAY_C and tmax - tmin >= 5.0:
            ph = (prof_h['sum'] - mine.reindex(prof_h.index).fillna(0)) / (prof_h['count'] - 1)
            shp_h = ph.reindex(range(24)).to_numpy()
            shp_h = (shp_h - shp_h.min()) / (shp_h.max() - shp_h.min())
            err_hot.append(day_temperature(tmin, tmax, tas, shp_h, x.hour.to_numpy()) - t)
    allm = np.concatenate(err_all)
    return {'rmse_all_days_K': float(np.sqrt((allm ** 2).mean())), 'n_days_all': len(err_all),
            'rmse_hot_days_K': float(np.sqrt((np.concatenate(err_hot) ** 2).mean())), 'n_days_hot': len(err_hot),
            'monthly_bias_K': {m: float(np.mean(v)) for m, v in bias_by_month.items() if v}}


def scenario_stats(w):
    loc = local_index(w)
    t = w.temp_c
    day = pd.Series(loc.date, index=w.index)
    dmax = t.groupby(day).max()
    roll = t.rolling(168).mean()
    return {'monthly_mean_temp_c': t.groupby(loc.month).mean().round(2).tolist(), 'days_max_ge_30': int((dmax >= 30).sum()), 'days_max_ge_35': int((dmax >= 35).sum()),
            'hottest_week_mean_temp_c': float(roll.max()), 'week29_mean_temp_c': float(t.iloc[WEEK29[0]:WEEK29[1] + 1].mean()),
            'week29_max_temp_c': float(t.iloc[WEEK29[0]:WEEK29[1] + 1].max()), 'annual_mean_temp_c': float(t.mean()), 'annual_ghi_kwh_m2': float(w.ghi_wm2.clip(lower=0).sum() / 1000.0)}


def ensemble_stats(ens):
    mon = month_of_day_index()
    tas, tmax = ens['tas'][0], ens['tasmax'][0]
    mm = [float(np.nanmean(tas[:, mon == m, :])) for m in range(1, 13)]
    ge = lambda x: float(np.nanmean((np.nan_to_num(tmax, nan=-99) >= x).sum(axis=1)))   # days per model-year per chain   # noqa: E731
    roll = np.array([np.nanmax(np.convolve(tas[y, :, c], np.ones(7) / 7, mode='valid')) if not np.isnan(tas[y, :, c]).any() else np.nan for y in range(30) for c in range(tas.shape[2])])
    hu = ens['hurs'][0]
    return {'hurs_max': float(np.nanmax(hu)), 'hurs_share_gt_100': float(np.nanmean(hu > 100.0)), 'monthly_mean_tas_c': [round(x, 2) for x in mm], 'days_tasmax_ge_30': ge(30.0), 'days_tasmax_ge_35': ge(35.0),
            'hottest_7day_mean_tas_median_c': float(np.nanmedian(roll)), 'n_chains': tas.shape[2]}


# ------------------------------------------------------------------------------------------------ main
def build(percentile=95.0, out=OUT, raw=RAW, write=True):
    os.makedirs(out, exist_ok=True)
    w0 = load_2023()
    cs = clearsky_hourly(w0.timestamp_utc)
    loc_hours = local_index(w0).hour.to_numpy()
    shape, n_hot_days = hot_day_shape(w0)
    table = diffuse_fraction_table(w0, cs)
    ratio = w0.ghi_wm2.to_numpy(float)[cs > 300] / cs[cs > 300]
    kmax = float(np.percentile(ratio, 99.9))
    ens = {lv: ensemble(lv, raw) for lv in (REF,) + LEVELS}
    res = {'deltas': {}, 'spells': {}, 'scenario_stats': {'hist (2023)': scenario_stats(w0)}, 'ensemble_stats': {lv: ensemble_stats(ens[lv]) for lv in ens},
           'hot_day_shape': shape.round(4).tolist(), 'n_hot_days_2023': n_hot_days, 'kmax': kmax, 'capped_hours': {}, 'capped_spell_days': {},
           'diffuse_table': {'edges': table[0].tolist(), 'median': table[1].round(3).tolist()}, 'files': []}
    frames = {}
    for lv in LEVELS:
        d = monthly_deltas(ens[lv], ens[REF])
        res['deltas'][lv] = {k: (v.round(4).tolist() if isinstance(v, np.ndarray) else v) for k, v in d.items()}
        typical, capped = apply_deltas(w0, d, cs)
        res['capped_hours'][lv] = capped
        frames[lv] = typical
    spells = {}
    for suffix, pc in (('', percentile), ('99', 99.0)):                    # default spells (`_hw`) and a more extreme variant (`_hw99`)
        for key, lv in (('hist', REF), ('gwl2.0', 'gwl2.0'), ('gwl3.0', 'gwl3.0')):
            spells[key + suffix] = select_spell(ens[lv], pc)
            base = w0 if key == 'hist' else frames[key]
            frames[key + '_hw' + suffix], capped = insert_spell(base, spells[key + suffix], shape, cs, table, kmax, loc_hours)
            res['capped_spell_days'][key + '_hw' + suffix] = capped
    res['spells'] = spells
    res['reconstruction'] = reconstruction_validation(w0, shape)
    for name, f in frames.items():
        res['scenario_stats'][name] = scenario_stats(f)
    if write:
        for name, f in frames.items():
            f.to_csv(os.path.join(out, f'weather_klo_{name}_hourly.csv'), index=False)
            pv_df, y = pv_ac_w_per_kwp(f)
            pv_df.to_csv(os.path.join(out, f'pv_ac_w_per_kwp_{name}_hourly.csv'), index=False)
            res['files'].append(name)
            res['scenario_stats'][name]['annual_specific_pv_yield_kwh_kwp'] = float(y.sum())
        pv0, y0 = pv_ac_w_per_kwp(w0)
        res['scenario_stats']['hist (2023)']['annual_specific_pv_yield_kwh_kwp'] = float(y0.sum())
        json.dump({k: spells[k] | {'level': k} for k in spells} | {'rule': f'7-day windows, target = percentile {percentile} of mean tasmax over all valid windows of the ensemble, chosen among windows starting 1 June to 25 August, closest to the target',
                                                                  'inserted_rows': list(WEEK29), 'note': 'keys hist, gwl2.0, gwl3.0 = default percentile; keys with suffix 99 = percentile 99'}, open(os.path.join(out, 'heatwave_spells.json'), 'w'), indent=1)
        write_report(res, percentile)
    return res, frames


def write_report(res, percentile, path=REPORT):
    L = ['# Climate scenarios for Kloten (Phase C, WP1): construction and validation', '',
         'Generated by `swiss/pipeline/build_climate.py`; every number below comes from the script. Source: CH2025 DAILY-LOCAL for station KLO (MeteoSwiss & ETH Zurich 2025, CC BY 4.0), observed 2023 hourly series as the anchor. '
         '`hist` is the 2023 file itself.', '',
         '## Scenarios', '', '| Scenario | Content |', '|---|---|', '| hist | observed 2023 hourly weather (data/canonical/weather_klo_2023_hourly.csv) |']
    for lv in LEVELS:
        L.append(f'| {lv} | 2023 with monthly CH2025 ensemble-median deltas of {lv} against the 1991-2020 reference (typical warmed year) |')
    for sfx, pc in (('', f'{percentile:g}'), ('99', '99')):
        for k in ('hist', 'gwl2.0', 'gwl3.0'):
            L.append(f'| {k}_hw{sfx} | {"2023" if k == "hist" else k + " typical year"} with a 7-day hot spell (percentile {pc} rule) from the {"1991-2020 reference" if k == "hist" else k} ensemble in rows {WEEK29[0]} to {WEEK29[1]} (2023 test week 29) |')
    L += ['', f'## Monthly deltas used (ensemble medians; additive in K for temperature, ratio for radiation and humidity)', '']
    for lv in LEVELS:
        d = res['deltas'][lv]
        L += [f'### {lv} (chains: ' + ', '.join(f'{k} {v}' for k, v in d['chains'].items()) + ')', '', '| Month | dtas | dtasmin | dtasmax | rsds ratio | rsds ratio (mean-based, comparison) | hurs ratio |', '|---|---|---|---|---|---|---|']
        for m in range(12):
            L.append(f'| {m + 1} | {d["tas"][m]:+.2f} | {d["tasmin"][m]:+.2f} | {d["tasmax"][m]:+.2f} | {d["rsds"][m]:.3f} | {d["rsds_mean_ratio"][m]:.3f} | {d["hurs"][m]:.3f} |')
        L += ['', f'Hours where the radiation increase was limited by the clear-sky cap: {res["capped_hours"][lv]}.', '']
    L += ['## Chosen hot spells', '',
          f'Rule: windows of 7 consecutive days, severity = mean tasmax; target = percentile {percentile:g} (default `_hw` files) or 99 (`_hw99` files) of the severity over all valid windows of the ensemble; chosen = the window starting between 1 June and 25 August whose severity is closest to the target. '
          'Windows with any missing value in tas, tasmin, tasmax, rsds or hurs are excluded.', '',
          '| Level | Chain | Model-year | Start (MM-DD) | Severity (mean tasmax, C) | Target (C) | p50 / p90 / p95 / p99 all windows | p50 / p95 / p99 summer windows | windows | chains | rsds scale capped (days) |', '|---|---|---|---|---|---|---|---|---|---|---|']
    for k, s in res['spells'].items():
        q, qs = s['severity_quantiles_all_windows'], s['severity_quantiles_summer_windows']
        L.append(f'| {("1991-2020 reference" if k.startswith("hist") else k.replace("99", ""))}{" (p99)" if k.endswith("99") else ""} | {s["chain"]} | {s["model_year"]} | {s["start_date_365"]} | {s["severity_mean_tasmax"]:.1f} | {s["target_severity"]:.1f} | '
                 f'{q["50"]:.1f} / {q["90"]:.1f} / {q["95"]:.1f} / {q["99"]:.1f} | {qs["50"]:.1f} / {qs["95"]:.1f} / {qs["99"]:.1f} | {s["n_windows"]} | {s["n_chains_common"]} | {res["capped_spell_days"][k.replace("99", "") + "_hw" + ("99" if k.endswith("99") else "")]} |')
    L += ['', 'Daily values of the chosen spells (tasmin / tasmax / tas in C, rsds in W/m2, hurs in %):', '']
    for k, s in res['spells'].items():
        dd = s['daily']
        L.append(f'- **{k}**: ' + '; '.join(f'{dd["tasmin"][i]:.1f}/{dd["tasmax"][i]:.1f}/{dd["tas"][i]:.1f}, {dd["rsds"][i]:.0f}, {dd["hurs"][i]:.0f}' for i in range(7)))
    L += ['', '## Validation', '']
    r = res['reconstruction']
    L += [f'(a) **Daily-to-hourly reconstruction on 2023.** Every observed local day is rebuilt from its own hourly minimum, maximum and mean with a diurnal shape that does not contain that day: all days with a range of at least 1 K '
          f'({r["n_days_all"]} days, month-specific shape): RMSE {r["rmse_all_days_K"]:.2f} K; hot days (hourly maximum >= {HOT_DAY_C:g} C and range >= 5 K, {r["n_days_hot"]} days, hot-day shape): RMSE {r["rmse_hot_days_K"]:.2f} K. '
          'Monthly bias of the daily mean error (K): ' + ', '.join(f'{m}: {v:+.2f}' for m, v in r['monthly_bias_K'].items()) + '. '
          f'The hot-day shape comes from {res["n_hot_days_2023"]} observed days.', '',
          '(b) **Zero-delta identity** (tested in `swiss/tests/test_climate.py`): the construction with zero additive deltas and unit ratios returns the 2023 series unchanged; the reference level is not written as a file.', '',
          '(c) **Statistics per scenario** (hourly series of the scenario file, local calendar). Temperature extremes of CH2025 are daily extremes of 2 m temperature; the scenario files contain hourly means, so their hourly maxima are slightly lower than daily maxima (difference not quantified).', '',
          '| Scenario | Annual mean temp (C) | Days with hourly max >= 30 C | >= 35 C | Hottest 168 h mean temp (C) | Week 29 mean / max temp (C) | Annual GHI (kWh/m2) | PV yield (kWh/kWp) | Monthly mean temperature (C) |', '|---|---|---|---|---|---|---|---|---|']
    for k, s in res['scenario_stats'].items():
        L.append(f'| {k} | {s["annual_mean_temp_c"]:.2f} | {s["days_max_ge_30"]} | {s["days_max_ge_35"]} | {s["hottest_week_mean_temp_c"]:.1f} | {s["week29_mean_temp_c"]:.1f} / {s["week29_max_temp_c"]:.1f} | {s["annual_ghi_kwh_m2"]:.0f} | {s.get("annual_specific_pv_yield_kwh_per_kwp", s.get("annual_specific_pv_yield_kwh_kwp", float("nan"))):.0f} | ' + ', '.join(f'{x:.1f}' for x in s['monthly_mean_temp_c']) + ' |')
    L += ['', 'CH2025 ensemble statistics for comparison (per model-year and chain; tasmax >= 30 C counts daily maxima):', '',
          '| Level | chains (tas) | Days tasmax >= 30 C | >= 35 C | Median hottest 7-day mean tas (C) | hurs max (share > 100 %) | Monthly mean tas (C) |', '|---|---|---|---|---|---|---|']
    for lv, s in res['ensemble_stats'].items():
        L.append(f'| {lv} | {s["n_chains"]} | {s["days_tasmax_ge_30"]:.1f} | {s["days_tasmax_ge_35"]:.1f} | {s["hottest_7day_mean_tas_median_c"]:.1f} | {s["hurs_max"]:.1f} ({100 * s["hurs_share_gt_100"]:.2f} %) | ' + ', '.join(f'{x:.1f}' for x in s['monthly_mean_tas_c']) + ' |')
    L += ['', 'Climate ensemble values describe the model world of KLO bias-adjusted to 1991-2020 (the reference ensemble is not the same as the single year 2023, which was warmer than the 1991-2020 normal in several months); the scenario files are the 2023 year with the climate change signal added.', '',
          '## Limitations', '',
          '- One station (Kloten) and one weather year (2023) as the base; no interannual variability, no change in the frequency of weather types except in the inserted spell.',
          '- Delta change keeps the day-to-day and hourly sequence of 2023; the sub-daily cycle carries only the change of diurnal range; extremes outside the 2023 sequence are only represented by the inserted spell.',
          '- Spells are sequences of single model chains (bias-adjusted by quantile mapping, 1991-2020), made hourly by the documented shape method; the reference ensemble reaches daily maxima above 40 C at Kloten, so spells are chosen at a percentile, not by the maximum. Their radiation and humidity are consistent in daily mean only.',
          '- CH2025 radiation is global only: direct and diffuse follow the 2023 clearness-index relation and the Haurwitz clear-sky shape (A-022), not a measurement.',
          '- CH2025 daily extremes are treated as the extremes of the hourly series (hourly means are slightly less extreme).',
          '- Medians of daily radiation by month are used as in the proposal; the mean-based ratios in the delta tables show the difference.',
          '- CH2025 relative humidity contains values above 100 % (maximum in the table above, model output): the daily mean is capped at 100 % when a spell is made hourly, and scaled humidity is capped at 100 %.',
          f'- Radiation of the spells is limited to {res["kmax"]:.3f} times the Haurwitz clear-sky value (99.9th percentile of the 2023 hourly ratio, hours with clear-sky above 300 W/m2); the share of spell days affected is in the spell table.',
          '- Wind, precipitation and pressure are not used.', '']
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, 'w', encoding='utf-8').write('\n'.join(L))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--percentile', type=float, default=95.0)
    a = ap.parse_args(argv)
    res, _ = build(a.percentile)
    for k, s in res['spells'].items():
        print(f'spell {k}: {s["chain"]} year {s["model_year"]} from {s["start_date_365"]} severity {s["severity_mean_tasmax"]:.1f} (target {s["target_severity"]:.1f})')
    print('reconstruction', {k: (round(v, 3) if isinstance(v, float) else v) for k, v in res['reconstruction'].items() if k != 'monthly_bias_K'})
    for k, s in res['scenario_stats'].items():
        print(k, round(s['annual_mean_temp_c'], 2), s['days_max_ge_30'], s['days_max_ge_35'], round(s['hottest_week_mean_temp_c'], 1))


if __name__ == '__main__':
    main()
