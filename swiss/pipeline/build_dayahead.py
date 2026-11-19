"""Task B5 (step 9, part 2): Swiss day-ahead scenario tariff for 2023.
Input : data/raw/energy_charts/dayahead_ch_2023.json (SRC-012; Energy-Charts API /price?bzn=CH, EUR/MWh hourly, start-of-hour UTC;
        licence CC BY 4.0 'from Bundesnetzagentur | SMARD.de', stated in the API documentation, checked 2026-11-18; downloaded with the owner's approval D-041).
Output: data/canonical/dayahead_ch_2023_hourly.csv  (DER-018)  columns: da_eur_mwh, import_chf_kwh, export_chf_kwh
Scenario (labelled what-if, never a claim about current Swiss prices): a retail spot pass-through
    import_t = max(grid_standard_t + fx * DA_t / 1000 + adder, 0)    with adder chosen so the annual mean equals the S0 mean (revenue neutral: only the SHAPE differs)
    export_t = max(fx * DA_t / 1000, 0)                               market price of the exported energy
fx = 0.97 CHF per EUR (assumed 2023 average, unverified, A-021). Grid component = the EKZ standard two-tier grid fee of 2023 (DER-008).
Run: cl/bin/python -I swiss/pipeline/build_dayahead.py
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CAN = os.path.join(ROOT, 'data', 'canonical')
RAW = os.path.join(ROOT, 'data', 'raw', 'energy_charts', 'dayahead_ch_2023.json')
FX = 0.97


def main():
    d = json.load(open(RAW))
    ts = pd.to_datetime(d['unix_seconds'], unit='s', utc=True)
    da = pd.Series(d['price'], index=ts, dtype=float)
    base = pd.read_csv(os.path.join(CAN, 'tariff_ekz_standard_2023_hourly.csv'), parse_dates=['timestamp_utc']).set_index('timestamp_utc')
    assert (da.index == base.index).all() and da.notna().all()
    spot = FX * da / 1000.0                                            # CHF/kWh
    grid = base.grid_rp_kwh / 100.0
    raw = grid + spot
    adder = float(base.total_chf_kwh.mean() - raw.mean())
    imp = (raw + adder).clip(lower=0.0)
    # after the floor the mean moves slightly; one correction step keeps the annual mean equal to S0
    adder += float(base.total_chf_kwh.mean() - imp.mean())
    imp = (raw + adder).clip(lower=0.0)
    exp = spot.clip(lower=0.0)
    assert (exp <= imp + 1e-12).all()
    out = pd.DataFrame({'da_eur_mwh': da, 'import_chf_kwh': imp, 'export_chf_kwh': exp})
    out.to_csv(os.path.join(CAN, 'dayahead_ch_2023_hourly.csv'), index_label='timestamp_utc', float_format='%.6f')
    qc = {'hours': len(out), 'da_eur_mwh_mean': float(da.mean()), 'da_min': float(da.min()), 'da_max': float(da.max()), 'negative_hours': int((da < 0).sum()),
          'fx_chf_per_eur_assumed': FX, 'adder_chf_kwh': adder, 'import_rp_mean': float(imp.mean() * 100), 'import_rp_min': float(imp.min() * 100), 'import_rp_max': float(imp.max() * 100),
          'export_rp_mean': float(exp.mean() * 100), 'hours_import_floored_at_zero': int((raw + adder < 0).sum()), 's0_mean_rp': float(base.total_chf_kwh.mean() * 100),
          'licence': 'CC BY 4.0 from Bundesnetzagentur | SMARD.de (Energy-Charts API documentation)'}
    json.dump(qc, open(os.path.join(ROOT, 'docs', 'data', 'data_quality_reports', 'qc_dayahead_2023.json'), 'w'), indent=1)
    print(json.dumps(qc, indent=1))


if __name__ == '__main__':
    main()
