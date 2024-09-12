import logging

from fastapi import WebSocket, WebSocketDisconnect

from app_types.primatives.cv import CvResponse
from app_types.primatives.command import AlgoCommandResponse
from modules.web_server.connection_manager import ConnectionManager


async def connection_handler(websocket: WebSocket):
    """
    Function to handle processing of websockets
    :param websocket:
    :return:
    """
    logger = logging.getLogger("Handler")
    try:
        while True:
            data = await websocket.receive_json()
            logger.info(f"Received: {data}")
            
            if "label" in data.keys():
                logger.info("Parsing data as CvResponse")
                cvRes = CvResponse.model_validate(data)
                ConnectionManager().handle_cv_response_callback(cvRes)
            if "commands" in data.keys():
                logger.info("Parsing data as AlgoCommandResponse")
                algoRes = AlgoCommandResponse.model_validate(data)
                ConnectionManager().handle_algo_response_callback(algoRes)

            # await websocket.send_text(data)
    except WebSocketDisconnect:
        ConnectionManager().remove_connection(websocket)

