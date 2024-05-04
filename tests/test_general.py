from pyhelper_utils.general import stt, tts, ignore_exceptions, retry_on_exception
import pytest
import logging


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


@pytest.fixture
def func_for_retry_on_exception(mocker):
    mock_func = mocker.Mock(side_effect=ValueError())
    mock_func.__name__ = "mock_func"
    _foo = retry_on_exception(logger=logging.getLogger(), retry=1, retry_interval=1)(mock_func)
    _foo.mock_func = _foo.__wrapped__
    return _foo


@pytest.fixture
def func_for_no_retry_no_exception(mocker):
    mock_func = mocker.Mock()
    mock_func.__name__ = "mock_func"
    _foo = retry_on_exception(logger=logging.getLogger(), retry=1, retry_interval=1)(mock_func)
    _foo.mock_func = _foo.__wrapped__
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


def test_retries_on_exception(func_for_retry_on_exception):
    with pytest.raises(ValueError):
        func_for_retry_on_exception()
    assert func_for_retry_on_exception.mock_func.call_count == 2


def test_no_retries_no_exception(func_for_no_retry_no_exception):
    func_for_no_retry_no_exception()
    assert func_for_no_retry_no_exception.mock_func.call_count == 1


def test_stt():
    assert stt(3600) == "1 hour"
    assert stt(3600 * 24) == "1 day"
    assert stt((60 * 60 * 14 + 65)) == "14 hours and 1 minute and 5 seconds"
    assert stt(30) == "30 seconds"
    assert stt(90) == "1 minute and 30 seconds"
