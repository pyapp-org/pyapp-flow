"""Helper functions for pyapp_flow."""

import logging
from contextlib import contextmanager
from typing import Any


@contextmanager
def change_log_level(level: int | str | None, *, logger: logging.Logger | None = None):
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


def human_join_strings(items, *, conjunction: str = "and", empty: str = ""):
    """Join a list of strings with a human-readable conjunction."""
    if not items:
        return empty

    if len(items) == 1:
        return items[0]

    return f"{', '.join(items[:-1])} {conjunction} {items[-1]}"


SENSITIVE_WORDS = ("credential", "authorization", "token", "secret", "password")


def set_sensitive_words(sensitive_words: tuple[str, ...]):
    global SENSITIVE_WORDS
    SENSITIVE_WORDS = tuple(sensitive_words)


def mask_keys(d: dict[str, Any], *, sensitive_words: tuple[str, ...] | None = None):
    """Mask dictionary values for keys that contain a sensitive name"""

    sensitive_words = sensitive_words or SENSITIVE_WORDS

    def _mask(key: str, value: Any) -> Any:
        if any(word in key for word in sensitive_words):
            return "****"
        return value

    return {key: _mask(key, value) for key, value in d.items()}
