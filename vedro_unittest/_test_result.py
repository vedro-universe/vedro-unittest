import unittest
from types import TracebackType
from typing import List, Tuple, Type, Union
from unittest import TestCase

__all__ = ("TestResult",)


ExcInfo = Tuple[Type[BaseException], BaseException, TracebackType]
OptExcInfo = Union[ExcInfo, Tuple[None, None, None]]


TestCaseExceptionList = List[Tuple[TestCase, BaseException]]


class UnexpectedSuccessError(AssertionError):
    __module__ = "vedro_unittest"


class TestResult(unittest.TestResult):
    def __init__(self) -> None:
        super().__init__()
        self.vedro_unittest_exceptions: TestCaseExceptionList = []
        self.vedro_unittest_expected_failures: TestCaseExceptionList = []
        self.vedro_unittest_unexpected_successes: TestCaseExceptionList = []

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
        unexpected_error = UnexpectedSuccessError("Scenario passed, but expected to fail")
        self.vedro_unittest_unexpected_successes.append((test, unexpected_error))

    def _get_exception(self, err: OptExcInfo) -> BaseException:
        _, exc_val, _ = err
        assert exc_val is not None
        return exc_val
