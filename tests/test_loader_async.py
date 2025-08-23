from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro import Scenario
from vedro.core import Dispatcher

from vedro_unittest import UnitTestScenarioProvider as Provider

from ._utils import create_scenario_source, dispatcher, provider, run_scenarios, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "provider",)  # fixtures


async def test_load_async_scenario(*, provider: Provider, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.IsolatedAsyncioTestCase):
                async def test_smth(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)

    with when:
        scenarios = await provider.provide(source)

    with then:
        assert len(scenarios) == 1
        assert issubclass(scenarios[0]._orig_scenario, Scenario)
        assert scenarios[0].name == "Scenario_TestCase_test_smth"
        assert scenarios[0].subject == "[TestCase] test smth"

        assert issubclass(scenarios[0]._orig_scenario, Scenario)


async def test_async_setup(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.IsolatedAsyncioTestCase):
                async def asyncSetUp(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("asyncSetUp|")
                def setUp(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("setUp|")
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
                async def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 2
        assert report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == (
            "setUp|asyncSetUp|test_smth1|setUp|asyncSetUp|test_smth2|"
        )


async def test_async_teardown(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.IsolatedAsyncioTestCase):
                async def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
                def tearDown(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("tearDown|")
                async def asyncTearDown(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("asyncTearDown|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 2
        assert report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == (
            "test_smth1|asyncTearDown|tearDown|test_smth2|asyncTearDown|tearDown|"
        )


async def test_async_cleanup(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.IsolatedAsyncioTestCase):
                def setUp(self):
                    self.addAsyncCleanup(self._cleanup_action)
                def test_smth(self):
                    self.assertTrue(True)
                def tearDown(self):
                    self.val = "tearDown"
                async def _cleanup_action(self):
                    with open("{tmp_file}", "w") as f:
                        f.write(self.val)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "tearDown"
