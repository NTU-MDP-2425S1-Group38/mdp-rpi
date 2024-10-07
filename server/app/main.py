"""
Entry file to start the server on the Raspberry Pi.
"""
import logging
import os
import signal
import sys
import threading
from multiprocessing import Process, Event
from typing import List

from dotenv import load_dotenv
from modules.serial.stm32 import STM
from modules.serial.android import Android
from modules.web_server.web_server import WebServer
from utils.logger import init_logger
import uvicorn


def run_web_server() -> None:
    load_dotenv()
    init_logger()
    logging.getLogger().info("Starting server as main!")
    web_server = WebServer().get_web_server()
    uvicorn.run(
        web_server,
        host="0.0.0.0",
        port=int(os.getenv("WEB_SERVER_PORT", 8080)),  # converts str env var to int
        log_level="debug",
        log_config=None,
    )


def run_bluetooth_server() -> None:
    load_dotenv()
    init_logger()
    android = Android()
    android.run()


def run_stm() -> None:
    load_dotenv()
    init_logger()
    stm = STM()
    stm.connect()


def main():
    load_dotenv()
    init_logger()

    threads:List[threading.Thread] = []


    def signal_handler(signum, frame):
        logging.getLogger().info(
            "Received termination signal. Shutting down gracefully..."
        )

        sys.exit(0)

    # Register the signal handler for SIGINT and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create the threads and pass the ready events
    server_process = threading.Thread(target=run_web_server)
    bluetooth_process = threading.Thread(target=run_bluetooth_server)
    stm_process = threading.Thread(target=run_stm)

    threads.extend([server_process, bluetooth_process, stm_process])

    for p in threads:
        p.start()

    for p in threads:
        p.join()


if __name__ == "__main__":
    main()
