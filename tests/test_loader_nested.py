from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro.core import Dispatcher

from vedro_unittest import UnitTestLoader as Loader

from ._utils import dispatcher, loader, run_test_cases, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "loader",)  # fixtures


async def test_load_scenarios(*, loader: Loader, tmp_scn_dir: Path):
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

    with when:
        test_cases = await loader.load(path)

    with then:
        assert len(test_cases) == 3


async def test_run_passed_tests(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 3


async def test_run_failed_tests(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == 3
        assert report.passed == 1
        assert report.failed == 2
