import subprocess
from typing import Any, List, Optional, Tuple

from simple_logger.logger import get_logger

from pyhelper_utils.exceptions import CommandExecFailed
from rrmngmnt import Host

LOGGER = get_logger(name=__name__)

TIMEOUT_30MIN = 30 * 60


def run_command(
    command: List[str],
    verify_stderr: bool = True,
    shell: bool = False,
    timeout: Optional[int] = None,
    capture_output: bool = True,
    check: bool = True,
    hide_log_command: bool = False,
    **kwargs: Any,
) -> Tuple[bool, str, str]:
    """
    Run command locally.

    Args:
        command (list): Command to run
        verify_stderr (bool, default True): Check command stderr
        shell (bool, default False): run subprocess with shell toggle
        timeout (int, optional): Command wait timeout
        capture_output (bool, default False): Capture command output
        check (bool, default True):  If check is True and the exit code was non-zero, it raises a
            CalledProcessError
        hide_log_command (bool, default False): If hide_log_command is True and check will be set to False,
            CalledProcessError will not get raise and command will not be printed.

    Returns:
        tuple: True, out if command succeeded, False, err otherwise.

    Raises:
        CalledProcessError: when check is True and command execution fails
    """
    command_for_log = ["Hide", "By", "User"] if hide_log_command else command

    LOGGER.info(f"Running {' '.join(command_for_log)} command")

    # when hide_log_command is set to True, check should be set to False to avoid logging sensitive data in
    # the exception
    sub_process = subprocess.run(
        command,
        capture_output=capture_output,
        check=check if not hide_log_command else False,
        shell=shell,
        text=True,
        timeout=timeout,
        **kwargs,
    )
    out_decoded = sub_process.stdout
    err_decoded = sub_process.stderr

    error_msg = (
        f"Failed to run {command_for_log}. rc: {sub_process.returncode}, out: {out_decoded}, error: {err_decoded}"
    )

    if sub_process.returncode != 0:
        LOGGER.error(error_msg)
        return False, out_decoded, err_decoded

    # From this point and onwards we are guaranteed that sub_process.returncode == 0
    if err_decoded and verify_stderr:
        LOGGER.error(error_msg)
        return False, out_decoded, err_decoded

    return True, out_decoded, err_decoded


def run_ssh_commands(
    host: Host,
    commands: List[str],
    get_pty: bool = False,
    check_rc: bool = True,
    timeout: int = TIMEOUT_30MIN,
    tcp_timeout: Optional[float] = None,
) -> list:
    """
    Run commands on remote host via SSH

    Args:
        host (Host): rrmngmnt host to execute the commands from.
        commands (list): List of multiple command lists [[cmd1, cmd2, cmd3]] or a list with a single command [cmd]
            Examples:
                 single command: shlex.split("sudo reboot"),
                 multiple commands: [shlex.split("sleep 5"), shlex.split("date")]

        get_pty (bool): get_pty parameter for remote session (equivalent to -t argument for ssh)
        check_rc (bool): if True checks command return code and raises if rc != 0
        timeout (int): ssh exec timeout
        tcp_timeout (float): an optional timeout (in seconds) for the TCP connect

    Returns:
        list: List of commands output.

    Raise:
        CommandExecFailed: If command failed to execute.
    """
    results: List[str] = []
    commands_list: List[List[str]] = commands if isinstance(commands[0], list) else [commands]
    with host.executor().session(timeout=tcp_timeout) as ssh_session:
        for cmd in commands_list:
            rc, out, err = ssh_session.run_cmd(cmd=cmd, get_pty=get_pty, timeout=timeout)
            LOGGER.info(f"[SSH][{host.fqdn}] Executed: {' '.join(cmd)}, rc:{rc}, out: {out}, error: {err}")
            if rc and check_rc:
                raise CommandExecFailed(name=" ".join(cmd), err=err)

            results.append(out)

    return results
