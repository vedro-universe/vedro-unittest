import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any, List, Type, cast

from niltype import Nil
from vedro import Scenario, skip
from vedro.core import ModuleLoader, ScenarioLoader

from ._test_result import TestResult
from ._utils import is_method_overridden

__all__ = ("TestCaseLoader",)


class TestCaseLoader(ScenarioLoader):
    def __init__(self, module_loader: ModuleLoader) -> None:
        self._module_loader = module_loader

    async def load(self, path: Path) -> List[Type[Scenario]]:
        module = await self._module_loader.load(path)
        # Register the loaded module in sys.modules so that unittest can discover setUpModule()
        sys.modules[module.__name__] = module
        return self._collect_scenarios(module)

    def _collect_scenarios(self, module: ModuleType) -> List[Type[Scenario]]:
        test_loader = unittest.TestLoader()
        test_suite = test_loader.loadTestsFromModule(module)

        if self._has_module_setup_or_teardown(module):
            return [self._create_vedro_scenario_for_module(test_suite, module)]

        loaded = []
        for suite in test_suite:
            if suite.countTestCases() == 0:
                continue

            first_test = self._get_first_test(suite)
            if self._has_class_setup_or_teardown(first_test):
                scenario = self._create_vedro_scenario_for_class(suite, module)
                loaded.append(scenario)
            else:
                for test in self._extract_tests_from_suite(suite):
                    scenario = self._create_vedro_scenario(test, module)
                    loaded.append(scenario)
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

    def _create_vedro_scenario_for_module(self, test_suite: unittest.TestSuite,
                                          module: ModuleType) -> Type[Scenario]:
        def do(scn: Scenario) -> None:
            self._process_test_result(scn.__class__, self._run_test(test_suite))

        first_test = self._get_first_test(test_suite)
        class_name = first_test.__class__.__name__
        scenario = type(f"Scenario__{class_name}", (Scenario,), {
            "__file__": os.path.abspath(str(module.__file__)),
            "subject": f"All tests in module '{module.__name__}'",
            "do": do,
        })

        return cast(Type[Scenario], scenario)

    def _create_vedro_scenario_for_class(self, test_suite: unittest.TestSuite,
                                         module: ModuleType) -> Type[Scenario]:
        def do(scn: Scenario) -> None:
            self._process_test_result(scn.__class__, self._run_test(test_suite))

        first_test = self._get_first_test(test_suite)
        class_name = first_test.__class__.__name__
        scenario = type(f"Scenario__{class_name}", (Scenario,), {
            "__file__": os.path.abspath(str(module.__file__)),
            "subject": f"All tests in class '{class_name}'",
            "do": do,
        })

        return cast(Type[Scenario], scenario)

    def _create_vedro_scenario(self, test_case: unittest.TestCase, module: ModuleType) -> Type[Scenario]:
        def do(scn: Scenario) -> None:
            self._process_test_result(scn.__class__, self._run_test(test_case))

        class_name = test_case.__class__.__name__
        method_name = test_case._testMethodName
        scenario = type(f"Scenario__{class_name}__{method_name}", (Scenario,), {
            "__file__": os.path.abspath(str(module.__file__)),
            "subject": f"[{class_name}] {method_name.replace('_', ' ')}",
            "do": do,
        })

        if self._is_test_skipped(test_case):
            skip_reason = self._get_test_skip_reason(test_case)
            return skip(skip_reason)(scenario)
        return cast(Type[Scenario], scenario)

    def _run_test(self, test: unittest.TestCase | unittest.TestSuite) -> TestResult:
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

    def _get_first_test(self, test_suite: unittest.TestSuite | unittest.TestCase) -> unittest.TestCase:
        if isinstance(test_suite, unittest.TestCase):
            return test_suite
        return self._get_first_test(next(iter(test_suite)))

    def _has_module_setup_or_teardown(self, module: ModuleType) -> bool:
        if getattr(module, "setUpModule", None):
            return True
        if getattr(module, "tearDownModule", None):
            return True
        return False

    def _has_class_setup_or_teardown(self, test_case: unittest.TestCase) -> bool:
        return (
            is_method_overridden("setUpClass", test_case, unittest.TestCase) or
            is_method_overridden("tearDownClass", test_case, unittest.TestCase)
        )

    def _is_test_skipped(self, test: unittest.TestCase) -> bool:
        return cast(bool, self._get_test_attr(test, "__unittest_skip__", False))

    def _get_test_skip_reason(self, test: unittest.TestCase) -> str:
        return cast(str, self._get_test_attr(test, "__unittest_skip_why__", ""))

    def _get_test_attr(self, test: unittest.TestCase, name: str, default: Any) -> Any:
        test_value = getattr(test, name, Nil)
        try:
            test_method = getattr(test, test._testMethodName)
        except AttributeError:
            test_method_value = Nil
        else:
            test_method_value = getattr(test_method, name, Nil)

        if test_method_value is not Nil:
            return test_method_value
        elif test_value is not Nil:
            return test_value
        else:
            return default
