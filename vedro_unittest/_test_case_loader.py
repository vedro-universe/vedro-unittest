import os
import unittest
from concurrent.futures import ThreadPoolExecutor
from inspect import isclass
from pathlib import Path
from types import ModuleType
from typing import Any, List, Type, cast

from niltype import Nil
from vedro import Scenario, skip
from vedro.core import ModuleLoader, ScenarioLoader

from ._test_result import TestResult

__all__ = ("TestCaseLoader",)


class TestCaseLoader(ScenarioLoader):
    def __init__(self, module_loader: ModuleLoader) -> None:
        self._module_loader = module_loader

    async def load(self, path: Path) -> List[Type[Scenario]]:
        module = await self._module_loader.load(path)
        loaded = self._collect_scenarios(module)
        return loaded

    def _collect_scenarios(self, module: ModuleType) -> List[Type[Scenario]]:
        loaded = []
        for name, val in module.__dict__.items():
            if isclass(val) and issubclass(val, unittest.TestCase) and val != unittest.TestCase:
                scenarios = self._create_vedro_scenarios(val, module)
                loaded.extend(scenarios)
        return loaded

    def _extract_tests_from_suite(self, test_suite: unittest.TestSuite) -> List[unittest.TestCase]:
        tests = []
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                tests.extend(self._extract_tests_from_suite(test))
            elif isinstance(test, unittest.TestCase):
                tests.append(test)
            else:
                raise TypeError(f"Unsupported test type: {type(test)}")
        return tests

    def _create_vedro_scenarios(self, test_case: Type[unittest.TestCase],
                                module: ModuleType) -> List[Type[Scenario]]:
        test_loader = unittest.TestLoader()
        test_suite = test_loader.loadTestsFromTestCase(test_case)
        tests = self._extract_tests_from_suite(test_suite)

        scenarios = []
        for test in tests:
            scenario = self._create_vedro_scenario(test)
            scenario.__file__ = os.path.abspath(module.__file__)  # type: ignore
            scenarios.append(scenario)
        return scenarios

    def _create_vedro_scenario(self, test: unittest.TestCase) -> Type[Scenario]:
        def do(scn: Scenario) -> None:
            test_result = self._run_test(test)
            self._process_test_result(scenario, test_result)

        scenario = type(self._create_scenario_name(test), (Scenario,), {
            "subject": self._create_scenario_subject(test),
            "do": do,
        })

        if self._is_test_skipped(test):
            skip_reason = self._get_test_skip_reason(test)
            return skip(skip_reason)(scenario)
        return cast(Type[Scenario], scenario)

    def _create_scenario_subject(self, test: unittest.TestCase) -> str:
        class_name = test.__class__.__name__
        method_name = test._testMethodName
        return f"[{class_name}] {method_name.replace('_', ' ')}"

    def _create_scenario_name(self, test: unittest.TestCase) -> str:
        class_name = test.__class__.__name__
        method_name = test._testMethodName
        return f"Scenario__{class_name}__{method_name}"

    def _run_test(self, test: unittest.TestCase) -> TestResult:
        test_result = TestResult()
        if isinstance(test, unittest.IsolatedAsyncioTestCase):
            with ThreadPoolExecutor() as executor:
                executor.submit(test.run, test_result).result()
        else:
            test.run(test_result)
        return test_result

    def _process_test_result(self, scenario: Type[Scenario], test_result: TestResult) -> None:
        if test_result.vedro_unittest_exceptions:
            _, exception = test_result.vedro_unittest_exceptions[0]
            raise exception

        if test_result.vedro_unittest_expected_failures:
            _, expected_failure = test_result.vedro_unittest_expected_failures[0]
            setattr(scenario, "__vedro_unittest_expected_failure__", expected_failure)

        if test_result.vedro_unittest_unexpected_successes:
            _, unexpected_error = test_result.vedro_unittest_unexpected_successes[0]
            setattr(scenario, "__vedro_unittest_unexpected_success__", unexpected_error)
            raise unexpected_error

    def _is_test_skipped(self, test: unittest.TestCase) -> bool:
        return cast(bool, self._get_test_attr(test, "__unittest_skip__", False))

    def _get_test_skip_reason(self, test: unittest.TestCase) -> str:
        return cast(str, self._get_test_attr(test, "__unittest_skip_why__", ""))

    def _get_test_attr(self, test: unittest.TestCase, name: str, default: Any) -> Any:
        test_method_value = getattr(getattr(test, test._testMethodName), name, Nil)
        test_value = getattr(test, name, Nil)
        if test_method_value is not Nil:
            return test_method_value
        elif test_value is not Nil:
            return test_value
        else:
            return default
