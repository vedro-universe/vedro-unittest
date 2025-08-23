from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro import Scenario
from vedro.core import Dispatcher, VirtualScenario

from vedro_unittest import UnitTestScenarioProvider as Provider

from ._utils import create_scenario_source, dispatcher, provider, run_scenarios, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "provider",)  # fixtures


async def test_load_scenario(*, provider: Provider, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            from parameterized import parameterized

            class TestCase(unittest.TestCase):
                @parameterized.expand([
                    (1, 2, 3),
                    (3, 4, 7),
                ])
                def test_add(self, a, b, expected):
                    self.assertEqual(a + b, expected)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)

    with when:
        scenarios = await provider.provide(source)

    with then:
        assert len(scenarios) == 2
        assert isinstance(scenarios[0], VirtualScenario)
        assert scenarios[0].name == "Scenario_TestCase_test_add_0"
        assert scenarios[0].subject == "[TestCase] test add 0"

        assert issubclass(scenarios[0]._orig_scenario, Scenario)


async def test_run_passed_test(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            from parameterized import parameterized

            class TestCase(unittest.TestCase):
                @parameterized.expand([
                    (1, 2, 3),
                    (3, 4, 7),
                ])
                def test_add(self, a, b, expected):
                    with open("{tmp_file}", "a") as f:
                        f.write(f"test_add_{{a}}_{{b}}|")
                    self.assertEqual(a + b, expected)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 2
        assert report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_add_1_2|test_add_3_4|"
