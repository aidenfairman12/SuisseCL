"""Data dictionary of contract v1: the single definition of every exported variable.

Field names carry their unit as a suffix (_kwh_el, _kwh_th, _chf, _soc, ...). `quantity` says what kind of number it is:
  energy_per_step  amount of energy in ONE simulation step. Mean power = value / (step_seconds / 3600). Never assume kWh == kW.
  state            level at the end of the step (0..1 for tank fill)
  ratio            dimensionless factor
  money            CHF per step (excl. VAT)
  control          controller output; mode is a category
`provenance`: measured | derived | modeled | synthetic | assumed_parameter (4 data classes + the assumed-parameter badge,
owner decision 2026-11-17). A dict {"SFH": ..., "MFH": ...} means the class depends on the building type.
`absent_when`: the variable is JSON null (not zeros) for a building without that component.
Naming: `hw` = "hot water and other heat-pump base load" (CityLearn's `dhw_*`; D-014e). Always show the `label`, not the id.
"""
from swiss.contract import CONTRACT_VERSION  # noqa: F401

E, ST, RT, MN, CT = 'energy_per_step', 'state', 'ratio', 'money', 'control'
SH_LABEL, HW_LABEL = 'space heating', 'hot water and other base load'


def v(label, unit, quantity, carrier, provenance, description, sources, absent_when=None):
    return {'label': label, 'unit': unit, 'quantity': quantity, 'carrier': carrier, 'provenance': provenance,
            'description': description, 'source_ids': sources, 'absent_when': absent_when}


SIM = ['M-001', 'D-018']
BUILDING_VARIABLES = {
    'hp_sh_kwh_el': v(f'Heat-pump electricity, {SH_LABEL}', 'kWh_el', E, 'electricity', 'modeled',
                      'Electricity drawn by the space-heating heat pump in this step (direct operation plus charging the heating tank). '
                      'Under "No control" it reproduces the derived series; under other controllers it is a simulation result.', SIM),
    'hp_hw_kwh_el': v(f'Heat-pump electricity, {HW_LABEL}', 'kWh_el', E, 'electricity', 'modeled',
                      'Electricity of the second heat-pump device, which serves the warm-weather base load (hot water and other use; A-005).', SIM + ['A-005']),
    'household_kwh_el': v('Household electricity', 'kWh_el', E, 'electricity', {'SFH': 'measured', 'MFH': 'synthetic'},
                          'Non-shiftable load: everything except the heat pump. SFH: metered (HEAPO); includes the electric water heater of SFH-mid and '
                          'SFH-high. MFH: synthetic composite of other EKZ apartments, NOT measured in these buildings (D-015).', ['SRC-001', 'SRC-002', 'D-014a', 'D-015']),
    'net_kwh_el': v('Electricity drawn from the grid', 'kWh_el', E, 'electricity', 'modeled',
                    'Heat pumps plus household electricity. No PV or battery in Phase A, so this is also the grid import and is never negative.', SIM),
    'cost_chf': v('Electricity cost', 'CHF', MN, None, 'derived', 'Grid import of the step times the tariff of the step (EKZ standard 2023, excl. VAT).', ['DER-008', 'D-012']),
    'sh_demand_kwh_th': v(f'Heat demand, {SH_LABEL}', 'kWh_th', E, 'heat', 'derived',
                          'Derived from measured heat-pump electricity times a modeled COP (M-001). Heat timing is unvalidated (ISS-028, ISS-030). Always met in the model.', ['M-001', 'DER-009']),
    'hw_demand_kwh_th': v(f'Heat demand, {HW_LABEL}', 'kWh_th', E, 'heat', 'derived',
                          'Warm-weather baseline of heat-pump electricity times COP. It may include uses other than hot water (SFH-high: ISS-027). '
                          'SFH-mid and SFH-high heat water electrically; that electricity is in household_kwh_el.', ['M-001', 'A-005', 'D-014e', 'ISS-027']),
}
for pre, lab in (('sh', SH_LABEL), ('hw', HW_LABEL)):
    tank = f'tank_{pre}'
    ab = 'no hot-water tank in this building' if pre == 'hw' else None
    BUILDING_VARIABLES.update({
        f'hp_{pre}_direct_kwh_th': v(f'Heat pump to demand, {lab}', 'kWh_th', E, 'heat', 'modeled',
                                      'Heat delivered by the heat pump straight to the demand.', SIM),
        f'hp_{pre}_to_tank_kwh_th': v(f'Heat pump to tank, {lab}', 'kWh_th', E, 'heat', 'modeled',
                                       'Heat the heat pump puts into the tank (before tank losses).', SIM + ['D-017a'], ab),
        f'{pre}_tank_to_demand_kwh_th': v(f'Tank to demand, {lab}', 'kWh_th', E, 'heat', 'modeled',
                                           'Stored heat delivered to the demand in this step.', SIM + ['D-017a'], ab),
        f'{pre}_tank_loss_kwh_th': v(f'Tank losses, {lab}', 'kWh_th', E, 'heat', 'modeled',
                                      'Heat lost in the tank (round-trip efficiency and standby loss) = into tank - out of tank - change in stored heat. '
                                      'Depends on assumed tank efficiency and loss rate (ISS-032).', SIM + ['D-017a', 'ISS-032'], ab),
        f'{pre}_tank_soc': v(f'Tank fill level, {lab}', 'fraction 0-1', ST, 'heat', 'modeled',
                              'Stored heat relative to the (assumed) tank capacity at the end of the step.', SIM + ['D-017a'], ab),
        f'{pre}_tank_action': v(f'Controller command, {lab} tank', 'fraction of tank capacity', CT, None, 'modeled',
                                 'Command passed to CityLearn: positive = charge, negative = discharge. It is NOT the executed flow (limits apply); '
                                 'use the *_to_tank and *_to_demand variables for what happened.', ['D-018'], ab),
        f'{pre}_tank_mode': v(f'Tank state, {lab}', 'category', CT, None, 'derived',
                              'charging | discharging | idle, from the executed flows (threshold in situation_thresholds.flow_epsilon_kwh_th).', ['D-018'], ab),
        f'cop_{pre}': v(f'Heat-pump COP, {lab}', 'ratio', RT, None, 'modeled',
                         'Carnot-fraction COP at the outdoor temperature of the step (M-001); eta calibrated to a literature SPF (D-014d).', ['M-001', 'D-014d']),
    })

DISTRICT_VARIABLES = {
    'net_kwh_el': v('District grid import', 'kWh_el', E, 'electricity', 'modeled', 'Sum of the six buildings (all non-negative in Phase A).', SIM),
    'hp_kwh_el': v('District heat-pump electricity', 'kWh_el', E, 'electricity', 'modeled', 'Both heat-pump devices of all buildings.', SIM),
    'household_kwh_el': v('District household electricity', 'kWh_el', E, 'electricity', 'modeled', 'Sum of household electricity (MFH part synthetic).', ['D-015']),
    'sh_demand_kwh_th': v(f'District heat demand, {SH_LABEL}', 'kWh_th', E, 'heat', 'derived', 'Sum over buildings.', ['M-001']),
    'hw_demand_kwh_th': v(f'District heat demand, {HW_LABEL}', 'kWh_th', E, 'heat', 'derived', 'Sum over buildings.', ['M-001', 'A-005']),
    'cost_chf': v('District electricity cost', 'CHF', MN, None, 'derived', 'Sum of building costs (excl. VAT).', ['DER-008']),
    'reward': v('Reward R-001', 'dimensionless', RT, None, 'modeled', 'Sum of the three parts below (carbon weight 0).', ['R-001', 'D-019']),
    'reward_cost': v('Reward part: cost', 'dimensionless', RT, None, 'modeled', 'Already weighted and scaled; negative = penalty.', ['R-001']),
    'reward_peak': v('Reward part: peak', 'dimensionless', RT, None, 'modeled', 'Squared district draw, weighted and scaled.', ['R-001']),
    'reward_ramp': v('Reward part: ramping', 'dimensionless', RT, None, 'modeled', 'Change of district draw, weighted and scaled.', ['R-001']),
}

CONDITION_VARIABLES = {
    'temp_c': {'label': 'Outdoor temperature', 'unit': '°C', 'provenance': 'measured', 'source_ids': ['SRC-004', 'DER-007'],
               'description': 'MeteoSwiss Zurich/Kloten, start-of-hour convention (D-009).'},
    'ghi_wm2': {'label': 'Global horizontal irradiance', 'unit': 'W/m²', 'provenance': 'measured', 'source_ids': ['SRC-004', 'DER-007'], 'description': 'MeteoSwiss Zurich/Kloten.'},
    'diffuse_wm2': {'label': 'Diffuse horizontal irradiance', 'unit': 'W/m²', 'provenance': 'measured', 'source_ids': ['SRC-004', 'DER-007'],
                    'description': 'One missing hour is set to 0 in the canonical file (see QC report).'},
    'beam_horizontal_wm2': {'label': 'Beam horizontal irradiance', 'unit': 'W/m²', 'provenance': 'derived', 'source_ids': ['DER-007'], 'description': 'ghi - diffuse.'},
    'price_chf_kwh': {'label': 'Electricity tariff', 'unit': 'CHF/kWh', 'provenance': 'measured', 'source_ids': ['DER-008', 'SRC-002', 'D-012'],
                      'description': 'Published EKZ standard two-tier tariff 2023, excl. VAT (a price schedule, not a metered quantity; the registry classifies it as measured).'},
    'tariff_tier': {'label': 'Tariff tier', 'unit': 'category', 'provenance': 'derived', 'source_ids': ['DER-008'], 'description': '"high" on weekdays 07:00-20:00 local, otherwise "low".'},
    'carbon_relative_rank': {'label': 'Grid carbon intensity, relative rank', 'unit': 'percent of the year\'s hours with lower intensity', 'provenance': 'modeled',
                             'source_ids': ['DER-011', 'M-002', 'SRC-011', 'D-013b', 'ISS-033'], 'relative_only': True,
                             'description': 'Rank of the hour inside the modeled 2023 series (1-99). The absolute level is about 61-63 % of the EPFL reference, so no absolute value is exported.'},
}

THRESHOLDS = {'tank_full_soc': 0.99, 'tank_empty_soc': 0.01, 'flow_epsilon_kwh_th': 1e-4, 'near_capacity_fraction': 0.95, 'storage_covers_demand_share': 0.5}

def _tank_tags(pre, name):
    pc = lambda x: f'{100 * x:.0f} %'  # noqa: E731
    return {
        f'{pre}_tank_charging': f'The {name} is being charged by the heat pump.',
        f'{pre}_tank_discharging': f'The {name} is supplying stored heat to the demand.',
        f'{pre}_tank_idle': f'The {name} is neither charging nor discharging.',
        f'{pre}_tank_full': f'The {name} is almost full ({pc(THRESHOLDS["tank_full_soc"])} or more).',
        f'{pre}_tank_empty': f'The {name} is almost empty ({pc(THRESHOLDS["tank_empty_soc"])} or less).',
        f'{pre}_tank_covers_demand': f'The {name} supplies at least {pc(THRESHOLDS["storage_covers_demand_share"])} of the heat demand it serves.',
    }


# User-facing wording (the dashboard shows these texts as they are): plain language, no field names; numbers come from THRESHOLDS.
SITUATION_TAGS = {
    'cold_hour': 'One of the coldest 10 % of hours of the year outdoors.',
    'high_tariff': 'A high-tariff hour (weekdays, 07:00 to 20:00 local time).',
    'low_tariff': 'A low-tariff hour.',
    'district_daily_peak': 'The hour with the highest electricity draw of its day, all six buildings together.',
    **_tank_tags('sh', 'heating tank'),
    **_tank_tags('hw', 'hot-water and base-load tank'),
    'hp_sh_near_capacity': f'The space-heating heat pump is running at {100 * THRESHOLDS["near_capacity_fraction"]:.0f} % or more of its nominal electrical power.',
}

UNITS = {
    'kWh_el': 'electrical energy in one step', 'kWh_th': 'thermal energy in one step',
    'CHF': 'Swiss francs excl. VAT', 'CHF/kWh': 'tariff', 'fraction 0-1': 'dimensionless fill level',
    'fraction of tank capacity': 'dimensionless command', 'ratio': 'dimensionless', '°C': 'degrees Celsius', 'W/m²': 'irradiance',
    'kW_el': 'mean electrical power over a step = kWh_el / (step_seconds / 3600)', 'kW_th': 'mean thermal power over a step = kWh_th / (step_seconds / 3600)',
}
