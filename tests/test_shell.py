import shlex
import subprocess
from subprocess import CalledProcessError

import paramiko
import pytest
from rrmngmnt import Host, ssh

from pyhelper_utils.exceptions import CommandExecFailed
from pyhelper_utils.shell import run_command, run_ssh_commands

ERROR_MESSAGE = "Expected value {expected}, actual value {actual}"
SUCCESSFUL_MESSAGE = "worked"
FAILURE_MESSAGE = "No such file"
TEST_COMMAND = "test"


@pytest.fixture()
def mocked_host(mocker):
    host = mocker.MagicMock(spec=Host)
    host.executor = mocker.MagicMock()
    host.executor.session = mocker.MagicMock(spec=ssh)
    return host


def test_run_command_return_true():
    rc, out, error = run_command(command=shlex.split(f"echo '{SUCCESSFUL_MESSAGE}'"), check=False)
    assert rc, ERROR_MESSAGE.format(expected=True, actual=rc)
    assert not error, ERROR_MESSAGE.format(expected="", actual="error")
    assert SUCCESSFUL_MESSAGE in out, ERROR_MESSAGE.format(expected=SUCCESSFUL_MESSAGE, actual=out)


def test_run_command_return_false():
    rc, _, _ = run_command(command=shlex.split("false"), check=False)
    assert not rc, ERROR_MESSAGE.format(expected=False, actual=rc)


def test_run_command_no_verify_raises_exception():
    with pytest.raises(CalledProcessError):
        run_command(command=shlex.split("false"), check=True, verify_stderr=False)


def test_run_command_error(mocker):
    mocker.patch(
        "pyhelper_utils.shell.subprocess.run",
        return_value=subprocess.CompletedProcess(args=None, stderr=FAILURE_MESSAGE, returncode=0, stdout=""),
    )
    rc, out, error = run_command(command=shlex.split("true"), capture_output=False, check=False, shell=True)
    assert not rc, ERROR_MESSAGE.format(expected=False, actual=rc)
    assert FAILURE_MESSAGE in error, ERROR_MESSAGE.format(expected=FAILURE_MESSAGE, actual="error")
    assert not out, ERROR_MESSAGE.format(expected="", actual=out)


def test_run_ssh_commands_command(mocked_host):
    output = "Success"
    with mocked_host.executor().session() as test_session:
        test_session.run_cmd.return_value = (False, output, None)
    result = run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)
    assert result == [output]


def test_run_ssh_commands_command_failure_check_rc(mocked_host):
    error = "error"
    commands = ["testfailed"]
    with mocked_host.executor().session() as test_session:
        test_session.run_cmd.return_value = (True, "", error)
    with pytest.raises(CommandExecFailed, match=rf"Command:(.*){commands}(.*)failed(.*)Error:(.*){error}"):
        run_ssh_commands(host=mocked_host, commands=commands, check_rc=True)


def test_run_ssh_commands_command_failure(mocked_host):
    with mocked_host.executor().session() as test_session:
        test_session.run_cmd.return_value = (True, "", None)
    result = run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)
    assert result == [""]


def test_run_ssh_commands_proxycommand_cleanup(mocked_host, mocker):
    executor = mocked_host.executor()
    mock_sock = mocker.MagicMock(spec=paramiko.ProxyCommand)
    mock_sock.process = mocker.MagicMock()
    executor.sock = mock_sock

    with executor.session() as test_session:
        test_session.run_cmd.return_value = (False, "", None)

    run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)

    mock_sock.close.assert_called_once()
    mock_sock.process.wait.assert_called_once_with(timeout=5)


def test_run_ssh_commands_proxycommand_cleanup_timeout(mocked_host, mocker):
    executor = mocked_host.executor()
    mock_sock = mocker.MagicMock(spec=paramiko.ProxyCommand)
    mock_sock.process = mocker.MagicMock()
    mock_sock.process.wait.side_effect = [subprocess.TimeoutExpired(cmd="proxy", timeout=5), None]
    executor.sock = mock_sock

    with executor.session() as test_session:
        test_session.run_cmd.return_value = (False, "", None)

    run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)

    mock_sock.close.assert_called_once()
    mock_sock.process.kill.assert_called_once()
    assert mock_sock.process.wait.call_count == 2


def test_run_ssh_commands_proxycommand_cleanup_kill_failure(mocked_host, mocker):
    executor = mocked_host.executor()
    mock_sock = mocker.MagicMock(spec=paramiko.ProxyCommand)
    mock_sock.process = mocker.MagicMock()
    mock_sock.process.wait.side_effect = subprocess.TimeoutExpired(cmd="proxy", timeout=5)
    mock_sock.process.kill.side_effect = OSError("kill failed")
    executor.sock = mock_sock

    with executor.session() as test_session:
        test_session.run_cmd.return_value = (False, "", None)

    run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)

    mock_sock.close.assert_called_once()
    mock_sock.process.kill.assert_called_once()


def test_run_ssh_commands_proxycommand_cleanup_unexpected_exception(mocked_host, mocker):
    executor = mocked_host.executor()
    mock_sock = mocker.MagicMock(spec=paramiko.ProxyCommand)
    mock_sock.process = mocker.MagicMock()
    mock_sock.process.wait.side_effect = OSError("unexpected")
    executor.sock = mock_sock

    with executor.session() as test_session:
        test_session.run_cmd.return_value = (False, "", None)

    run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)

    mock_sock.close.assert_called_once()
    mock_sock.process.kill.assert_not_called()


def test_run_ssh_commands_no_proxycommand(mocked_host, mocker):
    executor = mocked_host.executor()
    mock_sock = mocker.MagicMock()
    executor.sock = mock_sock

    with executor.session() as test_session:
        test_session.run_cmd.return_value = (False, "", None)

    run_ssh_commands(host=mocked_host, commands=[TEST_COMMAND], check_rc=False)

    mock_sock.close.assert_not_called()
