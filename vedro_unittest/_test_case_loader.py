import os
import unittest
from inspect import isclass
from pathlib import Path
from types import ModuleType
from typing import List, Type, TypeVar, Union, cast

from niltype import Nil
from vedro import Scenario, skip
from vedro.core import ModuleLoader, ScenarioLoader

__all__ = ("TestCaseLoader",)

T = TypeVar("T")


class UnexpectedSuccessError(AssertionError):
    pass


class TestCaseLoader(ScenarioLoader):
    def __init__(self, module_loader: ModuleLoader) -> None:
        self._module_loader = module_loader

    async def load(self, path: Path) -> List[Type[Scenario]]:
        module = await self._module_loader.load(path)
        loaded = self._collect_scenarios(module)
        return loaded

    def _collect_scenarios(self, module: ModuleType) -> List[Type[Scenario]]:
        loaded = []

        for name in module.__dict__:
            val = getattr(module, name)
            if isclass(val) and issubclass(val, unittest.TestCase) and val != unittest.TestCase:
                scenarios = self._create_vedro_scenarios(val, module)
                loaded.extend(scenarios)

        return loaded

    def _create_vedro_scenarios(self, test_case: Type[unittest.TestCase],
                                module: ModuleType) -> List[Type[Scenario]]:
        test_loader = unittest.TestLoader()
        test_suite = test_loader.loadTestsFromTestCase(test_case)

        scenarios = []
        for test in test_suite:
            if isinstance(test, unittest.TestSuite):
                raise ValueError("TestSuite is not supported")

            skip_reason = self._get_test_skip_reason(test) if self._is_test_skipped(test) else None
            is_failure_expected = self._is_test_expected_to_fail(test)

            scenario = self._create_vedro_scenario(test, skip_reason, is_failure_expected)
            scenario.__file__ = os.path.abspath(module.__file__)  # type: ignore
            scenarios.append(scenario)
        return scenarios

    def _create_vedro_scenario(self, test: unittest.TestCase,
                               skip_reason: Union[str, None] = None,
                               is_failure_expected: bool = False) -> Type[Scenario]:
        class_name = test.__class__.__name__
        method_name = test._testMethodName

        scenario_subject = f"{method_name}"
        scenario_name = f"Scenario__{class_name}__{method_name}"

        def do(self: Scenario) -> None:
            try:
                test.debug()
            except BaseException as e:
                if is_failure_expected:
                    setattr(scenario, "__vedro_unittest_expected_failure__", e)
                else:
                    raise
            else:
                if is_failure_expected:
                    setattr(scenario, "__vedro_unittest_unexpected_success__", True)
                    raise UnexpectedSuccessError("Scenario passed, but expected to fail")

        scenario = type(scenario_name, (Scenario,), {
            "subject": scenario_subject,
            "do": do,
        })

        if skip_reason is not None:
            return skip(skip_reason)(scenario)
        return cast(Type[Scenario], scenario)

    def _is_test_skipped(self, test: unittest.TestCase) -> bool:
        return self._get_test_attr(test, "__unittest_skip__", False)

    def _get_test_skip_reason(self, test: unittest.TestCase) -> str:
        return self._get_test_attr(test, "__unittest_skip_why__", "")

    def _is_test_expected_to_fail(self, test: unittest.TestCase) -> bool:
        return self._get_test_attr(test, "__unittest_expecting_failure__", False)

    def _get_test_attr(self, test: unittest.TestCase, name: str, default: T) -> T:
        test_method_value = getattr(getattr(test, test._testMethodName), name, Nil)
        test_value = getattr(test, name, Nil)
        if test_method_value is not Nil:
            return cast(T, test_method_value)
        elif test_value is not Nil:
            return cast(T, test_value)
        else:
            return default
