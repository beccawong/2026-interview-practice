# Grid of X, Y
# Some squres have bombs of Z number (0,3)
# User click on a cell, if no bomb, it opens adjacent squares
# A cell can be flagged, revealed, bomb, unopen
import random
import typing
from dataclasses import dataclass


@dataclass
class Cell:
    original_val: str | None
    current_state: str | None

    def __str__(self) -> str:
        return f"({self.original_val}, {self.current_state})"
    def __repr__(self) -> str:
        return f"({self.original_val}, {self.current_state})"

class Game:
    BOMB = "B"
    FLAG = "F"
    OPENED = "O"
    DIRS: typing.ClassVar = [(dr, dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1) if (dr, dc) != (0, 0)]

    def __init__(self, rows: int, cols: int):
        val_choices: list[str | None] = [None, self.BOMB]
        self.board = [
            [Cell(random.choices(val_choices, [70, 30])[0], None) for _ in range(cols)]
            for _ in range(rows)
        ]

    def turn(self, action: str, row: int, col: int) -> typing.Literal['C', 'L' ,'W']:
        if action == self.OPENED and self.board[row][col].original_val == self.BOMB:
            print("Game over. You hit a bomb")
            return 'L'

        if action == self.FLAG:
            self.board[row][col].current_state = self.FLAG

        if action == self.OPENED:
            self.board[row][col].current_state = Game.OPENED
            self._open_cell(row, col)

        still_in_game = False
        for r in self.board:
            still_in_game = still_in_game or any(cell.current_state is None and cell.original_val != self.BOMB for cell in r)
            if still_in_game:
                return 'C'
            
        return 'W'

    def _open_cell(self, row: int, col: int) -> None:
        if row < 0 or col < 0:
            return

        to_visit = [(row, col)]
        while to_visit:
            cell = to_visit.pop()
            bomb_count = 0
            valid_neighbors = []
            for neighbors in Game.DIRS:
                n_row = cell[0] + neighbors[0]
                n_col = cell[1] + neighbors[1]
                if 0 <= n_row < len(self.board) and 0 <= n_col < len(self.board[0]):
                    if self.board[n_row][n_col].original_val == self.BOMB:
                        bomb_count += 1
                    else:
                        if self.board[n_row][n_col].current_state is None:
                            valid_neighbors.append((n_row, n_col))

            if bomb_count and self.board[cell[0]][cell[1]].current_state is None:
                self.board[cell[0]][cell[1]].current_state = str(bomb_count)
            else:
                self.board[cell[0]][cell[1]].current_state = self.OPENED
                to_visit.extend(valid_neighbors)

    def print_state(self):
        for row in self.board:
            print(row)


g = Game(4, 4)
g.print_state()
game_on = True
while game_on:
    row = int(input("Pick a row: "))
    col = int(input("Pick a col: "))
    action = input("Pick action (O or F): ")

    game_on = g.turn(action, row, col)
    g.print_state()
