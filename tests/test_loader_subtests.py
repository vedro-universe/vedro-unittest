from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro.core import Dispatcher

from vedro_unittest import UnitTestScenarioProvider as Provider

from ._utils import create_scenario_source, dispatcher, provider, run_scenarios, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "provider",)  # fixtures


async def test_subtests_all_pass(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest

            class TestCase(unittest.TestCase):
                def test_subtests(self):
                    with open("{tmp_file}", "w") as f:
                        for i in range(3):
                            with self.subTest(i=i):
                                f.write(f"subtest {{i}}|")
                                self.assertTrue(i >= 0)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "subtest 0|subtest 1|subtest 2|"


async def test_subtests_one_of_three_fails(*, provider: Provider, tmp_scn_dir: Path,
                                           dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest

            class TestCase(unittest.TestCase):
                def test_subtests(self):
                    with open("{tmp_file}", "w") as f:
                        for i in range(3):
                            with self.subTest(i=i):
                                f.write(f"subtest {{i}}|")
                                self.assertTrue(i != 2)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "subtest 0|subtest 1|subtest 2|"
