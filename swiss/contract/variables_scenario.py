"""Data dictionary of the scenario files of contract v1.1 (web/public/bundle/sim_scenarios/<scenario>/): Phase B (S3, 2023 weather) and Phase C (one climate cell).

Additive to v1 (variables.py is unchanged): the same fields as there for provenance, unit and quantity, with the variables the Phase A bundle does not have
(rooftop PV, battery, export, cooling, indoor temperature). The scenario files record only what the district view draws, which keeps a full year small.
Electricity balance of every building and every step (checked at export and in the tests):
    import - export + pv = household + hp_sh + hp_hw + hp_cool + battery_charge - battery_discharge          (all kWh_el per step, battery flows measured at the bus)
`hp_cool_kwh_el` is null (not zero) for a building without a cooling device; in a scenario without cooling it is null everywhere.
"""
from swiss.contract.variables import CT, E, HW_LABEL, SH_LABEL, ST, v  # noqa: F401

SIM = ['M-001', 'D-018']


def building_variables(cooling):
    nocool = 'building has no cooling device (or the scenario has no cooling)'
    return {
        'import_kwh_el': v('Electricity bought from the grid', 'kWh_el', E, 'electricity', 'modeled', 'Net grid draw of the building when positive (never negative).', SIM),
        'export_kwh_el': v('Electricity sent to the grid', 'kWh_el', E, 'electricity', 'modeled',
                           'Net grid feed-in of the building when it produces more than it uses and stores. Paid at the assumed export price (A-015).', SIM + ['A-015']),
        'pv_kwh_el': v('Rooftop solar generation', 'kWh_el', E, 'electricity', 'modeled',
                       'AC output of the ASSUMED rooftop array of the building (size and orientation are assumptions, not survey data): modeled from measured irradiance and temperature.',
                       ['M-003', 'A-047']),
        'household_kwh_el': v('Household electricity', 'kWh_el', E, 'electricity', {'SFH': 'measured', 'MFH': 'synthetic'},
                              'Non-shiftable load: everything except the heat pumps. SFH: metered; MFH: synthetic composite (D-015).', ['SRC-001', 'SRC-002', 'D-015']),
        'hp_sh_kwh_el': v(f'Heat-pump electricity, {SH_LABEL}', 'kWh_el', E, 'electricity', 'modeled', 'Space-heating heat pump (direct operation plus charging the heating tank).', SIM + ['M-005']),
        'hp_hw_kwh_el': v(f'Heat-pump electricity, {HW_LABEL}', 'kWh_el', E, 'electricity', 'modeled', 'Second heat-pump device (hot water and other base load).', SIM + ['A-005']),
        'hp_cool_kwh_el': v('Heat-pump electricity, cooling', 'kWh_el', E, 'electricity', 'modeled',
                            'Electricity of the reversible heat pump when it cools. Cooling demand, COP and adoption are assumptions; there is no measured cooling load.',
                            ['M-006', 'A-040', 'A-041', 'A-044'] if cooling else ['M-006'], nocool),
        'battery_charge_kwh_el': v('Battery charging', 'kWh_el', E, 'electricity', 'modeled', 'Electricity taken from the building bus to charge the ASSUMED battery (1 kWh per kWp of panels); conversion losses stay inside the battery.', ['M-004', 'A-016', 'A-017']),
        'battery_discharge_kwh_el': v('Battery discharging', 'kWh_el', E, 'electricity', 'modeled', 'Electricity delivered to the building bus by the battery.', ['M-004', 'A-016', 'A-017']),
        'battery_soc': v('Battery fill level', 'fraction 0-1', ST, 'electricity', 'modeled', 'Stored energy relative to the (assumed) battery capacity at the end of the step.', ['M-004', 'A-016']),
        'temp_in_c': v('Indoor temperature', '°C', ST, None, 'modeled',
                       'Single-node RC room model (M-005), pooled priors; area calibrated to the derived 2023 heat. Not measured. Uncooled buildings float when it is hot' if cooling else
                       'Single-node RC room model (M-005), pooled priors; area calibrated to the derived 2023 heat. Not measured.', ['M-005', 'A-018', 'A-019']),
    }


def district_variables(cooling):
    nocool = 'scenario without cooling'
    return {
        'import_kwh_el': v('District grid import', 'kWh_el', E, 'electricity', 'modeled', 'Sum of building imports (the buildings share no connection, so building flows are not netted).', SIM),
        'export_kwh_el': v('District export', 'kWh_el', E, 'electricity', 'modeled', 'Sum of building exports.', SIM + ['A-015']),
        'pv_kwh_el': v('District solar generation', 'kWh_el', E, 'electricity', 'modeled', 'Sum over buildings.', ['M-003']),
        'battery_charge_kwh_el': v('District battery charging', 'kWh_el', E, 'electricity', 'modeled', 'Sum over buildings.', ['M-004']),
        'battery_discharge_kwh_el': v('District battery discharging', 'kWh_el', E, 'electricity', 'modeled', 'Sum over buildings.', ['M-004']),
        'hp_cool_kwh_el': v('District cooling electricity', 'kWh_el', E, 'electricity', 'modeled', 'Sum over cooled buildings.', ['M-006'], nocool),
    }


def condition_variables(climate):
    temp_prov = 'modeled' if climate else 'measured'
    return {
        'temp_c': {'label': 'Outdoor temperature', 'unit': '°C', 'provenance': temp_prov,
                   'source_ids': ['SRC-004', 'DER-007'] + (['A-045'] if climate else []),
                   'description': ('Observed 2023 weather at Zurich/Kloten shifted to a +2 °C global warming level with an inserted heat-wave week (CH2025 delta change): a modeled series.' if climate
                                   else 'MeteoSwiss Zurich/Kloten 2023, start-of-hour convention (D-009).')},
        'ghi_wm2': {'label': 'Global horizontal irradiance', 'unit': 'W/m²', 'provenance': temp_prov, 'source_ids': ['SRC-004', 'DER-007'], 'description': 'Direct plus diffuse irradiance used by the PV and room models.'},
        'price_chf_kwh': {'label': 'Electricity tariff', 'unit': 'CHF/kWh', 'provenance': 'measured', 'source_ids': ['DER-008', 'D-012'], 'description': 'EKZ standard two-tier tariff 2023, excl. VAT (a price schedule).'},
        'tariff_tier': {'label': 'Tariff tier', 'unit': 'category', 'provenance': 'derived', 'source_ids': ['DER-008'], 'description': '"high" on weekdays 07:00-20:00 local, otherwise "low".'},
    }


TAGS = {
    'district_daily_peak': 'The hour with the highest electricity purchase of its day, all six buildings together.',
    'high_tariff': 'A high-tariff hour (weekdays, 07:00 to 20:00 local time).',
    'cold_hour': 'One of the coldest 10 % of hours of the year outdoors.',
    'district_exporting': 'The district sends at least {export_hour_kwh} kWh to the grid in this hour.',
}
