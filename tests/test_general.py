import logging

import pytest

from pyhelper_utils.general import ignore_exceptions, stt, tts


@pytest.fixture
def func_for_ignore_exception():
    @ignore_exceptions(logger=logging.getLogger(), retry=1, retry_interval=1)
    def _foo():
        raise ValueError()

    return _foo


@pytest.fixture
def func_for_ignore_exception_with_return_value_on_error():
    @ignore_exceptions(logger=logging.getLogger(), retry_interval=1, return_on_error="test")
    def _foo():
        raise ValueError()

    return _foo


def test_tts():
    assert tts("1m") == 60
    assert tts("1h") == 3600
    assert tts("3600") == 3600


def test_ignore_exceptions(func_for_ignore_exception):
    assert not isinstance(func_for_ignore_exception(), Exception)
    assert not func_for_ignore_exception()


def test_ignore_exceptions_with_return_value(func_for_ignore_exception_with_return_value_on_error):
    assert func_for_ignore_exception_with_return_value_on_error() == "test"


def test_ignore_exception_raise_final_exception():
    @ignore_exceptions(retry=1, retry_interval=1, raise_final_exception=True)
    def _foo():
        raise ValueError()

    with pytest.raises(ValueError):
        _foo()


def test_stt():
    assert stt(3600) == "1 hour"
    assert stt(3600 * 24) == "1 day"
    assert stt(60 * 60 * 14 + 65) == "14 hours and 1 minute and 5 seconds"
    assert stt(30) == "30 seconds"
    assert stt(90) == "1 minute and 30 seconds"
