"""
Entry file to start the server on the Raspberry Pi.
"""
import logging

from utils.logger import init_logger

init_logger()


if __name__ == "__main__":
    logging.getLogger(__name__).info('Starting server!')
