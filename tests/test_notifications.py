from pyhelper_utils.notifications import send_slack_message
import pytest
from simple_logger.logger import get_logger
from requests.exceptions import SSLError


LOGGER = get_logger(name="test-notifications")
WEBHOOK_URL = "https://nonexists.non"


def test_send_slack_message():
    send_slack_message(webhook_url=WEBHOOK_URL, message="test", logger=LOGGER, raise_on_error=False)


def test_send_slack_message_wit_raise():
    with pytest.raises(SSLError):
        send_slack_message(webhook_url=WEBHOOK_URL, logger=LOGGER, message="test")
