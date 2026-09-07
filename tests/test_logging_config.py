from logging_config import configure_logging


def test_configure_logging_creates_log_directory_and_file(
    tmp_path,
):
    log_path = tmp_path / "logs" / "deepcrate.log"

    logger = configure_logging(log_path)
    logger.info("Test log message")

    for handler in logger.handlers:
        handler.flush()

    assert log_path.exists()
    assert "Test log message" in log_path.read_text(
        encoding="utf-8",
    )


def test_configure_logging_does_not_duplicate_handlers(
    tmp_path,
):
    log_path = tmp_path / "deepcrate.log"

    logger = configure_logging(log_path)
    logger = configure_logging(log_path)

    assert len(logger.handlers) == 2