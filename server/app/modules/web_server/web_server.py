from typing import Optional

from fastapi import FastAPI

from modules.web_server.routes.restful import rest_endpoints
from modules.web_server.routes.sockets import socket_endpoints
from utils.metaclass.singleton import Singleton


class WebServer(metaclass=Singleton):

    __web_server: Optional[FastAPI] = None


    def get_web_server(self) -> FastAPI:
        """
        Method to return a single reference to the fast API server.
        :return: FastAPI instance
        """

        # If instance already exists
        if self.__web_server:
            return self.__web_server

        # Create new instance of fast API
        app = FastAPI()

        # Register routes
        app.include_router(rest_endpoints)
        app.include_router(socket_endpoints, prefix="/ws")

        self.__web_server = app
        return self.__web_server

