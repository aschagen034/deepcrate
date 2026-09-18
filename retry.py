import logging
import time
from collections.abc import Callable
from typing import TypeVar


Result = TypeVar("Result")


def run_with_retries(
    operation: Callable[[], Result],
    retryable_exceptions: tuple[type[Exception], ...],
    operation_name: str = "operation",
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    sleep_func: Callable[[float], None] = time.sleep,
    delay_for_exception: (
        Callable[[Exception, int], float] | None
    ) = None,
    logger: logging.Logger | None = None,
) -> Result:
    """Run an operation again after temporary failures.

    The first retry waits for ``base_delay`` seconds. Later retries use
    exponential backoff up to ``max_delay``. A custom delay function can
    override the calculated delay, such as when an API provides a
    Retry-After value.
    """
    if max_attempts < 1:
        raise ValueError("Maximum attempts must be at least 1")

    if base_delay < 0:
        raise ValueError("Base delay cannot be negative")

    if max_delay < 0:
        raise ValueError("Maximum delay cannot be negative")

    if logger is None:
        logger = logging.getLogger("deepcrate")

    for attempt in range(1, max_attempts + 1):
        try:
            return operation()
        except retryable_exceptions as error:
            if attempt == max_attempts:
                logger.error(
                    "%s failed after %d attempts",
                    operation_name,
                    max_attempts,
                )
                raise

            if delay_for_exception is not None:
                delay = delay_for_exception(error, attempt)
            else:
                delay = min(
                    base_delay * (2 ** (attempt - 1)),
                    max_delay,
                )

            delay = max(0.0, delay)

            logger.warning(
                "%s failed on attempt %d of %d; "
                "retrying in %.1f seconds: %s",
                operation_name,
                attempt,
                max_attempts,
                delay,
                error,
            )

            sleep_func(delay)

    raise RuntimeError("Retry loop ended unexpectedly")