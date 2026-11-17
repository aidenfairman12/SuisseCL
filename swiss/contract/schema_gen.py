"""Generate schema/*.schema.json (JSON Schema draft 2020-12, restricted keyword subset checked by validate.py).

The run schema's per-building properties are generated from variables.py, so schema and data dictionary cannot drift;
test_contract.py fails if the committed files differ from what this script produces.
Run: PYTHONPATH=. cl/bin/python -I swiss/contract/schema_gen.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from swiss.contract import CONTRACT_VERSION  # noqa: E402
from swiss.contract.variables import BUILDING_VARIABLES, CONDITION_VARIABLES, DISTRICT_VARIABLES  # noqa: E402

DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schema')
PROV = ['measured', 'derived', 'modeled', 'synthetic', 'assumed_parameter']
MODES = ['charging', 'discharging', 'idle']
S = {'type': 'string'}
INT = {'type': 'integer'}
NUM = {'type': 'number'}
BOOL = {'type': 'boolean'}
SERIES = {'type': 'array', 'items': NUM}
SERIES_GAPS = {'type': 'array', 'items': {'type': ['number', 'null']}}
SERIES_ABSENT = {'type': ['array', 'null'], 'items': NUM}
MODES_ABSENT = {'type': ['array', 'null'], 'items': {'enum': MODES}}
IDS = {'type': 'array', 'items': {'type': 'string', 'pattern': r'^[A-Za-z]+[-:][A-Za-z0-9._:\-]+$'}}
VERSION = {'const': CONTRACT_VERSION}
MECH_NUM = ['import_moved_out_of_high_tariff_kwh_el', 'extra_tank_loss_kwh_th', 'extra_hp_electricity_kwh_el', 'tank_heat_in_kwh_th', 'tank_heat_out_kwh_th',
            'stored_heat_change_kwh_th', 'tank_charging_electricity_kwh_el', 'electricity_avoided_at_discharge_kwh_el', 'electricity_from_tank_losses_kwh_el',
            'electricity_from_stored_remainder_kwh_el', 'electricity_from_cop_timing_kwh_el', 'cost_from_tariff_timing_chf', 'cost_from_extra_electricity_chf']


def obj(props, required=None, extra=False):
    return {'type': 'object', 'properties': props, 'required': list(props) if required is None else required, 'additionalProperties': extra}


def ref(name):
    return {'$ref': f'common.schema.json#/$defs/{name}'}


def schemas():
    out = {}
    out['common'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'SuisseCL contract v1: shared definitions', '$defs': {
        'provenance': {'enum': PROV},
        'provenanceOrByType': {'oneOf': [{'enum': PROV}, obj({'SFH': {'enum': PROV}, 'MFH': {'enum': PROV}})]},
        'buildingId': {'type': 'string', 'pattern': r'^(SFH|MFH)-[a-z]+$'},
        'ids': IDS,
        'attribute': obj({'value': {'type': ['number', 'string', 'boolean', 'null']}, 'unit': {'type': ['string', 'null']}, 'provenance': {'enum': PROV + [None]},
                          'source_ids': IDS, 'available': BOOL, 'unavailable_reason': {'type': ['string', 'null']}}),
        'variable': obj({'label': S, 'unit': S, 'quantity': {'enum': ['energy_per_step', 'state', 'ratio', 'money', 'control']},
                         'carrier': {'enum': ['electricity', 'heat', None]}, 'provenance': ref('provenanceOrByType'), 'description': S,
                         'source_ids': IDS, 'absent_when': {'type': ['string', 'null']}}),
        'scope': obj({'kind': {'enum': ['window', 'year']}, 'start_step': INT, 'n_steps': INT}),
    }}
    cond = {k: obj({'label': S, 'unit': S, 'provenance': {'enum': PROV}, 'source_ids': IDS, 'description': S, 'relative_only': BOOL}, ['label', 'unit', 'provenance', 'source_ids', 'description'])
            for k in CONDITION_VARIABLES}
    out['manifest'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'manifest.json',
        **obj({
            'contract_version': VERSION, 'phase': {'const': 'A'}, 'kind': {'enum': ['sample', 'full']},
            'description': S, 'district_note': S, 'year': INT, 'timezone': S, 'index_convention': S,
            'time_axis': obj({'start_utc': S, 'step_seconds': {'type': 'integer', 'minimum': 1}, 'n_steps_inputs': INT, 'n_steps_simulated': INT, 'scope': ref('scope')}),
            'buildings': {'type': 'array', 'items': ref('buildingId'), 'minItems': 1},
            'controllers': {'type': 'array', 'items': obj({'id': S, 'key': S, 'display_name': S, 'short_name': S, 'algorithm_id': S, 'reference': BOOL,
                                                           'identical_to': {'type': ['string', 'null']}, 'note': {'type': ['string', 'null']},
                                                           'parameters': {'type': 'object'}})},
            'scenarios': {'type': 'array', 'items': obj({'id': S, 'label': S, 'dataset': S, 'description': S})},
            'runs': {'type': 'array', 'items': obj({'scenario': S, 'controller': S, 'file': S})},
            'variables': obj({'building': {'type': 'object', 'additionalProperties': ref('variable')}, 'district': {'type': 'object', 'additionalProperties': ref('variable')},
                              'conditions': obj(cond, list(cond))}),
            'situation_tags': {'type': 'object', 'additionalProperties': S},
            'situation_thresholds': obj({'cold_temp_c': NUM, 'tank_full_soc': NUM, 'tank_empty_soc': NUM, 'flow_epsilon_kwh_th': NUM,
                                         'near_capacity_fraction': NUM, 'storage_covers_demand_share': NUM}),
            'units': {'type': 'object', 'additionalProperties': S},
            'checks': {'type': 'object'},
            'generated': obj({'git_commit': S, 'git_dirty': BOOL, 'python': S, 'citylearn': S}),
            'files': {'type': 'object', 'additionalProperties': {'type': 'string', 'pattern': r'^[0-9a-f]{64}$'}},
            'inputs': {'type': 'object', 'additionalProperties': {'type': 'string', 'pattern': r'^[0-9a-f]{64}$'}},
        })}
    comp = obj({'id': S, 'label': S, 'category': {'enum': ['grid', 'conversion', 'storage', 'demand', 'input', 'control', 'outcome', 'future']},
                'description': S, 'phase_available': {'enum': ['A', 'B', 'C']}, 'status': {'enum': ['modeled', 'not_modeled']},
                'inputs': {'type': 'array', 'items': S}, 'outputs': {'type': 'array', 'items': S}, 'variables': {'type': 'array', 'items': S},
                'provenance': ref('provenanceOrByType'), 'source_ids': IDS, 'present_in': {'type': 'string'}, 'docs': IDS})
    flow = obj({'id': S, 'from': S, 'to': S, 'carrier': {'enum': ['electricity', 'heat', 'signal', 'control']}, 'variable': {'type': ['string', 'null']},
                'unit': {'type': ['string', 'null']}, 'description': S, 'status': {'enum': ['modeled', 'not_modeled']}})
    out['components'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'components.json',
        **obj({'contract_version': VERSION, 'components': {'type': 'array', 'items': comp}, 'flows': {'type': 'array', 'items': flow}})}
    comp_attrs = {'type': 'object', 'additionalProperties': ref('attribute')}
    out['buildings'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'buildings.json',
        **obj({'contract_version': VERSION, 'buildings': {'type': 'object', 'additionalProperties': obj({
            'id': ref('buildingId'), 'citylearn_name': S, 'display_name': S, 'type': {'enum': ['SFH', 'MFH']}, 'source_dataset': S,
            'attributes': comp_attrs,
            'components': {'type': 'object', 'additionalProperties': obj({'present': BOOL, 'label': S, 'attributes': comp_attrs})},
            'related_ids': IDS})}})}
    out['conditions'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'conditions.json',
        **obj({'contract_version': VERSION, 'scope': ref('scope'), 'timestamps_utc': {'type': 'array', 'items': S},
               'local_time': {'type': 'array', 'items': S}, 'local_hour': {'type': 'array', 'items': INT}, 'weekday': {'type': 'array', 'items': INT},
               'series': obj({'temp_c': SERIES_GAPS, 'ghi_wm2': SERIES_GAPS, 'diffuse_wm2': SERIES_GAPS, 'beam_horizontal_wm2': SERIES_GAPS,
                              'price_chf_kwh': SERIES, 'tariff_tier': {'type': 'array', 'items': {'enum': ['low', 'high']}}, 'carbon_relative_rank': SERIES_GAPS}),
               'building_flags': {'type': 'object', 'additionalProperties': obj({'gap_filled': {'type': 'array', 'items': INT}})}})}
    bprops = {}
    for k, var in BUILDING_VARIABLES.items():
        if k.endswith('_tank_mode'):
            bprops[k] = MODES_ABSENT
        else:
            bprops[k] = SERIES_ABSENT if var['absent_when'] else SERIES
    dprops = {k: SERIES for k in DISTRICT_VARIABLES}
    tags = {'type': 'object', 'additionalProperties': {'type': 'array', 'items': INT}}
    metric = {'type': 'number'}
    out['run'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'runs/<scenario>/<controller>.json',
        **obj({'contract_version': VERSION, 'scenario': S, 'controller': S, 'algorithm_id': S, 'identical_to': {'type': ['string', 'null']},
               'experiment_ids': {'type': 'array', 'items': S}, 'seed': INT,
               'reward': obj({'id': S, 'weights': {'type': 'object'}, 'scales': {'type': 'object'}}),
               'scope': ref('scope'),
               'buildings': {'type': 'object', 'additionalProperties': obj(bprops, [k for k, var in BUILDING_VARIABLES.items()])},
               'district': obj(dprops),
               'situations': obj({'district': tags, 'buildings': {'type': 'object', 'additionalProperties': tags}}),
               'summary': obj({'import_kwh_el': metric, 'peak_kw_el': metric, 'peak_step': INT, 'mean_daily_peak_kw_el': metric, 'cost_chf': metric, 'high_tariff_import_share': metric,
                               'hp_kwh_el': metric, 'tank_loss_kwh_th': metric, 'heat_from_tanks_kwh_th': metric, 'reward_sum': metric})})}
    out['comparisons'] = {'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': 'comparisons.json',
        **obj({'contract_version': VERSION, 'scenario': S, 'reference_controller': S, 'scope': ref('scope'),
               'comparisons': {'type': 'object', 'additionalProperties': obj({
                   'metrics': {'type': 'object', 'additionalProperties': obj({'unit': S, 'value': metric, 'reference': metric, 'delta': metric, 'delta_pct': {'type': ['number', 'null']}})},
                   'mechanisms': obj({**{k: metric for k in MECH_NUM}, 'carbon_from_timing_pct': {'type': ['number', 'null']},
                                      'carbon_from_extra_electricity_pct': {'type': ['number', 'null']},
                                      'relative_carbon_change_pct': {'type': ['number', 'null']}, 'peak_step_reference': INT, 'peak_step': INT}),
                   'relative_only': {'type': 'array', 'items': S}})}})}
    return out


def render(obj_):
    return json.dumps(obj_, indent=1, ensure_ascii=False, sort_keys=False) + '\n'


def main():
    os.makedirs(DIR, exist_ok=True)
    for name, sch in schemas().items():
        with open(os.path.join(DIR, f'{name}.schema.json'), 'w', encoding='utf-8') as f:
            f.write(render(sch))
        print('wrote', f'schema/{name}.schema.json')


if __name__ == '__main__':
    main()
