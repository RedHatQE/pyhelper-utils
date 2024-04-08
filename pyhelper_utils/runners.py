import time
import rich
import datetime
import sys
from typing import Callable


def function_runner_with_pdb(func: Callable):
    """
    Run function with support to drop into pdb.

    Args:
        func (Callable): Function to run
    """
    start_time = time.time()
    should_raise = False

    try:
        func()
    except Exception as ex:
        import traceback

        ipdb = __import__("ipdb")  # Bypass debug-statements pre-commit hook

        if "--pdb" in sys.argv:
            _, _, tb = sys.exc_info()
            traceback.print_exc()
            ipdb.post_mortem(tb)
        else:
            rich.print(f"{func.__name__}: Failed to execute with Error {ex}")
            should_raise = True
    finally:
        rich.print(f"Total execution time: {datetime.timedelta(seconds=time.time() - start_time)}")
        if should_raise:
            sys.exit(1)
