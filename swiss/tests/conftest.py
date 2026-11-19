"""Shared test fixtures.

`swiss.experiments.rl` keeps the active scenario in module globals (SCENARIO, SCHEMA, PRICE, HIGH; set by `rl.use_scenario`). Several tests (and their module-scoped
fixtures) switch to scenario s3 or point `rl.SCHEMA` at a climate cell, which leaked into later test modules: the Phase B RL and oracle tests then read a PV dataset and
failed only in a full run, each passing alone. After every test module this fixture resets the module to its default scenario s0 (only if the module has been imported).
"""
import sys

import pytest


@pytest.fixture(autouse=True, scope='module')
def _reset_rl_scenario_after_module():
    yield
    rl = sys.modules.get('swiss.experiments.rl')
    if rl is not None:
        rl.use_scenario('s0')
