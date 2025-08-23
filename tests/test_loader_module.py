from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro.core import Dispatcher, VirtualScenario

from vedro_unittest import UnitTestScenarioProvider as Provider

from ._utils import create_scenario_source, dispatcher, provider, run_scenarios, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "provider",)  # fixtures


async def test_load_scenario(*, provider: Provider, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            def setUpModule():
                pass
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    self.assertTrue(True)
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)

    with when:
        scenarios = await provider.provide(source)

    with then:
        assert len(scenarios) == 1
        assert isinstance(scenarios[0], VirtualScenario)
        assert scenarios[0].name == "Scenario_UnitTestSuite"
        assert scenarios[0].subject == "All tests in module 'scenarios.scenario'"


async def test_run_passed_test(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            def setUpModule():
                pass
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|"


async def test_run_failed_test_failure(*, provider: Provider, tmp_scn_dir: Path,
                                       dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            def setUpModule():
                pass
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
                    self.assertTrue(False)
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|"


async def test_run_failed_test_error(*, provider: Provider, tmp_scn_dir: Path,
                                     dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            def setUpModule():
                pass
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
                    raise TabError("details")
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|"


async def test_run_skipped_test(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            def setUpModule():
                pass
            @unittest.skip("reason")
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1
        assert report.skipped == 0

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth2|"


async def test_run_skipped_all_tests(provider: Provider, tmp_scn_dir: Path,
                                     dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            def setUpModule():
                pass
            @unittest.skip("reason")
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
            @unittest.skip("reason")
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.skipped == 1

        assert not tmp_file.exists()


async def test_module_setup(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest

            def setUpModule():
                with open("{tmp_file}", "a") as f:
                    f.write("setUpModule|")

            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")

            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "setUpModule|test_smth1|test_smth2|"


async def test_module_teardown(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest

            def tearDownModule():
                with open("{tmp_file}", "a") as f:
                    f.write("tearDownModule|")

            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")

            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
        '''))
        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|tearDownModule|"


async def test_module_cleanup(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest

            def setUpModule():
                unittest.addModuleCleanup(_module_cleanup_action)

            def tearDownModule():
                unittest._file_content = "tearDownModule"

            def _module_cleanup_action():
                with open("{tmp_file}", "w") as f:
                    f.write(unittest._file_content)

            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.assertTrue(True)
        '''))
        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1

        assert tmp_file.exists()
