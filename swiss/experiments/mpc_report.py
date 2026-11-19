"""Summarise swiss/experiments/mpc_results/*.json per scenario against the reference (zero action / thermostat), the PV rule and the exact optimum on the held-out weeks.
Run: PYTHONPATH=. cl/bin/python swiss/experiments/mpc_report.py [s1|s2|s3]"""
import glob, json, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
R = os.path.join(ROOT, 'swiss', 'experiments', 'mpc_results')
sc = sys.argv[1] if len(sys.argv) > 1 else 's2'
ref = json.load(open(os.path.join(R, f'mpc_{sc}_perfect_H48_L0_tv1.json')))
zero, rule = ref['reference'], ref['pv_rule_r0.1']
ceil = json.load(open(os.path.join(ROOT, 'swiss', 'experiments', 'oracle_results', 'rl_reference.json')))['scenarios'][sc]['saving_pct']
pct = lambda c: 100 * (zero['cost_chf'] - c) / zero['cost_chf']
pctc = lambda c: 100 * (zero['cost_corrected_chf'] - c) / zero['cost_corrected_chf']
print(f'{sc}: reference bill {zero["cost_chf"]:.1f} CHF; exact optimum saves {ceil:.2f} % (test weeks)')
print(f'{"case":40s} {"saving raw %":>12s} {"corrected %":>12s} {"of ceiling":>10s} {"peak kW":>8s} {"wk peak":>8s} {"cold K.h":>8s}')
rows = [('PV rule r=0.1', rule)]
for f in sorted(glob.glob(os.path.join(R, f'mpc_{sc}_*.json'))):
    d = json.load(open(f))
    n = f'MPC {d["mode"]}' + (f' (true {"+".join(d["perfect_parts"])})' if d.get('perfect_parts') else '') + f' H{d["horizon"]}'
    n += (f' noise {d["level"]}' if d['mode'] == 'noisy' else '') + (f' peak w={d["peak_w"]:g}' if d.get('peak_w') else '') + (f' planner RC x{d["rc_perturb"]:g}' if d.get('rc_perturb', 1.0) != 1.0 else '') + (f' margin {d["rc_margin"]:g}' if d.get('rc_margin') else '') + (' +correction' if d.get('rc_correct') else '') + (f' STOCH K={d["scenarios"]}' + (f' err x{d["err_scale"]:g}' if d.get('err_scale', 1.0) != 1.0 else '') + (f' share {d["share"]}' if d.get('share', 1) != 1 else '') if d.get('scenarios', 1) > 1 else '')
    rows.append((n, d['mpc']))
for n, m in rows:
    print(f'{n:40s} {pct(m["cost_chf"]):12.2f} {pctc(m["cost_corrected_chf"]):12.2f} {100 * pct(m["cost_chf"]) / ceil:9.0f}% {m["highest_hour_kw"]:8.1f} {m["mean_weekly_peak_kw"]:8.1f} {m["comfort_cold_kh"]:8.1f}')
print(f'{"reference":40s} {0:12.2f} {0:12.2f} {0:9.0f}% {zero["highest_hour_kw"]:8.1f} {zero["mean_weekly_peak_kw"]:8.1f} {zero["comfort_cold_kh"]:8.1f}')
