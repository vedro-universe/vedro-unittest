from typing import Type, Union

from vedro.core import Dispatcher, Plugin, PluginConfig, VirtualScenario
from vedro.events import ConfigLoadedEvent, ScenarioFailedEvent, ScenarioPassedEvent

from ._test_case_loader import TestCaseLoader

__all__ = ("VedroUnitTest", "VedroUnitTestPlugin",)


class VedroUnitTestPlugin(Plugin):
    def __init__(self, config: Type["VedroUnitTest"]) -> None:
        super().__init__(config)

    def subscribe(self, dispatcher: Dispatcher) -> None:
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
                  .listen(ScenarioPassedEvent, self.on_scenario_passed) \
                  .listen(ScenarioFailedEvent, self.on_scenario_failed)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        event.config.Registry.ScenarioLoader.register(  # pragma: no branch
            lambda: TestCaseLoader(module_loader=event.config.Registry.ModuleLoader()),
            self
        )

    def on_scenario_passed(self, event: ScenarioPassedEvent) -> None:
        scenario_result = event.scenario_result
        expected_failure = self._get_expected_failure(scenario_result.scenario)
        if expected_failure is not None:
            scenario_result.add_extra_details(
                "Expected Failure: "
                f"Scenario passed because it failed as expected with {expected_failure!r}"
            )

    def on_scenario_failed(self, event: ScenarioFailedEvent) -> None:
        scenario_result = event.scenario_result
        unexpected_success = self._get_unexpected_success(scenario_result.scenario)
        if unexpected_success is not None:
            scenario_result.add_extra_details(
                "Unexpected Success: "
                "Scenario failed because it was expected to fail, but the scenario passed"
            )

    def _get_expected_failure(self, scenario: VirtualScenario) -> Union[BaseException, None]:
        return getattr(scenario._orig_scenario, "__vedro_unittest_expected_failure__", None)

    def _get_unexpected_success(self, scenario: VirtualScenario) -> Union[bool, None]:
        return getattr(scenario._orig_scenario, "__vedro_unittest_unexpected_success__", None)


class VedroUnitTest(PluginConfig):
    plugin = VedroUnitTestPlugin
    description = "Allows running unittest test cases within the Vedro framework"
