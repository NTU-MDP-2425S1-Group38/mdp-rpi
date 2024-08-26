import logging

from fastapi import APIRouter, WebSocket

from modules.web_server.connection_handler import connection_handler
from modules.web_server.connection_manager import ConnectionManager

socket_endpoints = APIRouter()


@socket_endpoints.websocket("/connect")
async def connect(websocket: WebSocket):
    """
    Endpoint for adding "slaves"
    """
    logging.getLogger().info("New WS connection")
    await websocket.accept()
    await ConnectionManager().connect(websocket)
    await connection_handler(websocket)


@socket_endpoints.websocket("/observe")
async def observe(websocket: WebSocket):
    """
    Endpoint to add register as an observer
    """
    logging.getLogger().info("New WS observer")
    await websocket.accept()
    await ConnectionManager().observer(websocket)
