from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro.core import Dispatcher

from vedro_unittest import UnitTestLoader as Loader

from ._utils import dispatcher, loader, run_test_cases, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "loader",)  # fixtures


async def test_subtests_all_pass(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "subtest 0|subtest 1|subtest 2|"


async def test_subtests_one_of_three_fails(*, loader: Loader, tmp_scn_dir: Path,
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "subtest 0|subtest 1|subtest 2|"
