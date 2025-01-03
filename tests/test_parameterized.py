from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro import Scenario
from vedro.core import Dispatcher

from vedro_unittest import UnitTestLoader as Loader

from ._utils import dispatcher, loader, run_test_cases, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "loader",)  # fixtures


async def test_load_scenario(*, loader: Loader, tmp_scn_dir: Path):
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

    with when:
        test_cases = await loader.load(path)

    with then:
        assert len(test_cases) == 2
        assert issubclass(test_cases[0], Scenario)
        assert test_cases[0].__name__ == "Scenario_TestCase_test_add_0"
        assert test_cases[0].subject == "[TestCase] test add 0"


async def test_run_passed_test(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_add_1_2|test_add_3_4|"
