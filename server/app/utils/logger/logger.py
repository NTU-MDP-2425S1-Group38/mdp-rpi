import logging
import os
from time import localtime, strftime


def init_logger() -> None:
    logging.basicConfig(
        filename=f"{os.path.dirname(__file__)}/../../logs/{strftime('%Y-%m-%d_%H-%M-%S', localtime())}.log",
        level=logging.DEBUG
    )
