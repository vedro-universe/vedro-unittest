import inspect
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import ModuleType
from typing import Any, List, Tuple, Type, Union, cast
from unittest import IsolatedAsyncioTestCase, TestCase, TestLoader, TestSuite

from niltype import Nil
from vedro import Scenario, skip
from vedro.core import ModuleLoader, ScenarioLoader

from ._test_result import TestResult

__all__ = ("UnitTestLoader",)

if sys.version_info < (3, 11):
    ExceptionGroup = type("ExceptionGroup", (Exception,), {})


class UnitTestLoader(ScenarioLoader):
    """
    Loads unit test scenarios and converts them into Vedro-compatible scenarios.

    Handles the discovery and conversion of unittest-based tests within the Vedro framework.
    """
    def __init__(self, module_loader: ModuleLoader) -> None:
        """
        Initialize the UnitTestLoader with a module loader.

        :param module_loader: The loader responsible for loading Python modules.
        """
        self._module_loader = module_loader
        self._raise_as_exc_group = sys.version_info >= (3, 11)

    async def load(self, path: Path) -> List[Type[Scenario]]:
        """
        Load scenarios from a Python module located at the specified path.

        :param path: The path to the Python module to load.
        :return: A list of Vedro-compatible scenarios.
        """
        module = await self._module_loader.load(path)
        # Register the loaded module in sys.modules so that unittest can discover setUpModule()
        sys.modules[module.__name__] = module
        return self._collect_scenarios(module)

    def _collect_scenarios(self, module: ModuleType) -> List[Type[Scenario]]:
        """
        Collect test scenarios from a Python module.

        :param module: The loaded Python module.
        :return: A list of Vedro-compatible scenarios.
        """
        module_path = os.path.abspath(str(module.__file__))

        test_loader = TestLoader()
        test_suite = test_loader.loadTestsFromModule(module)

        if self._has_module_setup_or_teardown(module):
            scenario = self._build_vedro_scenario(
                test_suite,
                path=module_path,
                name="Scenario_UnitTestSuite",
                subject=f"All tests in module '{module.__name__}'"
            )
            return [scenario]

        loaded = []
        for suite in test_suite:
            if suite.countTestCases() == 0:
                continue

            first_test = self._get_first_test(suite)
            if self._has_class_setup_or_teardown(first_test):
                class_name = first_test.__class__.__name__
                scenario = self._build_vedro_scenario(
                    suite,
                    path=module_path,
                    name=f"Scenario_{class_name}",
                    subject=f"All tests in class '{class_name}'",
                )
                loaded.append(scenario)
            else:
                for test in self._extract_tests_from_suite(suite):
                    class_name, method_name = test.__class__.__name__, test._testMethodName
                    scenario = self._build_vedro_scenario(
                        test,
                        path=module_path,
                        name=f"Scenario_{class_name}_{method_name}",
                        subject=f"[{class_name}] {method_name.replace('_', ' ')}",
                    )
                    loaded.append(scenario)
        return loaded

    def _extract_tests_from_suite(self, test_suite: Union[TestSuite, TestCase]) -> List[TestCase]:
        """
        Extract individual test cases from a test suite.

        :param test_suite: The test suite or test case to extract from.
        :return: A list of test cases.
        :raises TypeError: If an unsupported test type is encountered.
        """
        if isinstance(test_suite, TestCase):
            return [test_suite]

        tests = []
        for test in test_suite:
            if isinstance(test, TestSuite):
                tests.extend(self._extract_tests_from_suite(test))
            elif isinstance(test, TestCase):
                tests.append(test)
            else:
                raise TypeError(f"Unsupported test type: {type(test)}")
        return tests

    def _get_first_test(self, test_suite: Union[TestSuite, TestCase]) -> TestCase:
        """
        Get the first test case from a test suite.

        :param test_suite: The test suite or test case to examine.
        :return: The first test case found.
        """
        if isinstance(test_suite, TestCase):
            return test_suite
        return self._get_first_test(next(iter(test_suite)))

    def _build_vedro_scenario(self, test: Union[TestSuite, TestCase], *,
                              path: str, name: str, subject: str) -> Type[Scenario]:
        """
        Build a Vedro scenario from a unittest test or test suite.

        :param test: The test or test suite to wrap in a scenario.
        :param path: The file path of the test.
        :param name: The name of the scenario.
        :param subject: The subject description of the scenario.
        :return: A Vedro-compatible scenario type.
        """
        def do(scn: Scenario) -> None:
            test_result = self._run_test(test)
            self._process_test_result(scn.__class__, test_result)

        scenario = type(name, (Scenario,), {
            "__file__": path,
            "subject": subject,
            "do": do,
        })

        is_skipped, skip_reason = self._is_test_skipped(test)
        if is_skipped:
            return skip(skip_reason)(scenario)
        return cast(Type[Scenario], scenario)

    def _run_test(self, test: Union[TestSuite, TestCase]) -> TestResult:
        """
        Run a unittest test or test suite and capture its results.

        :param test: The test or test suite to run.
        :return: The results of running the test.
        """
        test_result = TestResult()
        if isinstance(test, IsolatedAsyncioTestCase):
            with ThreadPoolExecutor() as executor:
                executor.submit(test.run, test_result).result()
        else:
            test.run(test_result)
        return test_result

    def _process_test_result(self, scenario: Type[Scenario], test_result: TestResult) -> None:
        """
        Process the results of a test run and apply them to the scenario.

        :param scenario: The scenario type associated with the test.
        :param test_result: The results of the test run.
        :raises ExceptionGroup: If multiple exceptions are grouped (Python 3.11+).
        :raises BaseException: If a single exception occurred.
        :raises UnexpectedSuccessError: If a test unexpectedly succeeded.
        """
        if test_result.vedro_unittest_exceptions:
            if self._raise_as_exc_group and len(test_result.vedro_unittest_exceptions) > 1:
                exceptions = [cast(Exception, e) for _, e in test_result.vedro_unittest_exceptions]
                raise ExceptionGroup("Multiple Unittest Exceptions", exceptions)
            else:
                _, exception = test_result.vedro_unittest_exceptions[0]
                raise exception

        if test_result.vedro_unittest_expected_failures:
            _, expected_failure = test_result.vedro_unittest_expected_failures[0]
            setattr(scenario, "__vedro_unittest_expected_failure__", expected_failure)

        if test_result.vedro_unittest_unexpected_successes:
            _, unexpected_error = test_result.vedro_unittest_unexpected_successes[0]
            setattr(scenario, "__vedro_unittest_unexpected_success__", unexpected_error)
            raise unexpected_error

    def _has_module_setup_or_teardown(self, module: ModuleType) -> bool:
        """
        Check if a module has setup or teardown methods.

        :param module: The module to check.
        :return: True if the module has setup or teardown methods, otherwise False.
        """
        if getattr(module, "setUpModule", None):
            return True
        if getattr(module, "tearDownModule", None):
            return True
        return False

    def _has_class_setup_or_teardown(self, test_case: TestCase) -> bool:
        """
        Check if a test case's class has setup or teardown methods.

        :param test_case: The test case to check.
        :return: True if the class has setup or teardown methods, otherwise False.
        """
        return (
            self._is_method_overridden("setUpClass", test_case, TestCase) or
            self._is_method_overridden("tearDownClass", test_case, TestCase)
        )

    def _is_method_overridden(self, method_name: str, child_class: Any, parent_class: Any) -> bool:
        """
        Determine if a method is overridden in a subclass.

        :param method_name: The name of the method to check.
        :param child_class: The subclass to examine.
        :param parent_class: The parent class to compare against.
        :return: True if the method is overridden, otherwise False.
        """
        child_method = inspect.getattr_static(child_class, method_name, None)
        parent_method = inspect.getattr_static(parent_class, method_name, None)

        if (child_method is None) or (parent_method is None):
            return False

        return child_method is not parent_method

    def _is_test_skipped(self, test_suite: Union[TestSuite, TestCase]) -> Tuple[bool, str]:
        """
        Check if a test or test suite is marked as skipped.

        :param test_suite: The test or test suite to check.
        :return: A tuple indicating if the test is skipped and the reason.
        """
        if isinstance(test_suite, TestCase):
            is_skipped = self._get_test_attr(test_suite, "__unittest_skip__", False)
            skip_reason = self._get_test_attr(test_suite, "__unittest_skip_why__", "")
            return is_skipped, skip_reason

        tests = self._extract_tests_from_suite(test_suite)
        if not tests:
            return False, ""

        for test in tests:
            is_skipped = self._get_test_attr(test, "__unittest_skip__", False)
            if not is_skipped:
                return False, ""

        return True, "All tests are skipped"

    def _get_test_attr(self, test: TestCase, name: str, default: Any) -> Any:
        """
        Retrieve an attribute from a test case or its method.

        :param test: The test case to query.
        :param name: The name of the attribute to retrieve.
        :param default: The default value to return if the attribute is not found.
        :return: The value of the attribute, or the default value.
        """
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
