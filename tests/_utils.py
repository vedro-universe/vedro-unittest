import os
from pathlib import Path
from typing import List, Type

import pytest
from vedro import Scenario
from vedro.core import Dispatcher, ModuleFileLoader, Report, VirtualScenario
from vedro.core.scenario_discoverer import create_vscenario
from vedro.core.scenario_runner import MonotonicScenarioRunner as ScenarioRunner
from vedro.core.scenario_scheduler import MonotonicScenarioScheduler as ScenarioScheduler

from vedro_unittest import TestCaseLoader, VedroUnitTest, VedroUnitTestPlugin

__all__ = ("dispatcher", "vedro_unittest", "tmp_scn_dir", "loader", "run_test_cases",)


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
def loader() -> TestCaseLoader:
    return TestCaseLoader(ModuleFileLoader())


def _create_vscenario(test_case: Type[Scenario], *, project_dir: Path) -> VirtualScenario:
    vscenario = create_vscenario(test_case, project_dir=project_dir)
    if getattr(test_case, "__vedro__skipped__", False):
        reason = getattr(test_case, "__vedro__skip_reason__", None)
        vscenario.skip(reason)
    return vscenario


async def run_test_cases(test_cases: List[Type[Scenario]], dispatcher: Dispatcher, *,
                         project_dir: Path) -> Report:
    scenarios = [_create_vscenario(test_case, project_dir=project_dir) for test_case in test_cases]
    scheduler = ScenarioScheduler(scenarios)

    runner = ScenarioRunner(dispatcher)
    report = await runner.run(scheduler)
    return report
