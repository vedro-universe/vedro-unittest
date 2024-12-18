from pathlib import Path
from unittest.mock import Mock

import pytest
from baby_steps import given, then, when
from vedro.core import Config, Dispatcher, ScenarioResult
from vedro.events import ConfigLoadedEvent, ScenarioFailedEvent, ScenarioPassedEvent

from ._utils import dispatcher, make_vscenario, tmp_scn_dir, vedro_unittest

__all__ = ("dispatcher", "tmp_scn_dir",)  # fixtures


@pytest.mark.usefixtures(vedro_unittest.__name__)
async def test_register_scenario_loader(*, dispatcher: Dispatcher):
    with given:
        config_ = Mock(Config)
        event = ConfigLoadedEvent(Path("."), config_)

    with when:
        await dispatcher.fire(event)

    with then:
        assert config_.Registry.ScenarioLoader.register.assert_called_once() is None
        assert len(config_.mock_calls) == 1


@pytest.mark.usefixtures(vedro_unittest.__name__)
async def test_scenario_passed(*, dispatcher: Dispatcher, tmp_scn_dir: Path):
    with given:
        vscenario = make_vscenario(project_dir=tmp_scn_dir, expected_failure=None)
        scenario_result = ScenarioResult(vscenario)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert scenario_result.extra_details == []


@pytest.mark.usefixtures(vedro_unittest.__name__)
async def test_scenario_passed_with_expected_failure(*, dispatcher: Dispatcher, tmp_scn_dir: Path):
    with given:
        expected_failure = AssertionError()
        vscenario = make_vscenario(project_dir=tmp_scn_dir, expected_failure=expected_failure)
        scenario_result = ScenarioResult(vscenario)
        event = ScenarioPassedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert scenario_result.extra_details == [
            "Expected Failure: "
            f"Scenario passed because it failed as expected with {expected_failure!r}"
        ]


@pytest.mark.usefixtures(vedro_unittest.__name__)
async def test_scenario_failed(*, dispatcher: Dispatcher, tmp_scn_dir: Path):
    with given:
        vscenario = make_vscenario(project_dir=tmp_scn_dir, unexpected_success=False)
        scenario_result = ScenarioResult(vscenario)
        event = ScenarioFailedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert scenario_result.extra_details == []


@pytest.mark.usefixtures(vedro_unittest.__name__)
async def test_scenario_failed_with_unexpected_success(*, dispatcher: Dispatcher,
                                                       tmp_scn_dir: Path):
    with given:
        vscenario = make_vscenario(project_dir=tmp_scn_dir, unexpected_success=True)
        scenario_result = ScenarioResult(vscenario)
        event = ScenarioFailedEvent(scenario_result)

    with when:
        await dispatcher.fire(event)

    with then:
        assert scenario_result.extra_details == [
            "Unexpected Success: "
            "Scenario failed because it was expected to fail, but the scenario passed"
        ]
