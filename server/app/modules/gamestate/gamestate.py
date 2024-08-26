from types.board import Board
from types.instruction import Instruction
from utils.metaclass.singleton import Singleton


class GameState(metaclass=Singleton):
    """
    Singleton class for holding onto the game state.
    """

    board: Board = Board()
    instruction: Instruction = Instruction()

    def __init__(self):
        self.__some_val = True


