"""System map of all three phases for the Overview diagram (bundle file system_map.json).

The data contract v1 (swiss/contract/registry.py) describes only the Phase A simulation by design. This module keeps that
contract unchanged and adds what Phases B and C model: assumed rooftop solar, a home battery, export, the building thermal
model (S3), EV charging and a local energy community (optimiser-only scenarios), warmed weather and cooling. Electricity
passes through one "building connection" node in every phase, so solar, battery, grid and loads meet in one place.

Every component and flow lists the phases it exists in. Text may differ by phase: a value is either a string (all phases)
or a dict keyed by phase. Source ids must be registry nodes (checked by the dashboard tests).
"""

PHASES = [
    {'id': 'A', 'label': 'Phase A', 'title': "Today's district",
     'summary': 'Heat pumps with heating and hot-water tanks; every unit of electricity comes from the grid. Observed weather, hour by hour over a year.'},
    {'id': 'B', 'label': 'Phase B', 'title': 'Solar, battery, building mass',
     'summary': 'A ladder of scenarios on the same year: assumed rooftop solar with an export price (S1), a home battery (S2), and a thermal model '
                'of each building with a comfort band (S3). EV charging and a local energy community were tested in the optimiser only.'},
    {'id': 'C', 'label': 'Phase C', 'title': 'Warmer climate and cooling',
     'summary': 'The S3 district in warmed and heat-wave weather from the Swiss climate scenarios, with cooling in some buildings: '
                'a central reversible heat pump or room units.'},
]
ALL, BC = ['A', 'B', 'C'], ['B', 'C']


def comp(id_, phases, label, description, provenance, sources, present_in='all six buildings', tag=None):
    return {'id': id_, 'phases': phases, 'label': label, 'description': description, 'provenance': provenance,
            'source_ids': sources, 'present_in': present_in, 'tag': tag}


def flow(id_, phases, a, b, carrier, description, both=False):
    return {'id': id_, 'phases': phases, 'from': a, 'to': b, 'carrier': carrier, 'description': description, 'both': both}


COMPONENTS = [
    # inputs and control
    comp('weather', ALL, 'Weather',
         {'A': 'Observed outdoor temperature at Zurich/Kloten; it sets how efficiently the heat pumps run.',
          'B': 'Observed temperature and sunshine: sunshine drives the solar panels, and in S3 temperature and sun drive each building\'s heat balance.',
          'C': 'Observed or warmed weather built from the Swiss climate scenarios, with or without an inserted heat wave. Drives heat pumps, solar output and each building\'s heat balance.'},
         {'A': 'measured', 'B': 'measured', 'C': 'modeled'}, {'A': ['SRC-004', 'DER-007'], 'B': ['SRC-004', 'DER-007'], 'C': ['SRC-014', 'DER-023', 'DER-025']}),
    comp('controller', ALL, 'Controller',
         {'A': 'Decides when the heating and hot-water tanks charge and discharge. Rule-based controllers and learning controllers were compared.',
          'B': 'Also runs the battery and, in S3, decides how much heat goes into the rooms within the comfort band. Compared: thermostat, solar rule, '
               'receding-horizon planner (MPC), exact optimum with perfect foresight and learning controllers.',
          'C': 'Also decides heating and cooling within the comfort band. Compared in every climate and cooling case: thermostat, solar rule, planner (MPC) and exact optimum.'},
         'modeled', {'A': ['ALG-001', 'ALG-003', 'ALG-004'], 'B': ['ALG-008', 'ALG-009', 'ALG-010', 'ALG-011'], 'C': ['ALG-012', 'ALG-013']}),
    comp('tariff', ALL, 'Electricity tariff',
         {'A': 'Two-tier EKZ standard tariff (excl. VAT); it prices grid electricity and is what the tariff-timed rules react to.',
          'B': 'The standard tariff plus an assumed price paid for exported solar; other tariff structures were tested as what-ifs.',
          'C': 'The standard tariff and the assumed export price, as in S3.'},
         {'A': 'measured', 'B': 'assumed_parameter', 'C': 'assumed_parameter'}, {'A': ['DER-008'], 'B': ['DER-008', 'A-015', 'D-034'], 'C': ['DER-008', 'A-015']}),
    comp('carbon', ALL, 'Grid carbon intensity',
         'Modeled hourly carbon intensity of Swiss grid electricity. Only how clean an hour is relative to the year is shown; it scores results and does not steer control.',
         'modeled', ['DER-011', 'M-002']),
    # supply
    comp('grid', ALL, 'Electricity grid',
         {'A': 'Supplies all electricity the buildings use; nothing is generated or stored on site.',
          'B': 'Supplies what solar and the battery do not cover and takes exported solar surplus at the assumed export price.',
          'C': 'Supplies what solar and the battery do not cover and takes exported solar surplus.'},
         'modeled', ['D-018']),
    comp('pv', BC, 'Rooftop solar',
         {'B': 'Assumed panels on every building (south, tilted), sized so a year\'s output roughly matches the building\'s electricity use and capped by the roof area. '
               'No real panels of these buildings are modeled.',
          'C': 'The Phase B panels, with output recomputed from each climate scenario\'s sunshine.'},
         'modeled', {'B': ['M-003', 'A-011', 'A-013', 'DER-012'], 'C': ['M-003', 'DER-024', 'A-047']}, tag={'B': 'assumed · from S1', 'C': 'assumed'}),
    comp('battery', BC, 'Home battery',
         'Assumed battery per building, sized by the kWh per kW of its solar panels, with a fixed round-trip efficiency.',
         'synthetic', ['M-004', 'A-016', 'A-017'], tag={'B': 'assumed · from S2', 'C': 'assumed'}),
    # connection
    comp('meter', ALL, 'Building connection',
         {'A': 'Where each building\'s grid electricity is metered. District results add up the six connections; the buildings share no grid connection.',
          'B': 'Balances solar, battery, grid and loads every hour; surplus solar is exported. Buildings share nothing here except in the energy-community scenario.',
          'C': 'Balances solar, battery, grid and loads every hour; surplus solar is exported.'},
         'modeled', ['DER-010', 'D-018']),
    comp('leg', ['B'], 'Local energy community',
         'Labelled scenario solved in the optimiser only: the six buildings share surplus solar at a discounted grid fee. They are a composite, not real neighbours.',
         'assumed_parameter', ['D-045', 'A-027', 'SRC-013'], present_in='the six buildings as one community (scenario)', tag='optimiser only'),
    # conversion and loads
    comp('hp_sh', ALL, {'A': 'Heat pump (space heating)', 'B': 'Heat pump (space heating)', 'C': 'Heat pump (heating and cooling)'},
         {'A': 'Turns electricity into heat; its efficiency (COP) falls as it gets colder outside.',
          'B': 'Turns electricity into heat; in S3 the controller decides how much heat goes into the rooms.',
          'C': 'Heats in winter. In cooled buildings the same reversible heat pump cools in summer (central system); the room-unit variant cools part of the floor area with separate units.'},
         'modeled', {'A': ['M-001'], 'B': ['M-001', 'M-005'], 'C': ['M-001', 'M-006', 'M-007', 'A-040', 'A-058']}, tag={'C': 'cooling from Phase C'}),
    comp('hp_hw', ALL, 'Heat pump (hot water)', 'Second heat-pump device for hot water and the other warm-weather base load.',
         'modeled', ['M-001', 'A-005']),
    comp('household', ALL, 'Household electricity',
         'Appliances, lighting and everything else that is not the heat pump. Metered for the houses; built from sampled apartment meters for the apartment buildings.',
         {'SFH': 'measured', 'MFH': 'synthetic'}, ['SRC-001', 'SRC-002', 'D-015']),
    comp('ev', ['B'], 'EV charging',
         'Labelled scenario solved in the optimiser only: two houses charge an electric car, with charging movable within an evening-to-morning window.',
         'derived', ['D-045', 'A-026', 'TR-017'], present_in='two houses (scenario)', tag='optimiser only'),
    # storage
    comp('tank_sh', ALL, 'Heating tank', 'Assumed buffer tank; the controller charges and discharges it.', 'assumed_parameter', ['D-017a', 'ISS-032']),
    comp('tank_hw', ALL, 'Hot-water tank', 'Assumed tank, only where the heat pump serves a hot-water load.', 'assumed_parameter', ['D-017a', 'ISS-032'],
         present_in='five buildings'),
    # demand
    comp('demand_sh', ALL, {'A': 'Space-heating demand', 'B': 'Space heating', 'C': 'Rooms and building mass'},
         {'A': 'Heat demand derived from measured heat-pump electricity. It is always met; indoor temperature is not modeled.',
          'B': 'S1 and S2 keep the derived demand. S3 replaces it with a thermal model of each building, so indoor temperature moves within a comfort band and the building itself stores heat.',
          'C': 'The S3 thermal model of each building: heated, and cooled where cooling is installed, within a comfort band. Uncooled buildings warm up in summer.'},
         {'A': 'derived', 'B': 'synthetic', 'C': 'synthetic'}, {'A': ['DER-009', 'M-001'], 'B': ['DER-009', 'M-005', 'A-020'], 'C': ['M-005', 'M-006', 'A-042', 'A-043']},
         tag={'B': 'thermal model in S3', 'C': 'thermal model'}),
    comp('demand_hw', ALL, 'Hot-water demand', 'Derived warm-weather baseline of heat-pump heat (hot water and other use).', 'derived', ['M-001', 'A-005']),
    # results
    comp('outcomes', ALL, 'District outcomes',
         {'A': 'Totals over the six buildings: electricity bought, the highest hour, the bill and relative emissions.',
          'B': 'Also export revenue, how much solar is used on site, and comfort in S3.',
          'C': 'Also cooling electricity, the share of it covered by solar, and hours above the comfort limit in uncooled buildings.'},
         'modeled', {'A': ['R-001'], 'B': ['R-001', 'D-036'], 'C': ['D-051', 'A-056']}),
]

FLOWS = [
    # electricity
    flow('grid_meter', ALL, 'grid', 'meter', 'electricity', {'A': 'Electricity bought from the grid.', 'B': 'Import, and export of solar surplus.', 'C': 'Import, and export of solar surplus.'},
         both={'A': False, 'B': True, 'C': True}),
    flow('pv_meter', BC, 'pv', 'meter', 'electricity', 'Solar output, used on site, stored or exported.'),
    flow('battery_meter', BC, 'battery', 'meter', 'electricity', 'Battery charging and discharging.', both=True),
    flow('meter_leg', ['B'], 'meter', 'leg', 'electricity', 'Surplus shared between the buildings of the community.', both=True),
    flow('meter_hp_sh', ALL, 'meter', 'hp_sh', 'electricity', {'A': 'Electricity for the space-heating heat pump.', 'B': 'Electricity for the space-heating heat pump.', 'C': 'Electricity for heating and, where installed, cooling.'}),
    flow('meter_hp_hw', ALL, 'meter', 'hp_hw', 'electricity', 'Electricity for the hot-water heat pump.'),
    flow('meter_household', ALL, 'meter', 'household', 'electricity', 'Electricity for household use.'),
    flow('meter_ev', ['B'], 'meter', 'ev', 'electricity', 'Electricity for charging the car.'),
    flow('meter_outcomes', ALL, 'meter', 'outcomes', 'electricity', 'Each building\'s grid exchange, summed for the district.'),
    # heat and cooling
    flow('hp_sh_tank', ALL, 'hp_sh', 'tank_sh', 'heat', 'Heat stored in the heating tank.'),
    flow('tank_sh_demand', ALL, 'tank_sh', 'demand_sh', 'heat', 'Stored heat delivered to the rooms.'),
    flow('hp_sh_demand', ALL, 'hp_sh', 'demand_sh', 'heat', 'Heat delivered straight to the rooms.'),
    flow('hp_sh_cooling', ['C'], 'hp_sh', 'demand_sh', 'cooling', 'Heat removed from the rooms of cooled buildings.'),
    flow('hp_hw_tank', ALL, 'hp_hw', 'tank_hw', 'heat', 'Heat stored in the hot-water tank.'),
    flow('tank_hw_demand', ALL, 'tank_hw', 'demand_hw', 'heat', 'Stored heat delivered to the hot-water demand.'),
    flow('hp_hw_demand', ALL, 'hp_hw', 'demand_hw', 'heat', 'Heat delivered straight to the hot-water demand.'),
    # input signals
    flow('weather_hp_sh', ALL, 'weather', 'hp_sh', 'signal', 'Outdoor temperature sets the COP.'),
    flow('weather_hp_hw', ALL, 'weather', 'hp_hw', 'signal', 'Outdoor temperature sets the COP.'),
    flow('weather_pv', BC, 'weather', 'pv', 'signal', 'Sunshine sets the solar output.'),
    flow('weather_demand_sh', BC, 'weather', 'demand_sh', 'signal', {'B': 'Outdoor temperature and sun drive the building\'s heat balance (S3).', 'C': 'Outdoor temperature and sun drive the building\'s heat balance.'}),
    flow('tariff_controller', ALL, 'tariff', 'controller', 'signal', 'Prices and the hour of day are what the tariff-timed controllers and the planners react to.'),
    flow('tariff_outcomes', ALL, 'tariff', 'outcomes', 'signal', {'A': 'The tariff turns grid import into a bill.', 'B': 'The tariff turns import into cost and export into revenue.', 'C': 'The tariff turns import into cost and export into revenue.'}),
    flow('carbon_outcomes', ALL, 'carbon', 'outcomes', 'signal', 'Carbon intensity turns grid import into a relative emission comparison.'),
    # control
    flow('controller_tank_sh', ALL, 'controller', 'tank_sh', 'control', 'Charge or discharge the heating tank.'),
    flow('controller_tank_hw', ALL, 'controller', 'tank_hw', 'control', 'Charge or discharge the hot-water tank.'),
    flow('controller_battery', BC, 'controller', 'battery', 'control', 'Charge or discharge the battery.'),
    flow('controller_hp_sh', BC, 'controller', 'hp_sh', 'control', {'B': 'How much heat goes into the rooms within the comfort band (S3).', 'C': 'How much to heat or cool within the comfort band.'}),
    flow('controller_ev', ['B'], 'controller', 'ev', 'control', 'When to charge inside the window (optimiser only).'),
]


def _at(v, phase):
    if isinstance(v, dict) and set(v) <= {'A', 'B', 'C'}:
        return v.get(phase)
    return v


def build():
    views = {}
    for p in PHASES:
        ph = p['id']
        comps = [{k: _at(v, ph) for k, v in c.items() if k != 'phases'} for c in COMPONENTS if ph in c['phases']]
        ids = {c['id'] for c in comps}
        flows = [{k: _at(v, ph) for k, v in f.items() if k != 'phases'} for f in FLOWS if ph in f['phases']]
        missing = [f['id'] for f in flows if f['from'] not in ids or f['to'] not in ids]
        if missing:
            raise ValueError(f'system_map: phase {ph} flows reference absent components: {missing}')
        views[ph] = {'components': comps, 'flows': flows}
    return {'phases': PHASES, 'views': views,
            'note': 'Phase A follows the simulation data contract; Phases B and C add the scenario models. Electricity passes through one building connection in every phase.'}
