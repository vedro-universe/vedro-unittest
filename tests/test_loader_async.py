from pathlib import Path
from textwrap import dedent

from baby_steps import given, then, when
from vedro import Scenario
from vedro.core import Dispatcher

from vedro_unittest import UnitTestLoader as Loader

from ._utils import dispatcher, loader, run_test_cases, tmp_scn_dir

__all__ = ("dispatcher", "tmp_scn_dir", "loader",)  # fixtures


async def test_load_async_scenario(*, loader: Loader, tmp_scn_dir: Path):
    with given:
        path = tmp_scn_dir / "scenario.py"
        path.write_text(dedent('''
            import unittest
            class TestCase(unittest.IsolatedAsyncioTestCase):
                async def test_smth(self):
                    self.assertTrue(True)
        '''))

    with when:
        test_cases = await loader.load(path)

    with then:
        assert len(test_cases) == 1
        assert issubclass(test_cases[0], Scenario)
        assert test_cases[0].__name__ == "Scenario_TestCase_test_smth"
        assert test_cases[0].subject == "[TestCase] test smth"


async def test_async_setup(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == (
            "setUp|asyncSetUp|test_smth1|setUp|asyncSetUp|test_smth2|"
        )


async def test_async_teardown(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 2

        assert tmp_file.exists()
        assert tmp_file.read_text() == (
            "test_smth1|asyncTearDown|tearDown|test_smth2|asyncTearDown|tearDown|"
        )


async def test_async_cleanup(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "tearDown"
