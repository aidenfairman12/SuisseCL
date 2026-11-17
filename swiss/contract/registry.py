"""Phase-aware component and flow registry of contract v1 (components.json): what the energy-system diagram and the cutaway may draw.

Only status "modeled" components exist in the Phase A simulation. Future-phase components are listed with status
"not_modeled" so the UI can show them as "future phase" and never as operational (spec §7.2). Variables named here are the
exported variable ids (per building unless prefixed "district.").
"""


def comp(id_, label, category, description, phase, status, variables, provenance, source_ids, present_in='all six buildings'):
    return {'id': id_, 'label': label, 'category': category, 'description': description, 'phase_available': phase, 'status': status,
            'variables': variables, 'provenance': provenance, 'source_ids': source_ids, 'present_in': present_in, 'docs': []}


def flow(id_, a, b, carrier, variable, unit, description):
    return {'id': id_, 'from': a, 'to': b, 'carrier': carrier, 'variable': variable, 'unit': unit, 'description': description, 'status': 'modeled'}


COMPONENTS = [
    comp('grid', 'Electricity grid', 'grid', 'The only electricity source in Phase A. Everything the buildings use is bought from the grid; there is no PV, battery or local sharing.',
         'A', 'modeled', ['net_kwh_el'], 'modeled', ['D-018']),
    comp('weather', 'Weather', 'input', 'Outdoor temperature (and irradiance, not used by any Phase A device). An input, not an energy source.',
         'A', 'modeled', ['temp_c'], 'measured', ['SRC-004', 'DER-007']),
    comp('tariff', 'Electricity tariff', 'input', 'Two-tier EKZ standard tariff 2023 (excl. VAT). An input that prices grid electricity.',
         'A', 'modeled', ['price_chf_kwh', 'tariff_tier'], 'measured', ['DER-008', 'D-012']),
    comp('carbon', 'Grid carbon intensity', 'input', 'Modeled series; only the relative rank of an hour is exported. Used for relative emission comparisons, not for control.',
         'A', 'modeled', ['carbon_relative_rank'], 'modeled', ['DER-011', 'M-002', 'D-013b', 'ISS-033']),
    comp('controller', 'Controller', 'control', 'Decides when each tank charges or discharges. It cannot switch the heat pump or change the demand.',
         'A', 'modeled', ['sh_tank_action', 'hw_tank_action', 'sh_tank_mode', 'hw_tank_mode'], 'modeled', ['ALG-001', 'ALG-003', 'ALG-004']),
    comp('hp_sh', 'Heat pump (space heating)', 'conversion', 'Turns electricity into heat; the COP falls as it gets colder outside. Modeled with a Carnot-fraction COP (M-001).',
         'A', 'modeled', ['hp_sh_kwh_el', 'hp_sh_direct_kwh_th', 'hp_sh_to_tank_kwh_th', 'cop_sh'], 'modeled', ['M-001', 'D-014d']),
    comp('hp_hw', 'Heat pump (hot water and other base load)', 'conversion', 'Second heat-pump device for the warm-weather base load (hot water and other use, A-005).',
         'A', 'modeled', ['hp_hw_kwh_el', 'hp_hw_direct_kwh_th', 'hp_hw_to_tank_kwh_th', 'cop_hw'], 'modeled', ['M-001', 'A-005', 'D-014e']),
    comp('tank_sh', 'Heating tank', 'storage', 'Synthetic buffer tank (assumed size, efficiency and loss rate); the controller charges and discharges it.',
         'A', 'modeled', ['sh_tank_soc', 'sh_tank_loss_kwh_th'], 'assumed_parameter', ['D-017a', 'ISS-029', 'ISS-032']),
    comp('tank_hw', 'Hot-water / base-load tank', 'storage', 'Synthetic tank, only where the heat pump serves a base load of at least 3 kWh_th per day (D-017a).',
         'A', 'modeled', ['hw_tank_soc', 'hw_tank_loss_kwh_th'], 'assumed_parameter', ['D-017a', 'ISS-029', 'ISS-032'], 'five buildings (not SFH-low)'),
    comp('demand_sh', 'Space-heating demand', 'demand', 'Derived heat demand; always met. Indoor temperature and comfort are not modeled.',
         'A', 'modeled', ['sh_demand_kwh_th'], 'derived', ['M-001', 'DER-009', 'D-018']),
    comp('demand_hw', 'Hot-water / base-load demand', 'demand', 'Derived warm-weather baseline of heat-pump heat (hot water and other use).',
         'A', 'modeled', ['hw_demand_kwh_th'], 'derived', ['M-001', 'A-005', 'D-014e']),
    comp('household', 'Household electricity', 'demand', 'Non-heat-pump electricity. Metered for the houses (incl. electric water heaters of SFH-mid and SFH-high); synthetic for the apartment buildings.',
         'A', 'modeled', ['household_kwh_el'], {'SFH': 'measured', 'MFH': 'synthetic'}, ['SRC-001', 'SRC-002', 'D-015']),
    comp('district_outcomes', 'District outcomes', 'outcome', 'Totals over the six buildings: electricity, peak demand, cost, and relative emissions.',
         'A', 'modeled', ['district.net_kwh_el', 'district.cost_chf'], 'modeled', ['R-001']),
    comp('pv', 'Photovoltaics', 'future', 'Not part of Phase A.', 'B', 'not_modeled', [], 'modeled', ['ISS-021'], 'none'),
    comp('battery', 'Electrical battery', 'future', 'Not part of Phase A.', 'B', 'not_modeled', [], 'modeled', [], 'none'),
    comp('ev', 'Electric vehicle charging', 'future', 'Not part of Phase A (SFH-low probably has EV charging inside its household electricity, ISS-026).', 'B', 'not_modeled', [], 'modeled', ['ISS-026'], 'none'),
    comp('energy_community', 'Local energy community', 'future', 'Not part of Phase A. The six buildings share no grid connection in the model.', 'B', 'not_modeled', [], 'modeled', [], 'none'),
    comp('cooling', 'Cooling', 'future', 'Not part of Phase A (Phase C).', 'C', 'not_modeled', [], 'modeled', [], 'none'),
]

FLOWS = [
    flow('grid_hp_sh', 'grid', 'hp_sh', 'electricity', 'hp_sh_kwh_el', 'kWh_el', 'Electricity bought for the space-heating heat pump.'),
    flow('grid_hp_hw', 'grid', 'hp_hw', 'electricity', 'hp_hw_kwh_el', 'kWh_el', 'Electricity bought for the base-load heat pump.'),
    flow('grid_household', 'grid', 'household', 'electricity', 'household_kwh_el', 'kWh_el', 'Electricity bought for household use.'),
    flow('grid_outcomes', 'grid', 'district_outcomes', 'electricity', 'district.net_kwh_el', 'kWh_el', 'District grid import.'),
    flow('hp_sh_demand', 'hp_sh', 'demand_sh', 'heat', 'hp_sh_direct_kwh_th', 'kWh_th', 'Heat delivered straight to the space-heating demand.'),
    flow('hp_sh_tank', 'hp_sh', 'tank_sh', 'heat', 'hp_sh_to_tank_kwh_th', 'kWh_th', 'Heat stored in the heating tank.'),
    flow('tank_sh_demand', 'tank_sh', 'demand_sh', 'heat', 'sh_tank_to_demand_kwh_th', 'kWh_th', 'Stored heat delivered to the space-heating demand.'),
    flow('hp_hw_demand', 'hp_hw', 'demand_hw', 'heat', 'hp_hw_direct_kwh_th', 'kWh_th', 'Heat delivered straight to the base-load demand.'),
    flow('hp_hw_tank', 'hp_hw', 'tank_hw', 'heat', 'hp_hw_to_tank_kwh_th', 'kWh_th', 'Heat stored in the hot-water/base-load tank.'),
    flow('tank_hw_demand', 'tank_hw', 'demand_hw', 'heat', 'hw_tank_to_demand_kwh_th', 'kWh_th', 'Stored heat delivered to the base-load demand.'),
    flow('weather_hp_sh', 'weather', 'hp_sh', 'signal', 'temp_c', '°C', 'Outdoor temperature sets the COP.'),
    flow('weather_hp_hw', 'weather', 'hp_hw', 'signal', 'temp_c', '°C', 'Outdoor temperature sets the COP.'),
    flow('tariff_controller', 'tariff', 'controller', 'signal', 'price_chf_kwh', 'CHF/kWh', 'Price and hour of day are observed by the tariff-timed controllers.'),
    flow('tariff_outcomes', 'tariff', 'district_outcomes', 'signal', 'price_chf_kwh', 'CHF/kWh', 'The tariff turns grid import into cost.'),
    flow('carbon_outcomes', 'carbon', 'district_outcomes', 'signal', 'carbon_relative_rank', 'percent rank', 'Carbon intensity turns grid import into a RELATIVE emission comparison.'),
    flow('controller_tank_sh', 'controller', 'tank_sh', 'control', 'sh_tank_action', 'fraction of tank capacity', 'Charge / discharge command.'),
    flow('controller_tank_hw', 'controller', 'tank_hw', 'control', 'hw_tank_action', 'fraction of tank capacity', 'Charge / discharge command.'),
]


def registry():
    comps = [dict(c) for c in COMPONENTS]
    for c in comps:
        c['inputs'] = [f['id'] for f in FLOWS if f['to'] == c['id']]
        c['outputs'] = [f['id'] for f in FLOWS if f['from'] == c['id']]
    return comps, FLOWS
