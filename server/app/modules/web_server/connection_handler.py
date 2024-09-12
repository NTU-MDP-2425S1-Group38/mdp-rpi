from fastapi import WebSocket, WebSocketDisconnect

from modules.web_server.connection_manager import ConnectionManager


async def connection_handler(websocket: WebSocket):
    """
    Function to handle processing of websockets
    :param websocket:
    :return:
    """

    try:
        while True:
            pass
            # data = await websocket.receive_text()
            # await websocket.send_text(data)
    except WebSocketDisconnect:
        ConnectionManager().remove_connection(websocket)

