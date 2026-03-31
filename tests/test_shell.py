from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import paramiko
import pytest
from timeout_sampler import TimeoutExpiredError

from pyhelper_utils.exceptions import CommandExecFailed
from pyhelper_utils.shell import DEFAULT_SSH_EXCEPTIONS, run_command, run_ssh_commands


@pytest.fixture
def mock_host():
    host = MagicMock()
    host.fqdn = "test-host.example.com"
    return host


@pytest.fixture
def mock_ssh_session():
    session = MagicMock()
    session.run_cmd.return_value = (0, "output", "")
    return session


@pytest.fixture
def mock_executor(mock_ssh_session):
    executor = MagicMock()
    executor.session.return_value.__enter__ = MagicMock(return_value=mock_ssh_session)
    executor.session.return_value.__exit__ = MagicMock(return_value=False)
    executor.sock = None
    return executor


@pytest.fixture
def mock_host_with_executor(mock_host, mock_executor):
    mock_host.executor.return_value = mock_executor
    return mock_host


class TestRunSshCommandsNoRetry:
    """Tests for run_ssh_commands without retry (wait_timeout=0, default)."""

    def test_single_command_success(self, mock_host_with_executor, mock_ssh_session):
        result = run_ssh_commands(host=mock_host_with_executor, commands=["echo", "hello"])
        assert result == ["output"]
        mock_ssh_session.run_cmd.assert_called_once()

    def test_multiple_commands_success(self, mock_host_with_executor, mock_ssh_session):
        mock_ssh_session.run_cmd.side_effect = [
            (0, "out1", ""),
            (0, "out2", ""),
        ]
        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=[["echo", "hello"], ["echo", "world"]],
        )
        assert result == ["out1", "out2"]
        assert mock_ssh_session.run_cmd.call_count == 2

    def test_command_failure_raises(self, mock_host_with_executor, mock_ssh_session):
        mock_ssh_session.run_cmd.return_value = (1, "", "error msg")
        with pytest.raises(CommandExecFailed):
            run_ssh_commands(host=mock_host_with_executor, commands=["failing", "cmd"])

    def test_command_failure_no_check_rc(self, mock_host_with_executor, mock_ssh_session):
        mock_ssh_session.run_cmd.return_value = (1, "out", "error msg")
        result = run_ssh_commands(host=mock_host_with_executor, commands=["cmd"], check_rc=False)
        assert result == ["out"]


class TestRunSshCommandsWithRetry:
    """Tests for run_ssh_commands with retry (wait_timeout > 0)."""

    def test_retry_on_ssh_exception(self, mock_host_with_executor, mock_ssh_session):
        """When SSHException occurs, retry should eventually succeed."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise paramiko.SSHException("Connection lost")
            return (0, "success", "")

        mock_ssh_session.run_cmd.side_effect = side_effect

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "hello"],
            wait_timeout=60,
            sleep=1,
        )
        assert result == ["success"]
        assert call_count == 3

    def test_retry_on_os_error(self, mock_host_with_executor, mock_ssh_session):
        """When OSError occurs, retry should eventually succeed."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("Connection refused")
            return (0, "ok", "")

        mock_ssh_session.run_cmd.side_effect = side_effect

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "test"],
            wait_timeout=60,
            sleep=1,
            exceptions_dict={OSError: []},
        )
        assert result == ["ok"]
        assert call_count == 2

    def test_no_retry_when_wait_timeout_zero(self, mock_host_with_executor, mock_ssh_session):
        """Default wait_timeout=0 should not retry."""
        mock_ssh_session.run_cmd.side_effect = paramiko.SSHException("fail")

        with pytest.raises(paramiko.SSHException):
            run_ssh_commands(host=mock_host_with_executor, commands=["echo", "hello"])

    def test_custom_exceptions_dict(self, mock_host_with_executor, mock_ssh_session):
        """Custom exceptions_dict should be used for retry."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("custom error")
            return (0, "done", "")

        mock_ssh_session.run_cmd.side_effect = side_effect

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "test"],
            wait_timeout=60,
            sleep=1,
            exceptions_dict={ConnectionError: []},
        )
        assert result == ["done"]

    def test_retry_does_not_catch_unspecified_exceptions(self, mock_host_with_executor, mock_ssh_session):
        """When an explicit exceptions_dict is provided, exceptions not in it raise TimeoutExpiredError immediately."""
        mock_ssh_session.run_cmd.side_effect = ValueError("unexpected")

        with pytest.raises(TimeoutExpiredError) as exc_info:
            run_ssh_commands(
                host=mock_host_with_executor,
                commands=["echo", "hello"],
                wait_timeout=60,
                sleep=1,
                exceptions_dict={OSError: []},
            )
        assert isinstance(exc_info.value.last_exp, ValueError)

    def test_retry_preserves_command_exec_failed(self, mock_host_with_executor, mock_ssh_session):
        """CommandExecFailed is NOT caught by default {SSHException: []} dict, so it raises TimeoutExpiredError immediately."""
        mock_ssh_session.run_cmd.return_value = (1, "", "error")

        with pytest.raises(TimeoutExpiredError) as exc_info:
            run_ssh_commands(
                host=mock_host_with_executor,
                commands=["fail", "cmd"],
                wait_timeout=5,
                sleep=1,
            )
        assert isinstance(exc_info.value.last_exp, CommandExecFailed)

    def test_default_exceptions_dict_uses_ssh_exception(self, mock_host_with_executor, mock_ssh_session, monkeypatch):
        """When exceptions_dict is not provided, DEFAULT_SSH_EXCEPTIONS is forwarded to TimeoutSampler."""
        from pyhelper_utils import shell as shell_mod

        captured: dict[str, object] = {}

        class _CapturingSampler:
            def __init__(self, **kwargs: object) -> None:
                captured["exceptions_dict"] = kwargs.get("exceptions_dict")
                self._result = kwargs["func"](
                    host=kwargs["host"],
                    commands_list=kwargs["commands_list"],
                    get_pty=kwargs["get_pty"],
                    check_rc=kwargs["check_rc"],
                    timeout=kwargs["timeout"],
                    tcp_timeout=kwargs["tcp_timeout"],
                )

            def __iter__(self):
                yield self._result

        monkeypatch.setattr(shell_mod, "TimeoutSampler", _CapturingSampler)

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "hello"],
            wait_timeout=60,
            sleep=1,
            # exceptions_dict NOT provided -- should default to DEFAULT_SSH_EXCEPTIONS
        )
        assert result == ["output"]
        assert captured["exceptions_dict"] is DEFAULT_SSH_EXCEPTIONS
        assert captured["exceptions_dict"] == {paramiko.SSHException: []}

    def test_none_exceptions_dict_catches_all(self, mock_host_with_executor, mock_ssh_session):
        """Passing exceptions_dict=None catches all exceptions."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("unexpected")
            return (0, "ok", "")

        mock_ssh_session.run_cmd.side_effect = side_effect

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "test"],
            wait_timeout=60,
            sleep=1,
            exceptions_dict=None,
        )
        assert result == ["ok"]
        assert call_count == 2

    def test_catch_all_exceptions(self, mock_host_with_executor, mock_ssh_session):
        """Passing {Exception: []} catches all exceptions."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("unexpected")
            return (0, "ok", "")

        mock_ssh_session.run_cmd.side_effect = side_effect

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "test"],
            wait_timeout=60,
            sleep=1,
            exceptions_dict={Exception: []},
        )
        assert result == ["ok"]
        assert call_count == 2

    def test_retry_returns_empty_list_on_first_success(self, mock_host_with_executor, mock_ssh_session, monkeypatch):
        """Empty list from _execute_ssh_commands is a valid success result and should be returned.

        An empty list is falsy in Python, so the retry loop must not treat it
        as a failure.  Before the fix the ``if sample:`` guard would skip it,
        causing the sampler to keep retrying until timeout.
        """
        from pyhelper_utils import shell as shell_mod

        monkeypatch.setattr(shell_mod, "_execute_ssh_commands", lambda **kwargs: [])

        result = run_ssh_commands(
            host=mock_host_with_executor,
            commands=["echo", "hello"],
            wait_timeout=60,
            sleep=1,
        )
        assert result == []


class TestRunSshCommandsProxyCleanup:
    """Tests for ProxyCommand cleanup in _execute_ssh_commands."""

    def test_proxy_command_cleanup(self, mock_host, mock_ssh_session):
        """ProxyCommand socket is closed and process is reaped."""
        mock_process = MagicMock()
        mock_process.wait.return_value = 0

        proxy = MagicMock(spec=paramiko.ProxyCommand)
        proxy.process = mock_process

        executor = MagicMock()
        executor.session.return_value.__enter__ = MagicMock(return_value=mock_ssh_session)
        executor.session.return_value.__exit__ = MagicMock(return_value=False)
        executor.sock = proxy
        mock_host.executor.return_value = executor

        run_ssh_commands(host=mock_host, commands=["echo", "test"])

        proxy.close.assert_called_once()
        mock_process.wait.assert_called_once_with(timeout=5)

    def test_proxy_command_cleanup_timeout_kills(self, mock_host, mock_ssh_session):
        """When process.wait times out, process is killed."""
        mock_process = MagicMock()
        mock_process.wait.side_effect = [subprocess.TimeoutExpired("cmd", 5), None]

        proxy = MagicMock(spec=paramiko.ProxyCommand)
        proxy.process = mock_process

        executor = MagicMock()
        executor.session.return_value.__enter__ = MagicMock(return_value=mock_ssh_session)
        executor.session.return_value.__exit__ = MagicMock(return_value=False)
        executor.sock = proxy
        mock_host.executor.return_value = executor

        run_ssh_commands(host=mock_host, commands=["echo", "test"])

        proxy.close.assert_called_once()
        mock_process.kill.assert_called_once()
        assert mock_process.wait.call_count == 2

    def test_proxy_command_cleanup_oserror_on_wait(self, mock_host, mock_ssh_session):
        """OSError during process.wait is suppressed."""
        mock_process = MagicMock()
        mock_process.wait.side_effect = OSError("No child process")

        proxy = MagicMock(spec=paramiko.ProxyCommand)
        proxy.process = mock_process

        executor = MagicMock()
        executor.session.return_value.__enter__ = MagicMock(return_value=mock_ssh_session)
        executor.session.return_value.__exit__ = MagicMock(return_value=False)
        executor.sock = proxy
        mock_host.executor.return_value = executor

        # Should not raise
        run_ssh_commands(host=mock_host, commands=["echo", "test"])

    def test_no_proxy_command_no_cleanup(self, mock_host_with_executor, mock_ssh_session):
        """When sock is not ProxyCommand, no cleanup happens."""
        result = run_ssh_commands(host=mock_host_with_executor, commands=["echo", "test"])
        assert result == ["output"]


class TestRunCommand:
    """Tests for the run_command function."""

    def test_successful_command(self):
        ok, out, _err = run_command(command=["echo", "hello"])
        assert ok is True
        assert "hello" in out

    def test_failed_command_check_false(self):
        ok, _out, _err = run_command(command=["false"], check=False)
        assert ok is False

    def test_failed_command_check_true(self):
        with pytest.raises(subprocess.CalledProcessError):
            run_command(command=["false"], check=True)

    def test_stderr_with_verify(self):
        ok, _out, _err = run_command(
            command=["bash", "-c", "echo err >&2; exit 0"],
            verify_stderr=True,
            check=False,
        )
        assert ok is False

    def test_stderr_without_verify(self):
        ok, _out, _err = run_command(
            command=["bash", "-c", "echo err >&2; echo ok; exit 0"],
            verify_stderr=False,
            check=False,
        )
        assert ok is True

    def test_hide_log_command(self):
        ok, out, _err = run_command(
            command=["echo", "secret"],
            hide_log_command=True,
        )
        assert ok is True
        assert "secret" in out

    def test_log_errors_false(self):
        ok, _out, _err = run_command(
            command=["false"],
            check=False,
            log_errors=False,
        )
        assert ok is False
