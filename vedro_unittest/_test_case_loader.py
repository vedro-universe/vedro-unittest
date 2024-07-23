import os
import unittest
from inspect import isclass
from pathlib import Path
from types import ModuleType, TracebackType
from typing import List, Tuple, Type, Union, cast

from vedro import Scenario, skip
from vedro.core import ModuleLoader, ScenarioLoader

__all__ = ("TestCaseLoader",)

ErrType = Tuple[Type[BaseException], BaseException, TracebackType]
ErrNoneType = Tuple[None, None, None]


class TestResult(unittest.TestResult):
    def _exc_info_to_string(self, err: Union[ErrType, ErrNoneType],
                            test: unittest.TestCase) -> str:
        if not hasattr(self, "_exceptions"):
            self._exceptions = []

        if err and err[0] is not None:
            self._exceptions.append(err)

        return super()._exc_info_to_string(err, test)  # type: ignore


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
            if isclass(val) and issubclass(val, unittest.TestCase):
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

            skip_reason: Union[str, None] = None
            if self._has_module_setup(module) or self._has_module_teardown(module):
                skip_reason = "Skipped because module has setUpModule or tearDownModule function"
            elif self._has_class_setup(test_case) or self._has_class_teardown(test_case):
                skip_reason = "Skipped because class has setUpClass or tearDownClass function"
            elif self._is_test_skipped(test):
                skip_reason = self._get_test_skip_reason(test)

            scenario = self._create_vedro_scenario(test, skip_reason)
            scenario.__file__ = os.path.abspath(module.__file__)  # type: ignore
            scenarios.append(scenario)
        return scenarios

    def _create_vedro_scenario(self, test: unittest.TestCase,
                               skip_reason: Union[str, None] = None) -> Type[Scenario]:
        class_name = test.__class__.__name__
        method_name = test._testMethodName

        scenario_subject = f"{method_name}"
        scenario_name = f"Scenario__{class_name}__{method_name}"

        def do(self: Scenario) -> None:
            test_result = TestResult()
            test.run(test_result)  # also runs setUp and tearDown

            exceptions = getattr(test_result, "_exceptions", [])
            for exc_type, exc_val, exc_tb in exceptions:
                raise exc_type(exc_val).with_traceback(exc_tb)

        scenario = type(scenario_name, (Scenario,), {
            "subject": scenario_subject,
            "do": do,
        })

        if skip_reason is not None:
            return skip(skip_reason)(scenario)
        return cast(Type[Scenario], scenario)

    def _is_test_skipped(self, test: unittest.TestCase) -> bool:
        return getattr(getattr(test, test._testMethodName), "__unittest_skip__", False)

    def _get_test_skip_reason(self, test: unittest.TestCase) -> str:
        return getattr(getattr(test, test._testMethodName), "__unittest_skip_why__", "")

    def _has_module_setup(self, module: ModuleType) -> bool:
        return hasattr(module, "setUpModule")

    def _has_module_teardown(self, module: ModuleType) -> bool:
        return hasattr(module, "tearDownModule")

    def _has_class_setup(self, test: Type[unittest.TestCase]) -> bool:
        return self._has_own_method(test, "setUpClass")

    def _has_class_teardown(self, test: Type[unittest.TestCase]) -> bool:
        return self._has_own_method(test, "tearDownClass")

    def _has_own_method(self, test: Type[unittest.TestCase], method_name: str) -> bool:
        for base in test.__mro__:
            if (base != unittest.TestCase) and (method_name in base.__dict__):
                return True
        return False
