import os
import unittest
from typing import Type, Union

from vedro.core import Dispatcher, Plugin, PluginConfig, VirtualScenario
from vedro.events import (
    ConfigLoadedEvent,
    ExceptionRaisedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
)
from vedro.plugins.director.rich.utils import TracebackFilter

from ._test_loader import UnitTestLoader

__all__ = ("VedroUnitTest", "VedroUnitTestPlugin",)


class VedroUnitTestPlugin(Plugin):
    """
    A plugin for integrating unittest test cases into the Vedro framework.

    Provides support for running unittest-based tests as Vedro scenarios, capturing
    expected failures, unexpected successes, and filtering traceback information.
    """
    def __init__(self, config: Type["VedroUnitTest"]) -> None:
        """
        Initialize the VedroUnitTestPlugin.

        :param config: The configuration class for the plugin.
        """
        super().__init__(config)
        self._show_internal_calls: bool = config.show_internal_calls
        self._tb_filter: Union[TracebackFilter, None] = None

    def subscribe(self, dispatcher: Dispatcher) -> None:
        """
        Subscribe to Vedro events for handling unittest scenarios.

        :param dispatcher: The event dispatcher to register listeners on.
        """
        dispatcher.listen(ConfigLoadedEvent, self.on_config_loaded) \
                  .listen(ScenarioPassedEvent, self.on_scenario_passed) \
                  .listen(ScenarioFailedEvent, self.on_scenario_failed) \
                  .listen(ExceptionRaisedEvent, self.on_exception_raised)

    def on_config_loaded(self, event: ConfigLoadedEvent) -> None:
        """
        Handle the configuration loaded event to register the unittest scenario loader.

        :param event: The configuration loaded event containing the application config.
        """
        event.config.Registry.ScenarioLoader.register(  # pragma: no branch
            lambda: UnitTestLoader(module_loader=event.config.Registry.ModuleLoader()),
            self
        )

    def on_scenario_passed(self, event: ScenarioPassedEvent) -> None:
        """
        Handle a scenario passed event to capture expected failure details.

        :param event: The scenario passed event containing scenario results.
        """
        scenario_result = event.scenario_result
        expected_failure = self._get_expected_failure(scenario_result.scenario)
        if expected_failure is not None:
            scenario_result.add_extra_details(
                "Expected Failure: "
                f"Scenario passed because it failed as expected with {expected_failure!r}"
            )

    def on_scenario_failed(self, event: ScenarioFailedEvent) -> None:
        """
        Handle a scenario failed event to capture unexpected success details.

        :param event: The scenario failed event containing scenario results.
        """
        scenario_result = event.scenario_result
        unexpected_success = self._get_unexpected_success(scenario_result.scenario)
        if unexpected_success is not None:
            scenario_result.add_extra_details(
                "Unexpected Success: "
                "Scenario failed because it was expected to fail, but the scenario passed"
            )

    def on_exception_raised(self, event: ExceptionRaisedEvent) -> None:
        """
        Handle an exception raised event to filter traceback information.

        :param event: The exception raised event containing exception details.
        """
        if self._show_internal_calls:
            return

        if self._tb_filter is None:
            vedro_unittest_module = os.path.dirname(__file__)
            self._tb_filter = TracebackFilter(modules=[unittest, vedro_unittest_module])

        event.exc_info.traceback = self._tb_filter.filter_tb(event.exc_info.traceback)

    def _get_expected_failure(self, scenario: VirtualScenario) -> Union[BaseException, None]:
        """
        Retrieve the expected failure exception from a scenario.

        :param scenario: The scenario to inspect.
        :return: The expected failure exception, or None if not applicable.
        """
        return getattr(scenario._orig_scenario, "__vedro_unittest_expected_failure__", None)

    def _get_unexpected_success(self, scenario: VirtualScenario) -> Union[BaseException, None]:
        """
        Retrieve the unexpected success exception from a scenario.

        :param scenario: The scenario to inspect.
        :return: The unexpected success exception, or None if not applicable.
        """
        return getattr(scenario._orig_scenario, "__vedro_unittest_unexpected_success__", None)


class VedroUnitTest(PluginConfig):
    """
    Configuration class for the VedroUnitTestPlugin.
    """
    plugin = VedroUnitTestPlugin
    description = "Allows running unittest test cases within the Vedro framework"

    # Show internal calls (unittest and vedro_unittest) in the traceback output
    show_internal_calls = False
