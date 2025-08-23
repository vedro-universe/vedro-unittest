import os
from pathlib import Path
from typing import List, Optional

import pytest
from vedro import Scenario
from vedro.core import Dispatcher, ModuleFileLoader, Report, ScenarioSource, VirtualScenario
from vedro.core.scenario_discoverer import create_vscenario
from vedro.core.scenario_runner import MonotonicScenarioRunner as ScenarioRunner
from vedro.core.scenario_scheduler import MonotonicScenarioScheduler as ScenarioScheduler
from vedro.plugins.skipper import SkipperPlugin

from vedro_unittest import UnitTestScenarioProvider, VedroUnitTest, VedroUnitTestPlugin

__all__ = ("dispatcher", "vedro_unittest", "tmp_scn_dir", "provider", "run_scenarios",
           "make_vscenario", "create_scenario_source",)


@pytest.fixture
def dispatcher() -> Dispatcher:
    return Dispatcher()


@pytest.fixture
def vedro_unittest(dispatcher: Dispatcher) -> VedroUnitTestPlugin:
    plugin = VedroUnitTestPlugin(VedroUnitTest)
    plugin.subscribe(dispatcher)
    return plugin


@pytest.fixture()
def tmp_scn_dir(tmp_path: Path) -> Path:
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        scn_dir = tmp_path / "scenarios/"
        scn_dir.mkdir(exist_ok=True)
        yield scn_dir.relative_to(tmp_path)
    finally:
        os.chdir(cwd)


@pytest.fixture()
def provider() -> UnitTestScenarioProvider:
    return UnitTestScenarioProvider()


def create_scenario_source(path: Path, project_dir: Path) -> ScenarioSource:
    return ScenarioSource(path, project_dir, ModuleFileLoader())


async def run_scenarios(scenarios: List[VirtualScenario], dispatcher: Dispatcher) -> Report:
    # In test runs SkipperPlugin is not active, so apply manual skips here using scenario metadata
    for scenario in scenarios:
        if scenario.get_meta("skipped", plugin=SkipperPlugin, default=False):
            reason = scenario.get_meta("skip_reason", plugin=SkipperPlugin, default=None)
            scenario.skip(reason)

    scheduler = ScenarioScheduler(scenarios)

    runner = ScenarioRunner(dispatcher)
    report = await runner.run(scheduler)
    return report


def make_vscenario(*, project_dir: Path,
                   unexpected_success: bool = False,
                   expected_failure: Optional[BaseException] = None) -> VirtualScenario:
    class _Scenario(Scenario):
        pass

    if unexpected_success:
        setattr(_Scenario, "__vedro_unittest_unexpected_success__", unexpected_success)

    if expected_failure:
        setattr(_Scenario, "__vedro_unittest_expected_failure__", expected_failure)

    return create_vscenario(_Scenario, project_dir=project_dir)
