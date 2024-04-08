from pyhelper_utils.runners import function_runner_with_pdb
import pytest
import sys


@pytest.fixture
def sys_argv():
    sys.argv.append("--pdb")
    yield
    sys.argv.remove("--pdb")


@pytest.fixture
def func_with_raise():
    def _foo():
        raise ValueError()

    return _foo


@pytest.fixture
def func_with_return():
    def _foo():
        return True

    return _foo


def test_function_runner_with_raise_with_pdb(sys_argv, func_with_raise):
    assert not function_runner_with_pdb(func=func_with_raise, dry_run=True)


def test_function_runner_with_raise(func_with_raise):
    with pytest.raises(SystemExit):
        function_runner_with_pdb(func=func_with_raise)


def test_function_runner_with_return(sys_argv, func_with_return):
    assert function_runner_with_pdb(func=func_with_return)
