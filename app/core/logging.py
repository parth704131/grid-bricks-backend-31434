import logging


def configure_logging(level: str) -> None:
    """Configure concise, process-wide logs without including sensitive settings."""
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
