import os
import sys
import unittest
from typing import Generator, List, Type, Union

from vedro.core import ConfigType, Dispatcher, Plugin, PluginConfig, VirtualScenario
from vedro.core.exc_info import TracebackFilter
from vedro.events import (
    ConfigLoadedEvent,
    ExceptionRaisedEvent,
    ScenarioFailedEvent,
    ScenarioPassedEvent,
)

from ._scenario_provider import UnitTestScenarioProvider

__all__ = ("VedroUnitTest", "VedroUnitTestPlugin",)

if sys.version_info < (3, 11):
    class ExceptionGroup(BaseException):
        exceptions: List[BaseException] = []


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
        self._global_config: Union[ConfigType, None] = None
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
        Handle the configuration loaded event to register the unittest scenario provider.

        :param event: The configuration loaded event containing the application config.
        """
        self._global_config = event.config
        scenario_collector = self._global_config.Registry.ScenarioCollector()
        scenario_collector.register_provider(UnitTestScenarioProvider(), self)

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
            assert self._global_config  # for type checker
            tb_filter_factory = self._global_config.Registry.TracebackFilter
            vedro_unittest_module = os.path.dirname(__file__)
            self._tb_filter = tb_filter_factory(modules=[unittest, vedro_unittest_module])

        for exc in self._yield_exceptions(event.exc_info.value):
            if tb := getattr(exc, "__traceback__", None):
                exc.__traceback__ = self._tb_filter.filter_tb(tb)

        event.exc_info.traceback = self._tb_filter.filter_tb(event.exc_info.traceback)

    def _yield_exceptions(self, exc: BaseException) -> Generator[BaseException, None, None]:
        """
        Recursively yield all exceptions in an ExceptionGroup, including nested ones.

        :param exc: A BaseException that may be an ExceptionGroup or a regular exception.
        :return: A generator of leaf exceptions.
        """
        if isinstance(exc, ExceptionGroup):
            for sub_exc in exc.exceptions:
                yield from self._yield_exceptions(sub_exc)
        else:
            yield exc

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
