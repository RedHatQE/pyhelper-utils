from pyhelper_utils.general import tts


def test_tts():
    assert tts("1m") == 60
    assert tts("1h") == 3600
    assert tts("3600") == 3600
