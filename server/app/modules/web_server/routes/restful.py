import logging
from time import strftime, localtime

from fastapi import APIRouter

from modules.camera.camera import Camera
from modules.gamestate.gamestate import GameState

rest_endpoints = APIRouter()
logger = logging.getLogger("/command/capture")


@rest_endpoints.get("/")
async def index():
    logger.info("Return base route")
    return f"Hello the time now is {strftime('%Y-%m-%d_%H-%M-%S', localtime())}"



@rest_endpoints.post("/command/capture")
async def capture():
    """
    Endpoint to trigger the GameState class to take a picture and send to slaves
    :return:
    """
    logger.info("Received capture command")
    # state = GameState().capture_and_process_image()
    # return state
    cam = Camera()
    cam.capture()
    return ""
