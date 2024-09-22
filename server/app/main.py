"""
Entry file to start the server on the Raspberry Pi.
"""
import logging
import os
import signal
import sys
from multiprocessing import Process, Event
from dotenv import load_dotenv
from modules.serial.stm32 import STM
from modules.serial.android import Android
from modules.camera.camera import Camera
from modules.gamestate import GameState
from modules.web_server.web_server import WebServer
from utils.logger import init_logger
import uvicorn


def run_web_server(ready_event) -> None:
    load_dotenv()
    init_logger()
    logging.getLogger().info("Starting server as main!")
    web_server = WebServer().get_web_server()
    ready_event.set()  # Signal that the web server is ready
    uvicorn.run(
        web_server,
        host="0.0.0.0",
        port=int(os.getenv("WEB_SERVER_PORT", 8080)),  # converts str env var to int
        log_level="debug",
        log_config=None,
    )


def run_bluetooth_server(ready_event) -> None:
    load_dotenv()
    init_logger()
    android = Android()
    ready_event.set()  # Signal that the Bluetooth server is ready
    android.run()


def run_stm(ready_event) -> None:
    load_dotenv()
    init_logger()
    stm = STM()
    stm.connect()
    ready_event.set()  # Signal that the STM is ready


def main():
    load_dotenv()
    init_logger()

    processes = []
    web_server_ready = Event()
    bluetooth_ready = Event()
    stm_ready = Event()

    def signal_handler(signum, frame):
        logging.getLogger().info(
            "Received termination signal. Shutting down gracefully..."
        )
        for process in processes:
            process.kill()

        sys.exit(0)

    # Register the signal handler for SIGINT and SIGTERM
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create the processes and pass the ready events
    server_process = Process(target=run_web_server, args=(web_server_ready,))
    bluetooth_process = Process(target=run_bluetooth_server, args=(bluetooth_ready,))
    stm_process = Process(target=run_stm, args=(stm_ready,))

    processes.extend([server_process, bluetooth_process, stm_process])

    for p in processes:
        p.start()

    # Wait for all processes to signal that they are ready
    web_server_ready.wait()
    bluetooth_ready.wait()
    stm_ready.wait()

    logging.getLogger().info("All processes initialized. Now initializing GameState.")

    # Initialize GameState and run the required task
    game_state = GameState()
    game_state._run_task_checklist_a5()

    for p in processes:
        p.join()


if __name__ == "__main__":
    main()
