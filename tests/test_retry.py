import pytest

from retry import run_with_retries


class TemporaryError(Exception):
    pass


class PermanentError(Exception):
    pass


def test_run_with_retries_returns_first_success():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        return "success"

    result = run_with_retries(
        operation,
        retryable_exceptions=(TemporaryError,),
        sleep_func=delays.append,
    )

    assert result == "success"
    assert len(attempts) == 1
    assert delays == []


def test_run_with_retries_uses_exponential_backoff():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")

        if len(attempts) < 3:
            raise TemporaryError("Temporary failure")

        return "success"

    result = run_with_retries(
        operation,
        retryable_exceptions=(TemporaryError,),
        max_attempts=3,
        base_delay=2.0,
        sleep_func=delays.append,
    )

    assert result == "success"
    assert len(attempts) == 3
    assert delays == [2.0, 4.0]


def test_run_with_retries_raises_after_final_attempt():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        raise TemporaryError("Still unavailable")

    with pytest.raises(
        TemporaryError,
        match="Still unavailable",
    ):
        run_with_retries(
            operation,
            retryable_exceptions=(TemporaryError,),
            max_attempts=3,
            sleep_func=delays.append,
        )

    assert len(attempts) == 3
    assert delays == [1.0, 2.0]


def test_run_with_retries_does_not_retry_permanent_error():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")
        raise PermanentError("Invalid request")

    with pytest.raises(
        PermanentError,
        match="Invalid request",
    ):
        run_with_retries(
            operation,
            retryable_exceptions=(TemporaryError,),
            sleep_func=delays.append,
        )

    assert len(attempts) == 1
    assert delays == []


def test_run_with_retries_uses_custom_delay():
    attempts = []
    delays = []

    def operation():
        attempts.append("called")

        if len(attempts) == 1:
            raise TemporaryError("Rate limited")

        return "success"

    result = run_with_retries(
        operation,
        retryable_exceptions=(TemporaryError,),
        sleep_func=delays.append,
        delay_for_exception=lambda error, attempt: 12.0,
    )

    assert result == "success"
    assert delays == [12.0]


def test_run_with_retries_rejects_invalid_attempt_count():
    with pytest.raises(
        ValueError,
        match="Maximum attempts",
    ):
        run_with_retries(
            lambda: "success",
            retryable_exceptions=(TemporaryError,),
            max_attempts=0,
        )