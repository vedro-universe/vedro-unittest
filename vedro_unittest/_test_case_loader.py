import importlib
import importlib.util
import unittest
from importlib.abc import Loader
from importlib.machinery import ModuleSpec
from inspect import isclass
from pathlib import Path
from types import ModuleType
from types import TracebackType
from typing import List, Type, cast, Tuple

from vedro import Scenario
from vedro.core import ScenarioLoader

__all__ = ("TestCaseLoader",)


class TestResult(unittest.TestResult):
    def _exc_info_to_string(self, err: Tuple[Type[BaseException], BaseException, TracebackType],
                            test: unittest.TestCase) -> str:
        if not hasattr(self, "_exceptions"):
            self._exceptions = []
        self._exceptions.append(err)

        return super()._exc_info_to_string(err, test)


class TestCaseLoader(ScenarioLoader):
    async def load(self, path: Path) -> List[Type[Scenario]]:
        spec = self._spec_from_path(path)
        module = self._module_from_spec(spec)
        self._exec_module(cast(Loader, spec.loader), module)

        loaded = []
        for name in module.__dict__:
            if name.startswith("_"):
                continue
            val = getattr(module, name)

            if isclass(val) and issubclass(val, unittest.TestCase):
                scenarios = self._create_vedro_scenarios(val, module)
                loaded.extend(scenarios)

        return loaded

    def _create_vedro_scenarios(self, test_case: Type[unittest.TestCase],
                                module: ModuleType) -> List[Type[Scenario]]:
        test_loader = unittest.TestLoader()  # class variable
        test_suite = test_loader.loadTestsFromTestCase(test_case)

        scenarios = []
        for test in test_suite:
            scenario = self._create_vedro_scenario(test)
            scenario.__file__ = module.__file__  # backward compatibility
            scenarios.append(scenario)
        return scenarios

    def _create_vedro_scenario(self, test: unittest.TestCase) -> Type[Scenario]:
        scenario_subject = test._testMethodName
        scenario_name = f"Scenario__{test.__class__.__name__}__{scenario_subject}"

        def do(self_):
            test_result = TestResult()
            test.run(test_result)
            for exc_type, exc_val, exc_tb in getattr(test_result, "_exceptions", []):
                raise exc_val.with_traceback(exc_tb)

        scn = type(scenario_name, (Scenario,), {
            "subject": scenario_subject,
            "do": do,

            "__module__": test.__module__,
            "__doc__": test.__doc__,
        })
        return cast(Type[Scenario], scn)

    def _spec_from_path(self, path: Path) -> ModuleSpec:
        """
        Create a module specification from a file path.

        :param path: The file path for which to create the module spec.
        :return: The ModuleSpec for the given path.
        :raises ModuleNotFoundError: If no module specification can be created for the path.
        """
        module_name = self._path_to_module_name(path)
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None:
            raise ModuleNotFoundError(module_name)
        return spec

    def _path_to_module_name(self, path: Path) -> str:
        """
        Convert a file path to a Python module name.

        :param path: The file path to convert.
        :return: A string representing the module name.
        """
        parts = path.with_suffix("").parts
        return ".".join(parts)

    def _module_from_spec(self, spec: ModuleSpec) -> ModuleType:
        """
        Load a module from a module specification.

        :param spec: The module specification from which to load the module.
        :return: The loaded module.
        """
        return importlib.util.module_from_spec(spec)

    def _exec_module(self, loader: Loader, module: ModuleType) -> None:
        """
        Execute a module that has been loaded.

        :param loader: The loader to use for executing the module.
        :param module: The module to execute.
        """
        loader.exec_module(module)
