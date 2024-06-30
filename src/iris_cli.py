import shubhlipi as sh

DEFAULT_TEMP = 6500
DEFAULT_BRIGHT = 100
TOOL_PATH = "./resources/iris-micro-linux-0.0.7/iris-micro.sh"


def iris_cli(temp: int, bright: int):
    """Calls the actual cli app to set the temperature and brightness"""
    command = f"{TOOL_PATH} {temp} {bright}"
    sh.cmd(command, display=False)


def reset_cli():
    """Reset cli"""
    iris_cli(DEFAULT_TEMP, DEFAULT_BRIGHT)
