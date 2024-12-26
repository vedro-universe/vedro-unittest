from pathlib import Path
from textwrap import dedent

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
            class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
                async def test_smth(self):
                    self.assertTrue(True)
        '''))

    with when:
        test_cases = await loader.load(path)

    with then:
        assert len(test_cases) == 1
        assert issubclass(test_cases[0], Scenario)
        assert test_cases[0].__name__ == "Scenario__AsyncTestCase__test_smth"
        assert test_cases[0].subject == "[AsyncTestCase] test smth"


async def test_run_passed_test(*, loader: TestCaseLoader, tmp_scn_dir: Path,
                               dispatcher: Dispatcher):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
                async def test_smth(self):
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
            class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
                async def test_smth(self):
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
            class AsyncTestCase(unittest.IsolatedAsyncioTestCase):
                @unittest.skip
                async def test_smth(self):
                    self.assertTrue(True)
        '''))

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.skipped == 1