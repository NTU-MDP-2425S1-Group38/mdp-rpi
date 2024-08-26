from typing import List
from fastapi import WebSocket
from utils.metaclass.singleton import Singleton


class ConnectionManager(metaclass=Singleton):

    connections: List[WebSocket]

    def __init__(self):
        self.connections = []

    async def connect(self, websocket: WebSocket) -> None:
        self.connections.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.remove(websocket)


