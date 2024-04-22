import shlex
from subprocess import CalledProcessError
import pytest
import subprocess
from pyhelper_utils.exceptions import CommandExecFailed
from pyhelper_utils.shell import run_command, run_ssh_commands
from rrmngmnt import Host, ssh

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
