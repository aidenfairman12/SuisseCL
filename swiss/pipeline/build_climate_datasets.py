"""Phase C (WP2): build the CityLearn dataset of a (climate scenario, cooling adoption) cell -> swiss/datasets/climate/<scenario>_<adoption>/ (regenerated on demand,
git-ignored like the q15 datasets). Every cell is an S3 district: assumed PV (ratio 1.0), assumed battery (1 kWh/kWp), the RC building model, plus cooling in the cooled
buildings. Scenario weather and PV files come from the WP1 pipeline (data/canonical/climate/); `hist` = the observed 2023 files; `*_hw99` = heat-wave week from the 99th-percentile spell (matrix), `*_hw` = 95th percentile (sensitivity).

Adoption (shares of the 46 dwelling units, labelled defaults, A-044):
  none = no cooling (heating-only district)       low = MFH-small (5 units, 10.9 %)      medium = MFH-medium (14 units, 30.4 %)
  high = MFH-large (24 units, 52.2 %)             high_alt = MFH-medium + MFH-small + the three houses (22 units, 47.8 %), a sensitivity to the building identity
Run: cl/bin/python -I swiss/pipeline/build_climate_datasets.py --scenario gwl3.0_hw99 --adoption high      or      --all  (matrix)  /  --all-extra
"""
import argparse
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, ROOT)
from swiss.citylearn_build import build_dataset  # noqa: E402

MATRIX_SCENARIOS = ('hist', 'hist_hw99', 'gwl2.0', 'gwl2.0_hw99', 'gwl3.0', 'gwl3.0_hw99')       # the Phase C matrix: observed 2023, typical warmed years, p99 heat-wave variants
EXTRA_SCENARIOS = ('gwl1.5', 'hist_hw', 'gwl2.0_hw', 'gwl3.0_hw')                                  # sensitivities: 1.5 C level and the p95 heat-wave variants
SCENARIOS = MATRIX_SCENARIOS + EXTRA_SCENARIOS
ADOPTION = {'none': (), 'low': ('MFH-small',), 'medium': ('MFH-medium',), 'high': ('MFH-large',),
            'high_alt': ('MFH-medium', 'MFH-small', 'SFH-low', 'SFH-mid', 'SFH-high')}
UNITS = {'SFH-low': 1, 'SFH-mid': 1, 'SFH-high': 1, 'MFH-small': 5, 'MFH-medium': 14, 'MFH-large': 24}
CARBON = os.path.join(ROOT, 'data', 'canonical', 'carbon_intensity_citylearn_2023.csv')


def unit_share(adoption):
    return sum(UNITS[r] for r in ADOPTION[adoption]) / float(sum(UNITS.values()))


def files(scenario):
    """(weather file, PV file) of a scenario; `hist` is the observed 2023 pair. Returns None if a scenario file does not exist yet."""
    if scenario == 'hist':
        return (os.path.join(ROOT, 'data', 'canonical', 'weather_klo_2023_hourly.csv'),
                os.path.join(ROOT, 'data', 'canonical', 'pv', 'pv_ac_w_per_kwp_2023_hourly.csv'))
    d = os.path.join(ROOT, 'data', 'canonical', 'climate')
    w, p = os.path.join(d, f'weather_klo_{scenario}_hourly.csv'), os.path.join(d, f'pv_ac_w_per_kwp_{scenario}_hourly.csv')
    return (w, p) if os.path.exists(w) and os.path.exists(p) else None


RU_FRACTION = 0.4                                  # archetype B default cooled fraction (assumption A-058, no source); sensitivity 0.2 and 0.6
RU_SENSITIVITY = ((('gwl3.0_hw99', 'high'), (0.2, 0.6)),)


def ru_suffix(fraction):
    """Cell-name suffix of archetype B: `_ru` for the default fraction, `_ru0.2` and `_ru0.6` for the sensitivities."""
    return '_ru' if abs(fraction - RU_FRACTION) < 1e-9 else f'_ru{fraction:g}'


def cell_name(scenario, adoption, fraction=None):
    return f'{scenario}_{adoption}' + ('' if fraction is None else ru_suffix(fraction))


def cell_dir(scenario, adoption, fraction=None):
    return os.path.join(ROOT, 'swiss', 'datasets', 'climate', cell_name(scenario, adoption, fraction))


def ru_cells():
    """(scenario, adoption, fraction) of every archetype B cell of the matrix: low, medium, high x the six scenarios at the default fraction + the two sensitivities."""
    out = [(s, a, RU_FRACTION) for s in MATRIX_SCENARIOS for a in ('low', 'medium', 'high')]
    for (s, a), fr in RU_SENSITIVITY:
        out += [(s, a, f) for f in fr]
    return out


def build_cell(scenario, adoption, quiet=True, fraction=None):
    f = files(scenario)
    if f is None:
        raise FileNotFoundError(f'scenario files for {scenario} not found in data/canonical/climate')
    out = f'climate/{cell_name(scenario, adoption, fraction)}'
    fr = 1.0 if fraction is None else fraction
    if quiet:
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            build_dataset.main(out_name=out, carbon_file=CARBON, pv_ratio=1.0, battery_kwh_per_kwp=1.0, rc=True, weather_file=f[0], pv_file=f[1],
                               cooled_buildings=ADOPTION[adoption], climate_scenario=scenario, cooled_fraction=fr)
    else:
        build_dataset.main(out_name=out, carbon_file=CARBON, pv_ratio=1.0, battery_kwh_per_kwp=1.0, rc=True, weather_file=f[0], pv_file=f[1],
                           cooled_buildings=ADOPTION[adoption], climate_scenario=scenario, cooled_fraction=fr)
    return cell_dir(scenario, adoption, fraction)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--scenario', choices=SCENARIOS)
    ap.add_argument('--adoption', choices=list(ADOPTION))
    ap.add_argument('--all', action='store_true', help='the matrix scenarios whose files exist x every adoption level')
    ap.add_argument('--all-extra', action='store_true', help='also the sensitivity scenarios (gwl1.5, p95 heat waves)')
    ap.add_argument('--fraction', type=float, default=None, help='archetype B (room units): cooled fraction of the floor area of the cooled buildings (cell name suffix _ru, _ru0.2, ...)')
    ap.add_argument('--all-ru', action='store_true', help='every archetype B cell of the matrix (18 at the default fraction + 2 sensitivities)')
    a = ap.parse_args()
    if a.all_ru:
        cells = ru_cells()
    else:
        cells = [(s, ad, a.fraction) for s in (SCENARIOS if a.all_extra else MATRIX_SCENARIOS) for ad in ADOPTION] if (a.all or a.all_extra) else [(a.scenario, a.adoption, a.fraction)]
    for s, ad, fr in cells:
        if files(s) is None:
            print(f'skip {cell_name(s, ad, fr)}: scenario files missing')
            continue
        print('built', build_cell(s, ad, fraction=fr))
