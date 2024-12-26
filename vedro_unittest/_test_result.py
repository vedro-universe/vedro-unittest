import unittest
from types import TracebackType
from typing import List, Tuple, Union
from unittest import TestCase

__all__ = ("TestResult",)


ExcInfo = tuple[type[BaseException], BaseException, TracebackType]
OptExcInfo = ExcInfo | tuple[None, None, None]


class TestResult(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.vedro_unittest_exceptions: List[Tuple[TestCase, BaseException]] = []
        self.vedro_unittest_expected_failures: List[Tuple[TestCase, BaseException]] = []
        self.vedro_unittest_unexpected_successes: List[Tuple[TestCase, None]] = []

    def addSuccess(self, test: TestCase) -> None:
        pass

    def addError(self, test: TestCase, err: OptExcInfo) -> None:
        super().addError(test, err)
        self.vedro_unittest_exceptions.append((test, self._get_exception(err)))

    def addFailure(self, test: TestCase, err: OptExcInfo) -> None:
        super().addFailure(test, err)
        self.vedro_unittest_exceptions.append((test, self._get_exception(err)))

    def addSkip(self, test: TestCase, reason: str) -> None:
        super().addSkip(test, reason)
        self.vedro_unittest_exceptions.append((test, unittest.case.SkipTest(reason)))

    def addSubTest(self, test: TestCase, subtest: TestCase, err: Union[OptExcInfo, None]) -> None:
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.vedro_unittest_exceptions.append((subtest, self._get_exception(err)))

    def addExpectedFailure(self, test: TestCase, err: OptExcInfo) -> None:
        super().addExpectedFailure(test, err)
        self.vedro_unittest_expected_failures.append((test, self._get_exception(err)))

    def addUnexpectedSuccess(self, test: TestCase) -> None:
        super().addUnexpectedSuccess(test)
        self.vedro_unittest_unexpected_successes.append((test, None))

    def _get_exception(self, err: OptExcInfo) -> BaseException:
        _, exc_val, _ = err
        assert exc_val is not None
        return exc_val
