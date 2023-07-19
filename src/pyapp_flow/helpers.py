"""Helper functions for pyapp_flow."""

import logging
from contextlib import contextmanager
from typing import Union


@contextmanager
def change_log_level(level: Union[int, str, None], *, logger: logging.Logger = None):
    """Temporarily change the log level of a logger."""
    if level is None:
        yield
    else:
        logger = logger or logging.root
        old_level = logger.level
        logger.setLevel(level)
        try:
            yield
        finally:
            logger.setLevel(old_level)
