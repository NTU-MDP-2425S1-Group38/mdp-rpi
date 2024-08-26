"""
Entry file to start the server on the Raspberry Pi.
"""
import logging
import os
from multiprocessing import Process
from dotenv import load_dotenv

from modules.web_server.web_server import WebServer
from utils.logger import init_logger
import uvicorn


def run_web_server() -> None:
    load_dotenv()
    init_logger()
    logging.getLogger().info('Starting server as main!')
    web_server = WebServer().get_web_server()
    uvicorn.run(
        web_server,
        host="0.0.0.0",
        port=int(os.getenv("WEB_SERVER_PORT", 8080)),  # converts str env var to int
        log_level="debug",
        log_config=None
    )



def main():
    load_dotenv()
    init_logger()

    server_process = Process(target=run_web_server)

    server_process.start()

    server_process.join()


if __name__ == "__main__":
    main()
