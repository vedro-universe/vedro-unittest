from pathlib import Path
from textwrap import dedent

import pytest
from baby_steps import given, then, when
from vedro import Scenario
from vedro.core import Dispatcher, VirtualScenario

from vedro_unittest import UnitTestScenarioProvider as Provider

from ._utils import create_scenario_source, dispatcher, provider, run_scenarios, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "provider",)  # fixtures


async def test_provide_scenario(*, provider: Provider, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)

    with when:
        scenarios = await provider.provide(source)

    with then:
        assert len(scenarios) == 1
        assert isinstance(scenarios[0], VirtualScenario)
        assert scenarios[0].name == "Scenario_TestCase_test_smth"
        assert scenarios[0].subject == "[TestCase] test smth"

        assert issubclass(scenarios[0]._orig_scenario, Scenario)


async def test_provide_scenarios(*, provider: Provider, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth1(self):
                    self.assertTrue(True)
                def test_smth2(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)

    with when:
        scenarios = await provider.provide(source)

    with then:
        assert len(scenarios) == 2


async def test_run_passed_test(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
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


async def test_run_failed_test_failure(*, provider: Provider, tmp_scn_dir: Path,
                                       dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.assertTrue(False)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1


async def test_run_failed_test_error(*, provider: Provider, tmp_scn_dir: Path,
                                     dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    raise TabError("details")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1


@pytest.mark.parametrize("decorator", [
    "unittest.skip",
    "unittest.skip('reason')",
    "unittest.skipIf(True, 'reason')",
    "unittest.skipUnless(False, 'reason')",
])
async def test_run_skipped_test_decorators(decorator: str, *,
                                           provider: Provider,
                                           tmp_scn_dir: Path,
                                           dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                @{decorator}
                def test_smth(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.skipped == 1


@pytest.mark.parametrize("decorator", [
    # If unittest.skip is used without providing a reason,
    # it returns a decorator that prevents unittest discovery from running the test.
    # "unittest.skip",

    "unittest.skip('reason')",
    "unittest.skipIf(True, 'reason')",
    "unittest.skipUnless(False, 'reason')",
])
async def test_run_skipped_class_decorators(decorator: str, *,
                                            provider: Provider,
                                            tmp_scn_dir: Path,
                                            dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            @{decorator}
            class TestCase(unittest.TestCase):
                def test_smth1(self):
                    self.assertTrue(True)
                def test_smth2(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 2
        assert report.skipped == 2


async def test_run_force_fail(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.fail("Intentional failure")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1


async def test_run_force_skip(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.skipTest("Intentional skip")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1 == report.failed == 1


async def test_run_expected_failure_passed(*, provider: Provider, tmp_scn_dir: Path,
                                           dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                @unittest.expectedFailure
                def test_smth(self):
                    self.assertTrue(False)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.passed == 1


async def test_run_expected_failure_failed(*, provider: Provider, tmp_scn_dir: Path,
                                           dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                @unittest.expectedFailure
                def test_smth(self):
                    self.assertTrue(True)
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 1
        assert report.failed == 1


async def test_setup(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                def setUp(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("setUp|")
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
                def test_smth2(self):
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
        assert tmp_file.read_text() == "setUp|test_smth1|setUp|test_smth2|"


async def test_teardown(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth1(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth1|")
                def test_smth2(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("test_smth2|")
                def tearDown(self):
                    with open("{tmp_file}", "a") as f:
                        f.write("tearDown|")
        '''))

        source = create_scenario_source(path, tmp_scn_dir.parent)
        scenarios = await provider.provide(source)

    with when:
        report = await run_scenarios(scenarios, dispatcher)

    with then:
        assert report.total == 2
        assert report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|tearDown|test_smth2|tearDown|"


async def test_cleanup(*, provider: Provider, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                def setUp(self):
                    self.addCleanup(self._cleanup_action)
                def test_smth(self):
                    self.assertTrue(True)
                def tearDown(self):
                    self.val = "tearDown"
                def _cleanup_action(self):
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
