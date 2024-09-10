import logging
from time import strftime, localtime

from fastapi import APIRouter

from modules.gamestate.gamestate import GameState

rest_endpoints = APIRouter()


@rest_endpoints.get("/")
async def index():
    return f"Hello the time now is {strftime('%Y-%m-%d_%H-%M-%S', localtime())}"



@rest_endpoints.post("/command/capture")
async def capture():
    """
    Endpoint to trigger the GameState class to take a picture and send to slaves
    :return:
    """
    logger = logging.getLogger("/command/capture")
    logger.info("Received capture command")
    GameState().capture_and_process_image()
