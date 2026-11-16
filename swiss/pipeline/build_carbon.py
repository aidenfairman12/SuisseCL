"""Task A6 / D-013: modeled hourly consumption-based LIFECYCLE carbon intensity of the Swiss electricity supply.

Inputs : data/raw/energy_charts/*.json (SRC-011, CC BY 4.0, attribution energy-charts.info):
         public_power for ch/de/fr/at/it (MW) and cbpf (cross-border physical flows into CH, GW; positive = import into CH,
         sign convention verified: July 2023 net export of 56 GWh/day equals ch 'Cross border electricity trading').
Method (first-order tracing, average not marginal intensity):
  I_dom,t = sum_k G_k,t EF_k / sum_k G_k,t                       (Swiss domestic generation only; diagnostic series)
  I_n,t   = same formula for neighbour n (FR, DE, AT, IT) from its own generation (its own imports ignored)
  I_cons,t = [sum_k G_k,t EF_k + sum_n max(F_n,t,0) * I_n,t] / [sum_k G_k,t + sum_n max(F_n,t,0)]
  Exports leave at the average mix (do not change the intensity). Pumped-storage generation and consumption are excluded.
Emission factors: IPCC AR5 WG3 Annex III Table A.III.2 lifecycle medians (verified from the PDF) with documented PROXIES
for technologies absent from that table (see EF_PROXY). Output unit gCO2eq/kWh (and kg/kWh for CityLearn).
No interpolation: hours with missing inputs stay NaN and are counted.
Run: cl/bin/python -I swiss/pipeline/build_carbon.py [2023|2016|2017]
"""
import glob
import json
import os
import sys

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW = os.path.join(ROOT, 'data', 'raw', 'energy_charts')
CAN = os.path.join(ROOT, 'data', 'canonical')
QCDIR = os.path.join(ROOT, 'docs', 'data', 'data_quality_reports')

# IPCC AR5 WG3 Annex III Table A.III.2, lifecycle MEDIAN (gCO2eq/kWh) - verified from the PDF
EF_IPCC = {'Nuclear': 12.0, 'Hydro Run-of-River': 24.0, 'Hydro water reservoir': 24.0, 'Biomass': 230.0,
           'Geothermal': 38.0, 'Wind onshore': 11.0, 'Wind offshore': 12.0, 'Fossil hard coal': 820.0, 'Fossil gas': 490.0}
SOLAR_CH, SOLAR_OTHER = 41.0, 48.0  # PV rooftop (CH, mostly rooftop - assumption) / PV utility (neighbours - assumption)
# NOT in the IPCC table -> PROXIES (assumptions A-006..A-009, sensitivity reported)
EF_PROXY = {'Fossil brown coal / lignite': 820.0,   # coal PC median; true lignite is higher -> underestimate
            'Fossil coal-derived gas': 820.0,       # coal PC median
            'Fossil oil': 820.0,                    # coal PC median (oil is lower in reality) -> overestimate
            'Waste': 230.0, 'Others': 230.0}        # biomass-dedicated median as stand-in
EXCLUDE = {'Hydro pumped storage', 'Hydro pumped storage consumption', 'Cross border electricity trading', 'Load',
           'Residual load', 'Renewable share of load', 'Renewable share of generation'}


def window(tag):
    if tag == '2023':
        return pd.Timestamp('2022-12-31 23:00', tz='UTC'), pd.Timestamp('2023-12-31 23:00', tz='UTC')
    y = int(tag)
    return pd.Timestamp(f'{y - 1}-12-31 23:00', tz='UTC'), pd.Timestamp(f'{y}-12-31 23:00', tz='UTC')


def load_power(country, start, end):
    frames = []
    for f in sorted(glob.glob(os.path.join(RAW, f'public_power_{country}_*.json'))):
        d = json.load(open(f))
        idx = pd.to_datetime(d['unix_seconds'], unit='s', utc=True)
        frames.append(pd.DataFrame({p['name']: p['data'] for p in d['production_types']}, index=idx))
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated()]
    df = df[(df.index >= start) & (df.index < end)]
    return df.resample('1h').mean()  # MW, start-of-hour label (API timestamps mark period start)


def load_flows(start, end):
    frames = []
    for f in sorted(glob.glob(os.path.join(RAW, 'cbpf_ch_*.json'))):
        d = json.load(open(f))
        idx = pd.to_datetime(d['unix_seconds'], unit='s', utc=True)
        frames.append(pd.DataFrame({c['name']: c['data'] for c in d['countries']}, index=idx))
    df = pd.concat(frames).sort_index()
    df = df[~df.index.duplicated()]
    df = df[(df.index >= start) & (df.index < end)]
    return df.resample('1h').mean() * 1000.0  # GW -> MW (hourly mean)


STRUCTURAL_RUN_H = 48  # NaN runs of at least this many hours = technology not reporting/operating (structural zero)


def structural_zero(series):
    isn = series.isna().to_numpy()
    out = series.copy()
    i = 0
    while i < len(isn):
        if isn[i]:
            j = i
            while j < len(isn) and isn[j]:
                j += 1
            if j - i >= STRUCTURAL_RUN_H:
                out.iloc[i:j] = 0.0
            i = j
        else:
            i += 1
    return out


def intensity(df, solar_ef, proxy_scale=1.0):
    ef = dict(EF_IPCC); ef.update({k: v * proxy_scale for k, v in EF_PROXY.items()}); ef['Solar'] = solar_ef
    # technologies that are entirely absent (all NaN for the whole window) are not part of that system's mix
    df = df.dropna(axis=1, how='all')
    df = df.apply(structural_zero)
    cols = [c for c in df.columns if c not in EXCLUDE and c in ef]
    unknown = [c for c in df.columns if c not in EXCLUDE and c not in ef]
    assert not unknown, f'unmapped technologies: {unknown}'
    g = df[cols].clip(lower=0)
    # NaN in any generation column makes the hour NaN (no interpolation)
    tot = g.sum(axis=1, min_count=len(cols))
    emis = (g * pd.Series(ef)[cols]).sum(axis=1, min_count=len(cols))
    return emis / tot, tot, emis


def build(tag, proxy_scale=1.0):
    start, end = window(tag)
    idx = pd.date_range(start, end, freq='1h', inclusive='left')
    ch = load_power('ch', start, end).reindex(idx)
    flows = load_flows(start, end).reindex(idx)
    i_dom, g_ch, e_ch = intensity(ch, SOLAR_CH, proxy_scale)
    nb_int, fill_flags = {}, {}
    for code, name in (('fr', 'France'), ('de', 'Germany'), ('at', 'Austria'), ('it', 'Italy')):
        p = load_power(code, start, end).reindex(idx)
        ser = intensity(p, SOLAR_OTHER, proxy_scale)[0]
        miss = ser.isna()
        fill_flags[name] = miss
        nb_int[name] = ser.fillna(ser.mean())  # FLAGGED fallback: neighbour annual mean intensity for hours with missing generation data
    imp = flows[['France', 'Germany', 'Austria', 'Italy']].clip(lower=0)
    nb = pd.DataFrame(nb_int)
    imp_emis = (imp * nb).sum(axis=1, min_count=4)
    imp_tot = imp.sum(axis=1, min_count=4)
    i_cons = (e_ch + imp_emis) / (g_ch + imp_tot)
    flag = pd.DataFrame(fill_flags).any(axis=1).astype(int)
    out = pd.DataFrame({'ci_consumption_lifecycle_g_per_kwh': i_cons, 'neighbour_intensity_fallback_flag': flag, 'ci_domestic_generation_lifecycle_g_per_kwh': i_dom,
                        'domestic_generation_excl_pumped_mwh': g_ch, 'imports_mwh': imp_tot,
                        'import_share': imp_tot / (g_ch + imp_tot)}, index=idx)
    for n in imp.columns:
        out[f'import_{n.lower()}_mwh'] = imp[n]
    return out, ch, flows


if __name__ == '__main__':
    tag = sys.argv[1] if len(sys.argv) > 1 else '2023'
    out, ch, flows = build(tag)
    # CityLearn input: kgCO2eq/kWh; the few hours with missing flow data (short gaps) are linearly interpolated AND flagged
    c0 = out.ci_consumption_lifecycle_g_per_kwh
    out['gap_interpolated_flag'] = c0.isna().astype(int)
    assert c0.isna().sum() <= 6, 'unexpectedly many missing carbon hours'
    out['carbon_intensity_kg_per_kwh'] = c0.interpolate(limit=6, limit_direction='both') / 1000.0
    out.index.name = 'timestamp_utc'
    out.to_csv(os.path.join(CAN, f'carbon_ch_{tag}_hourly.csv'))
    low, high = build(tag, 0.5)[0], build(tag, 1.5)[0]
    c = out.ci_consumption_lifecycle_g_per_kwh
    qc = {'tag': tag, 'rows': len(out), 'missing_consumption_hours': int(c.isna().sum()),
          'fallback_flagged_hours': int(out.neighbour_intensity_fallback_flag.sum()),
          'missing_domestic_hours': int(out.ci_domestic_generation_lifecycle_g_per_kwh.isna().sum()),
          'mean_consumption_g_kwh': float(c.mean()), 'mean_domestic_g_kwh': float(out.ci_domestic_generation_lifecycle_g_per_kwh.mean()),
          'min': float(c.min()), 'max': float(c.max()), 'p05': float(c.quantile(.05)), 'p95': float(c.quantile(.95)),
          'monthly_mean_g_kwh': c.resample('MS').mean().round(1).tolist(),
          'mean_by_local_hour': c.groupby(c.index.tz_convert('Europe/Zurich').hour).mean().round(1).tolist(),
          'import_share_mean': float(out.import_share.mean()),
          'annual_generation_twh': {k: float(ch[k].sum() / 1e6) for k in ch.columns if k not in EXCLUDE},
          'annual_net_flow_twh_positive_import': {k: float(flows[k].sum() / 1e6) for k in flows.columns},
          'proxy_sensitivity_mean_g_kwh': {'proxies_x0.5': float(low.ci_consumption_lifecycle_g_per_kwh.mean()),
                                           'reference': float(c.mean()), 'proxies_x1.5': float(high.ci_consumption_lifecycle_g_per_kwh.mean())}}
    json.dump(qc, open(os.path.join(QCDIR, f'qc_carbon_{tag}.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in qc.items() if k not in ('mean_by_local_hour',)}, indent=1))
