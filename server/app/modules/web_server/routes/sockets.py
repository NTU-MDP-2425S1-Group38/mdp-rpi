import logging

from fastapi import APIRouter, WebSocket

from modules.web_server.connection_handler import connection_handler
from modules.web_server.connection_manager import ConnectionManager

from modules.serial.stm32 import STM
from modules.gamestate import GameState

socket_endpoints = APIRouter()


@socket_endpoints.websocket("/connect")
async def connect(websocket: WebSocket):
    """
    Endpoint for adding "slaves"
    """
    logging.getLogger().info("New WS connection")
    await websocket.accept()
    await ConnectionManager().connect(websocket)
    # Initialize GameState and run the required task
    game_state = GameState()
    game_state._run_task_checklist_a5()
    await connection_handler(websocket)


@socket_endpoints.websocket("/observe")
async def observe(websocket: WebSocket):
    """
    Endpoint to add register as an observer
    """
    logging.getLogger().info("New WS observer")
    await websocket.accept()
    await ConnectionManager().observer(websocket)


@socket_endpoints.websocket("/stm-command")
async def stm_command(websocket: WebSocket):
    """
    WebSocket endpoint to send commands to the STM32.
    Expects a comma-separated string format: "flag,speed,angle,val".
    """
    stm = STM()
    stm.connect()
    logging.getLogger().info("New STM command connection")
    await websocket.accept()

    while True:
        data = await websocket.receive_text()
        logging.getLogger().info(f"Received command: {data}")

        # Parse the received data (assuming format: "flag,speed,angle,val")
        try:
            flag, speed, angle, val = data.split(",")
            speed = int(speed)
            angle = int(angle)
            val = int(val)

            # Call the send_cmd function
            stm.send_cmd(flag, speed, angle, val)

            # Send a confirmation back to the client
            await websocket.send_text(f"Command sent: {data}")
        except ValueError as e:
            # Handle parsing errors
            error_msg = f"Invalid data format: {data}. Error: {str(e)}"
            logging.getLogger().error(error_msg)
            await websocket.send_text(error_msg)
