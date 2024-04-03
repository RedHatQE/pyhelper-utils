from pyhelper_utils.general import tts, ignore_exceptions
import pytest
import logging


@pytest.fixture
def func_for_ignore_exception():
    @ignore_exceptions(logger=logging.getLogger(), retry=1)
    def _foo():
        raise ValueError()

    return _foo


def test_tts():
    assert tts("1m") == 60
    assert tts("1h") == 3600
    assert tts("3600") == 3600


def test_ignore_exceptions(func_for_ignore_exception):
    assert not isinstance(func_for_ignore_exception(), Exception)
