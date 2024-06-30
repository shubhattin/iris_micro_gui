import os
import subprocess as sub


DEFAULT_TEMP = 6500
DEFAULT_BRIGHT = 100

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TOOL_PATH = os.path.join(CURRENT_DIR, "resources/iris-micro-linux-0.0.7/iris-micro.sh")


def iris_cli(temp: int, bright: int):
    """Calls the actual cli app to set the temperature and brightness"""

    with sub.Popen(
        [TOOL_PATH, str(temp), str(bright)],
        stderr=sub.STDOUT,
        stdout=sub.PIPE,
        # bufsize=1,  # unbuffered, so will show as soon as possible
        universal_newlines=True,
    ) as process:
        process.wait()
        return process.returncode


def reset_cli():
    """Reset cli"""
    iris_cli(DEFAULT_TEMP, DEFAULT_BRIGHT)
