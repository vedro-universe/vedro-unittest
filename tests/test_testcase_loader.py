from pathlib import Path
from textwrap import dedent

import pytest
from baby_steps import given, then, when
from vedro import Scenario
from vedro.core import Dispatcher

from vedro_unittest import TestCaseLoader

from ._utils import dispatcher, loader, run_test_cases, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "loader",)  # fixtures


async def test_load_scenario(*, loader: TestCaseLoader, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.assertTrue(True)
        '''))

    with when:
        test_cases = await loader.load(path)

    with then:
        assert len(test_cases) == 1
        assert issubclass(test_cases[0], Scenario)
        assert test_cases[0].__name__ == "Scenario__TestCase__test_smth"
        assert test_cases[0].subject == "TestCase.test_smth"


async def test_run_passed_test(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                               dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.assertTrue(True)
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1


async def test_run_failed_test(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                               dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.assertTrue(False)
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1


async def test_run_skipped_test(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                                dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                @unittest.skip
                def test_smth(self):
                    self.assertTrue(True)
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.skipped == 1


@pytest.mark.parametrize("decorator", [
    "unittest.skip",
    "unittest.skip('reason')",
    "unittest.skipIf(True, 'reason')",
    "unittest.skipUnless(False, 'reason')",
])
async def test_run_skipped_test_decorators(decorator: str, *, loader: TestCaseLoader,
                                           tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                @{decorator}
                def test_smth(self):
                    self.assertTrue(True)
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.skipped == 1


@pytest.mark.parametrize("decorator", [
    # If unittest.skip is used without providing a reason,
    # it returns a decorator that prevents unittest discovery from running the test.
    # "unittest.skip",

    "unittest.skip('reason')",
    "unittest.skipIf(True, 'reason')",
    "unittest.skipUnless(False, 'reason')",
])
async def test_run_skipped_class_decorators(decorator: str, *, loader: TestCaseLoader,
                                            tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.skipped == 2


async def test_run_intentional_fail(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                                    dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.fail("Intentional failure for testing")
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == 1 == report.failed == 1


async def test_run_expected_failure_passed(*, loader: TestCaseLoader, tmp_scn_dir: Path,
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1


async def test_run_expected_failure_failed(*, loader: TestCaseLoader, tmp_scn_dir: Path,
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1


async def test_set_up(*, loader: TestCaseLoader, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                def setUp(self):
                    self.val = "setUp"
                def test_smth(self):
                    with open("{tmp_file}", "w") as f:
                        f.write(self.val)
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "setUp"


async def test_tear_down(*, loader: TestCaseLoader, tmp_scn_dir: Path, dispatcher: Dispatcher):
    with given:
        tmp_file = tmp_scn_dir / "tmp_file.txt"

        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent(f'''
            import unittest
            class TestCase(unittest.TestCase):
                def test_smth(self):
                    self.val = "test_smth"
                def tearDown(self):
                    with open("{tmp_file}", "w") as f:
                        f.write(self.val)
        '''))
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth"


async def test_cleanup(*, loader: TestCaseLoader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "tearDown"


async def test_subtest_all_pass(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                                dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_subtests(self):
                    for i in range(3):
                        with self.subTest(i=i):
                            self.assertTrue(i < 3)  # i is 0, 1, 2 - always True
        '''))
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1


async def test_subtest_one_fails(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                                 dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.TestCase):
                def test_subtests(self):
                    for i in range(3):
                        with self.subTest(i=i):
                            self.assertTrue(i < 2)  # fails when i=2
        '''))
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1
