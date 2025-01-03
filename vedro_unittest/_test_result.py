import unittest
from types import TracebackType
from typing import List, Tuple, Type, Union
from unittest import TestCase

__all__ = ("TestResult",)


ExcInfo = Tuple[Type[BaseException], BaseException, TracebackType]
OptExcInfo = Union[ExcInfo, Tuple[None, None, None]]


TestCaseExceptionList = List[Tuple[TestCase, BaseException]]


class UnexpectedSuccessError(AssertionError):
    """
    Represents an unexpected success in a test scenario.

    Used to indicate that a test case passed when it was expected to fail.
    """
    __module__ = "vedro_unittest"


class TestResult(unittest.TestResult):
    """
    Extends unittest.TestResult to handle custom test result reporting.

    Tracks exceptions, expected failures, and unexpected successes during
    the execution of unit tests.
    """
    def __init__(self) -> None:
        """
        Initialize the TestResult instance with custom tracking lists.
        """
        super().__init__()
        self.vedro_unittest_exceptions: TestCaseExceptionList = []
        self.vedro_unittest_expected_failures: TestCaseExceptionList = []
        self.vedro_unittest_unexpected_successes: TestCaseExceptionList = []

    def addSuccess(self, test: TestCase) -> None:
        """
        Record the success of a test case.

        :param test: The test case that succeeded.
        """
        pass

    def addError(self, test: TestCase, err: OptExcInfo) -> None:
        """
        Record an error that occurred during the execution of a test case.

        :param test: The test case that caused the error.
        :param err: The exception information for the error.
        """
        super().addError(test, err)
        self.vedro_unittest_exceptions.append((test, self._get_exception(err)))

    def addFailure(self, test: TestCase, err: OptExcInfo) -> None:
        """
        Record a failure for a test case.

        :param test: The test case that failed.
        :param err: The exception information for the failure.
        """
        super().addFailure(test, err)
        self.vedro_unittest_exceptions.append((test, self._get_exception(err)))

    def addSkip(self, test: TestCase, reason: str) -> None:
        """
        Record that a test case was skipped.

        :param test: The test case that was skipped.
        :param reason: The reason for skipping the test case.
        """
        super().addSkip(test, reason)
        self.vedro_unittest_exceptions.append((test, unittest.case.SkipTest(reason)))

    def addSubTest(self, test: TestCase, subtest: TestCase, err: Union[OptExcInfo, None]) -> None:
        """
        Record the result of a subtest.

        :param test: The parent test case.
        :param subtest: The subtest case being reported.
        :param err: The exception information, if the subtest failed or had an error.
        """
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.vedro_unittest_exceptions.append((subtest, self._get_exception(err)))

    def addExpectedFailure(self, test: TestCase, err: OptExcInfo) -> None:
        """
        Record a test case that failed as expected.

        :param test: The test case that was expected to fail.
        :param err: The exception information for the expected failure.
        """
        super().addExpectedFailure(test, err)
        self.vedro_unittest_expected_failures.append((test, self._get_exception(err)))

    def addUnexpectedSuccess(self, test: TestCase) -> None:
        """
        Record a test case that unexpectedly succeeded.

        :param test: The test case that unexpectedly succeeded.
        """
        super().addUnexpectedSuccess(test)
        unexpected_error = UnexpectedSuccessError("Scenario passed, but expected to fail")
        self.vedro_unittest_unexpected_successes.append((test, unexpected_error))

    def _get_exception(self, err: OptExcInfo) -> BaseException:
        """
        Extract the exception instance from exception information.

        :param err: The exception information tuple.
        :return: The exception instance.
        """
        _, exc_val, _ = err
        assert exc_val is not None
        return exc_val
