from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro.core import Dispatcher

from vedro_unittest import UnitTestScenarioProvider as Provider

from ._utils import create_scenario_source, dispatcher, provider, run_scenarios, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "provider",)  # fixtures


async def test_load_scenarios(*, provider: Provider, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class BaseTestCase(unittest.TestCase):
                def test_base_method(self):
                    self.assertTrue(True)
            class ChildTestCase(BaseTestCase):
                def test_child_method(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)

    with when:
        scenarios = await provider.provide(source)

    with then:
        assert len(scenarios) == 3


async def test_run_passed_tests(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class BaseTestCase(unittest.TestCase):
                def test_base_method(self):
                    self.assertTrue(True)
            class ChildTestCase(BaseTestCase):
                def test_child_method(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 3
        assert report.passed == 3


async def test_run_failed_tests(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class BaseTestCase(unittest.TestCase):
                def test_base_method(self):
                    self.assertTrue(False)
            class ChildTestCase(BaseTestCase):
                def test_child_method(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 3
        assert report.passed == 1
        assert report.failed == 2
