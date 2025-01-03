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
            def setUpModule():
                pass
            class TestCase1(unittest.TestCase):
                def test_smth1(self):
                    self.assertTrue(True)
            class TestCase2(unittest.TestCase):
                def test_smth2(self):
                    self.assertTrue(True)
        '''))

    with when:
        test_cases = await loader.load(path)

    with then:
        assert len(test_cases) == 1
        assert issubclass(test_cases[0], Scenario)
        assert test_cases[0].__name__ == "Scenario_UnitTestSuite"
        assert test_cases[0].subject == "All tests in module 'scenarios.scenario'"


async def test_run_passed_test(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|"


async def test_run_failed_test_failure(*, loader: Loader, tmp_scn_dir: Path,
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|"


async def test_run_failed_test_error(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|"


async def test_run_skipped_test(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.failed == 1
        assert report.skipped == 0

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth2|"


async def test_run_skipped_all_tests(loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.skipped == 1

        assert not tmp_file.exists()


async def test_module_setup(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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

        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "setUpModule|test_smth1|test_smth2|"


async def test_module_teardown(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
        assert tmp_file.read_text() == "test_smth1|test_smth2|tearDownModule|"


async def test_module_cleanup(*, loader: Loader, tmp_scn_dir: Path, dispatcher: Dispatcher):
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
        test_cases = await loader.load(path)

    with when:
        report = await run_test_cases(test_cases, dispatcher, project_dir=tmp_scn_dir.parent)

    with then:
        assert report.total == report.passed == 1

        assert tmp_file.exists()
