import logging
from typing import List
from fastapi import WebSocket
from utils.metaclass.singleton import Singleton


class ConnectionManager(metaclass=Singleton):

    connections: List[WebSocket] = []
    observers: List[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        logging.getLogger().info("Adding websocket to all connections in ConnectionManager")
        self.connections.append(websocket)

    async def observer(self, websocket: WebSocket) -> None:
        logging.getLogger().info("Adding websocket to observers in ConnectionManager")
        self.observers.append(websocket)

    def remove_connection(self, websocket: WebSocket) -> None:
        logging.getLogger().info("Removing websocket connection from ConnectionManager")
        self.connections.remove(websocket)

    def remove_observer(self, websocket:WebSocket) -> None:
        logging.getLogger().info("Removing websocket observer from ConnectionManager")
        self.observers.remove(websocket)

