from abc import ABC, abstractmethod
from typing import Literal


class StmCommand(ABC):

    @abstractmethod
    def to_serial(self) -> str:
        """
        Method to serialise the method into a string to be sent to the STM
        :return:
        """
        raise NotImplementedError



class StmMoveToDistance(StmCommand):

    def __init__(self, distance: int, forward:bool=True, speed:int=40):
        """
        :param distance: Distance to move to.
        :param forward: True if the robot should move forward to specified distance
        :param speed: Speed the robot should move
        """
        self.distance = distance
        self.forward = forward
        self.speed = speed

    def to_serial(self) -> str:
        flag = "W" if self.forward else "w"
        # "W/w{SPEED}|{ANGLE}|{DISTANCE}
        return f"{flag}{round(self.speed,2)}|0|{round(self.distance,2)}\n"


class StmMove(StmCommand):
    """
    Command to move forward
    """

    def __init__(
            self,
            distance: int,
            forward: bool = True,
            angle: int = 0,
            speed: int = 55
    ):
        self.distance = distance
        self.forward = forward
        self.angle = angle
        self.speed = speed

    def to_serial(self) -> str:
        flag = "T" if self.forward else "t"
        # "T/t{SPEED}|{ANGLE}|{DISTANCE}
        return f"{flag}{self.speed}|{round(self.angle,2)}|{round(self.distance,2)}\n"


class StmWiggle(StmCommand):

    def to_serial(self) -> str:
        return StmMove(0, angle=-20, speed=0).to_serial()


class StmTurn(StmCommand):

    def __init__(
            self,
            angle: int,
            speed: int,
            forward: bool = True
    ):
        self.angle = angle
        self.speed = speed
        self.forward = forward

    def to_serial(self) -> str:

        servo_angle = 0

        if self.angle != 0:
            if self.angle < 0:
                servo_angle = -25
            else:
                servo_angle = 25

        # the resultant angle is scaled due to servo issues
        return StmMove(distance=int(0.98*(abs(self.angle))), angle=servo_angle, speed=self.speed).to_serial()


class StmStraight(StmCommand):

    def __init__(
            self,
            distance: int,
            speed: int,
            forward: bool = True
    ):
        self.distance = distance
        self.speed = speed
        self.forward = forward

    def to_serial(self) -> str:
        return StmMove(distance=self.distance, angle=0, speed=self.speed, forward=self.forward).to_serial()


class StmToggleMeasure(StmCommand):

    def to_serial(self) -> str:
        return "D\n"


class StmSideHug(StmCommand):

    def __init__(
            self,
            side: Literal["left", "right"],
            threshold: int,
            speed: int,
            forward: bool = True
    ):
        """
        Command to use the IR sensor to "hug" the obstacles.
        :param side: Literal["left","right"] to set which side sensor to use
        :param threshold: Distance to be detected, robot will stop after distance detected is >= threshold.
        :param speed: Speed for the robot to move
        :param forward: Self explanatory
        """

        self.side = side
        self.threshold = threshold
        self.speed = speed
        self.forward = forward

    def to_serial(self) -> str:

        flag = "L" if self.side == "left" else "R"
        if not self.forward:
            flag = flag.lower()

        # format
        # flag, speed, angle, threshold distance
        return f"{flag}{self.speed}|0|{self.threshold}\n"














