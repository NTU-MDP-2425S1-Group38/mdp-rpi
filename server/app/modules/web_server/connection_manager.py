import asyncio
import logging
from asyncio import Future
from collections import defaultdict
from typing import List, Optional, Dict, Set, Coroutine, Callable, Union
from uuid import uuid4

from fastapi import WebSocket

from app_types.data.slave_models import (
    SlaveObstacle,
    SlaveWorkRequest,
    SlaveWorkRequestType,
    SlaveWorkRequestPayloadAlgo,
    SlaveWorkRequestPayloadImageRecognition,
)
from app_types.obstacle import Obstacle
from app_types.primatives.command import Command, AlgoCommandResponse
from app_types.primatives.cv import CvResponse
from app_types.primatives.obstacle_label import ObstacleLabel
from utils.metaclass.singleton import Singleton
from pydantic import ValidationError


class ConnectionManager(metaclass=Singleton):
    connections: List[WebSocket] = []
    observers: List[WebSocket] = []
    logger = logging.getLogger("Connection Manager")
    pending_responses: Dict[
        str, Callable[[Union[AlgoCommandResponse, CvResponse]], None]
    ] = {}

    async def connect(self, websocket: WebSocket) -> None:
        logging.getLogger().info(
            "Adding websocket to all connections in ConnectionManager"
        )
        self.connections.append(websocket)

    async def observer(self, websocket: WebSocket) -> None:
        logging.getLogger().info("Adding websocket to observers in ConnectionManager")
        self.observers.append(websocket)

    def remove_connection(self, websocket: WebSocket) -> None:
        logging.getLogger().info("Removing websocket connection from ConnectionManager")
        self.connections.remove(websocket)

    def remove_observer(self, websocket: WebSocket) -> None:
        logging.getLogger().info("Removing websocket observer from ConnectionManager")
        self.observers.remove(websocket)

    """
    PRIVATE METHODS
    """

    # def _run_async(self, coro: Coroutine):
    #     loop = asyncio.get_event_loop()
    #     if loop.is_running():
    #         return asyncio.create_task(coro)
    #     else:
    #         return loop.run_until_complete(coro)

    def _run_async(self, coro):
        try:
            self.logger.info("Attempting to run async coroutine")
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            asyncio.ensure_future(coro, loop=loop)
        else:
            loop.run_until_complete(coro)

    """
    ALGO RELATED STUFF
    """

    async def _broadcast_algo_req(
        self, req_id: str, obstacles: List[Obstacle]
    ) -> List[Command]:
        if not self.connections:
            self.logger.error("No slave connections available to process algo!")
            return []

        req = SlaveWorkRequest(
            id=req_id,
            type=SlaveWorkRequestType.Algorithm,
            payload=SlaveWorkRequestPayloadAlgo(
                obstacles=[SlaveObstacle(**i.model_dump()) for i in obstacles]
            ),
        ).model_dump_json()

        tasks = [asyncio.create_task(c.send_text(req)) for c in self.connections]

        await asyncio.gather(*tasks)

    def handle_algo_response_callback(self, response: AlgoCommandResponse) -> None:
        self.logger.info(f"Activating algo callback for {response.id}")
        if response.id in self.pending_responses.keys():
            self.logger.info(f"Running callback for {response.id}")
            self.pending_responses[response.id](response)
            self.pending_responses.pop(response.id, None)
            return
        self.logger.info(
            f"Matching callback no longer found for {response.id}! Has it been executed?"
        )

    def slave_request_algo(
        self, obstacles: List[Obstacle], callback: Callable[[AlgoCommandResponse], None]
    ) -> None:
        self.logger.info("Sending Algo request to slaves!")
        req_id = str(uuid4())
        self.pending_responses[req_id] = callback
        asyncio.run(self._broadcast_algo_req(req_id, obstacles))
        # TODO implement callback logic

    """
    CV RELATED STUFF
    """

    async def _broadcast_cv_req(self, req_id: str, image: str, ignore_bullseye: bool) -> None:
        self.logger.info("Entering _broadcast_cv_req")

        if not self.connections:
            self.logger.error("No slave connections available to process cv!")
            return None

        req = SlaveWorkRequest(
            id=req_id,
            type=SlaveWorkRequestType.ImageRecognition,
            payload=SlaveWorkRequestPayloadImageRecognition(
                image=image,
                ignore_bullseye=ignore_bullseye
            ),
        ).model_dump_json()

        tasks = [asyncio.create_task(c.send_text(req)) for c in self.connections]

        await asyncio.gather(*tasks)

    def handle_cv_response_callback(self, response: CvResponse) -> None:
        self.logger.info(f"Activating CV callback for {response.id}")
        if response.id in self.pending_responses.keys():
            self.logger.info(f"Running callback for {response.id}")
            self.pending_responses[response.id](response)
            self.pending_responses.pop(response.id, None)
            return
        self.logger.info(
            f"Matching callback no longer found for {response.id}! Has it been executed?"
        )

    def slave_request_cv(
        self, image: str, callback: Callable[[CvResponse], None], ignore_bullseye:bool = False
    ) -> None:
        """
        :param image: base64 string of image
        :param callback: callback function that takes `CvResponse` as the only arg, and returns None.
        :param ignore_bullseye: Specify if bullseye detections should be ignored.
        :return: None
        """
        self.logger.info("Sending CV request to slaves!")
        req_id = str(uuid4())
        self.pending_responses[req_id] = callback
        self._run_async(self._broadcast_cv_req(req_id, image, ignore_bullseye))
