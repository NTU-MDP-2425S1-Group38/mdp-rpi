import asyncio
import logging
from asyncio import Future
from collections import defaultdict
from typing import List, Optional, Dict, Set, Coroutine
from uuid import uuid4

from fastapi import WebSocket

from app_types.data.slave_models import SlaveObstacle, SlaveWorkRequest, SlaveWorkRequestType, \
    SlaveWorkRequestPayloadAlgo, SlaveWorkRequestPayloadImageRecognition
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

    """
    PRIVATE METHODS
    """

    def _run_async(self, coro: Coroutine):
        self.logger.info("Attempting to run async coroutine")
        try:
            loop = asyncio.get_running_loop()
            self.logger.info("Event loop is running, creating task")
        except RuntimeError:
            self.logger.warning("No running loop, setting up a new temporary loop")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(coro)
            loop.close()
            return result

        # If the loop is running, we schedule the coroutine as a task and wait for its result safely.
        if loop.is_running():
            task = asyncio.create_task(coro)
            return asyncio.run_coroutine_threadsafe(task, loop).result()
        else:
            return loop.run_until_complete(coro)


    """
    ALGO RELATED STUFF
    """

    async def _broadcast_algo_req(self, req_id:str, obstacles: List[Obstacle]) -> List[Command]:

        if not self.connections:
            self.logger.error("No slave connections available to process algo!")
            return []

        req = SlaveWorkRequest(
            id=req_id,
            type=SlaveWorkRequestType.Algorithm,
            payload=SlaveWorkRequestPayloadAlgo(obstacles=[SlaveObstacle(**i.model_dump()) for i in obstacles])
        ).model_dump_json()

        async def send_and_receive(websocket: WebSocket) -> Optional[CvResponse]:
            await websocket.send_text(req)
            response = await websocket.receive_json()
            try:
                parsed = CvResponse(**response)
                if parsed.id != req_id:
                    self.logger.warning("Race condition! Received a mismatched ID from request!")
                    return None

                return parsed
            except ValidationError:
                self.logger.error("Unable to parse CvResponse!")
                return None

        tasks = [asyncio.create_task(send_and_receive(conn)) for conn in self.connections]

        # Await for the first non-null response
        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                result = await task
                if result:  # Check if the result is non-null
                    # Cancel any remaining tasks since we have a valid result
                    for pending_task in pending:
                        pending_task.cancel()
                    return result

            # If no valid result, keep waiting for other tasks
            tasks = list(pending)


    def slave_request_algo(self, obstacles: List[Obstacle]) -> List[Command]:
        self.logger.info("Sending Algo request to slaves!")
        return asyncio.run(self._broadcast_algo_req(str(uuid4()), obstacles))

    """
    CV RELATED STUFF
    """

    async def _broadcast_cv_req(self, req_id:str, image: str) -> Optional[ObstacleLabel]:

        self.logger.info("Entering _broadcast_cv_req")

        if not self.connections:
            self.logger.error("No slave connections available to process cv!")
            return ObstacleLabel.Unknown

        req = SlaveWorkRequest(
            id=req_id,
            type=SlaveWorkRequestType.Algorithm,
            payload=SlaveWorkRequestPayloadImageRecognition(image=image)
        ).model_dump_json()

        self.logger.info(f"Created request object!")

        async def send_and_receive(websocket: WebSocket) -> Optional[CvResponse]:
            await websocket.send_text(req)
            self.logger.info("Sending request to slave!")
            response = await websocket.receive_json()
            try:
                parsed = CvResponse(**response)
                if parsed.id != req_id:
                    self.logger.warning("Race condition! Received a mismatched ID from request!")
                    return None

                return parsed
            except ValidationError:
                self.logger.error("Unable to parse CvResponse!")
                return None


        tasks = [send_and_receive(conn) for conn in self.connections]

        # Await for the first non-null response
        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                result = await task
                if result:  # Check if the result is non-null
                    # Cancel any remaining tasks since we have a valid result
                    for pending_task in pending:
                        pending_task.cancel()
                    return result

            # If no valid result, keep waiting for other tasks
            tasks = list(pending)

    def slave_request_cv(self, image: str) -> Optional[ObstacleLabel]:
        self.logger.info("Sending CV request to slaves!")
        return self._run_async(self._broadcast_cv_req(str(uuid4()), image))


