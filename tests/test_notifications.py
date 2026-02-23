import pytest
from simple_logger.logger import get_logger

from pyhelper_utils.notifications import send_slack_message

LOGGER = get_logger(name="test-notifications")
WEBHOOK_URL = "https://nonexists.non"


def test_send_slack_message():
    send_slack_message(webhook_url=WEBHOOK_URL, message="test", logger=LOGGER, raise_on_error=False)


def test_send_slack_message_with_raise():
    with pytest.raises(Exception):
        send_slack_message(webhook_url=WEBHOOK_URL, logger=LOGGER, message="test", post_timout=1)
