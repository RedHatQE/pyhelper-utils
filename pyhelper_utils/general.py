from __future__ import annotations
import re
from time import sleep
from functools import wraps
from logging import Logger
from typing import Any


def tts(ts: Any) -> int:
    """
    Convert time string to seconds.

    Args:
        ts (str): time string to convert, can be and int followed by s/m/h
            if only numbers was sent return int(ts)

    Example:
        >>> tts(ts="1h")
        3600
        >>> tts(ts="3600")
        3600

    Returns:
        int: Time in seconds
    """
    if time_and_unit_match := re.match(r"(?P<time>\d+)(?P<unit>\w)", str(ts)):
        time_and_unit = time_and_unit_match.groupdict()
    else:
        return int(ts)

    _time = int(time_and_unit["time"])
    _unit = time_and_unit["unit"].lower()
    if _unit == "s":
        return _time
    elif _unit == "m":
        return _time * 60
    elif _unit == "h":
        return _time * 60 * 60
    else:
        return int(ts)


def ignore_exceptions(
    retry: int = 0,
    retry_interval: int = 1,
    return_on_error: Any = None,
    logger: Logger | None = None,
) -> Any:
    """
    Decorator to ignore exceptions with support for retry.

    Args:
        retry (int): Number of retry if the underline function throw exception.
        retry_interval (int): Number of seconds to wait between retries.
        return_on_error (Any): Return value if the underline function throw exception.
        logger (Logger): logger to use, if not passed no logs will be displayed.


    Returns:
        any: the underline function return value.
    """

    def wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as ex:
                if retry:
                    sleep(retry_interval)
                    for _ in range(0, retry):
                        try:
                            return func(*args, **kwargs)
                        except Exception:
                            sleep(retry_interval)

                if logger:
                    logger.info(f"{func.__name__} error: {ex}")
                return return_on_error

        return inner

    return wrapper
