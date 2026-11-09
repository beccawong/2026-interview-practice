"""
Crossword Puzzle Solver (single machine).

Board format
------------
    '#'  blocked cell
    '_'  empty cell to fill
    'A'  pre-filled letter

Approach
--------
1. Derive slots (maximal horizontal / vertical runs of >= 2 open cells) and
   give them standard crossword numbers (row-major scan; a cell gets a number
   if it starts an Across or Down slot).
2. Treat it as a constraint-satisfaction problem:
     variables   = slots
     domain      = dictionary words of the slot's length
     constraints = crossing cells must share a letter, pre-filled letters
                   must match, each word used at most once.
3. Backtracking search with:
     - MRV (minimum remaining values): always fill the slot with the fewest
       candidate words next -> fails fast, prunes hugely.
     - Forward checking: after placing a word, make sure every crossing
       slot still has at least one candidate; otherwise undo immediately.
     - An index (length, position, letter) -> set(words) so candidate lookup
       is a set intersection instead of a scan of the whole dictionary.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

BLOCK = "#"
EMPTY = "_"


@dataclass
class Slot:
    number: int
    direction: str  # "Across" | "Down"
    start_row: int
    start_col: int
    length: int
    word: str | None = None  # filled in by the solver

    def cells(self) -> list[tuple[int, int]]:
        dr, dc = (0, 1) if self.direction == "Across" else (1, 0)
        return [(self.start_row + dr * i, self.start_col + dc * i) for i in range(self.length)]


@dataclass
class Crossword:
    board: list[list[str]]
    clues: dict[str, str]  # word -> clue
    slots: list[Slot] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.board = [[ch.upper() for ch in row] for row in self.board]
        self.clues = {w.upper(): c for w, c in self.clues.items()}
        self.rows, self.cols = len(self.board), len(self.board[0]) if self.board else 0
        self.slots = self._find_slots()
        self.used: set[str] = set()

        # cell -> [(slot_index, position_in_slot)], used for crossing checks
        self.cell_to_slots: dict[tuple[int, int], list[tuple[int, int]]] = defaultdict(list)
        for si, slot in enumerate(self.slots):
            for pos, cell in enumerate(slot.cells()):
                self.cell_to_slots[cell].append((si, pos))

        # Indexes for fast candidate lookup.
        self.by_length: dict[int, set[str]] = defaultdict(set)
        self.by_pos_letter: dict[tuple[int, int, str], set[str]] = defaultdict(set)
        for w in self.clues:
            self.by_length[len(w)].add(w)
            for i, ch in enumerate(w):
                self.by_pos_letter[(len(w), i, ch)].add(w)

    # ------------------------------------------------------------------ setup
    def _open(self, r: int, c: int) -> bool:
        return 0 <= r < self.rows and 0 <= c < self.cols and self.board[r][c] != BLOCK

    def _find_slots(self) -> list[Slot]:
        slots: list[Slot] = []
        number = 0
        for r in range(self.rows):
            for c in range(self.cols):
                if not self._open(r, c):
                    continue
                starts_across = not self._open(r, c - 1) and self._open(r, c + 1)
                starts_down = not self._open(r - 1, c) and self._open(r + 1, c)
                if not (starts_across or starts_down):
                    continue
                number += 1
                if starts_across:
                    length = 0
                    while self._open(r, c + length):
                        length += 1
                    slots.append(Slot(number, "Across", r, c, length))
                if starts_down:
                    length = 0
                    while self._open(r + length, c):
                        length += 1
                    slots.append(Slot(number, "Down", r, c, length))
        return slots

    # ------------------------------------------------------------- candidates
    def _candidates(self, slot: Slot) -> set[str]:
        """Unused words that match the slot's length and any letters already on the board."""
        result = self.by_length.get(slot.length, set())
        for pos, (r, c) in enumerate(slot.cells()):
            ch = self.board[r][c]
            if ch != EMPTY:
                result = result & self.by_pos_letter.get((slot.length, pos, ch), set())
                if not result:
                    return set()
        return result - self.used

    # ------------------------------------------------------ place / undo word
    def fit_word(self, word: str, slot: Slot) -> list[tuple[int, int]] | None:
        """Write `word` into `slot`. Returns the cells that changed (previously
        empty), or None if the word conflicts with existing letters."""
        cells = slot.cells()
        if any(self.board[r][c] not in (EMPTY, word[i]) for i, (r, c) in enumerate(cells)):
            return None
        changed = []
        for i, (r, c) in enumerate(cells):
            if self.board[r][c] == EMPTY:
                self.board[r][c] = word[i]
                changed.append((r, c))
        return changed

    def _undo_word(self, changed: list[tuple[int, int]]) -> None:
        for r, c in changed:
            self.board[r][c] = EMPTY

    def _crossings_still_viable(self, changed: list[tuple[int, int]]) -> bool:
        """Forward check: every unfilled slot crossing a newly written cell
        must still have at least one candidate."""
        for cell in changed:
            for si, _ in self.cell_to_slots[cell]:
                other = self.slots[si]
                if other.word is None and not self._candidates(other):
                    return False
        return True

    # ------------------------------------------------------------------ solve
    def solve(self) -> bool:
        unfilled = [s for s in self.slots if s.word is None]
        if not unfilled:
            return True

        # MRV: pick the most constrained slot.
        best, best_cands = None, None
        for s in unfilled:
            cands = self._candidates(s)
            if not cands:
                return False  # dead end
            if best_cands is None or len(cands) < len(best_cands):
                best, best_cands = s, cands
                if len(cands) == 1:
                    break

        assert best is not None and best_cands is not None
        for word in sorted(best_cands):  # sorted -> deterministic output
            changed = self.fit_word(word, best)
            if changed is None:
                continue
            best.word = word
            self.used.add(word)
            if self._crossings_still_viable(changed) and self.solve():
                return True
            self.used.discard(word)
            best.word = None
            self._undo_word(changed)
        return False

    # ----------------------------------------------------------------- output
    def answers(self) -> list[str]:
        ordered = sorted(self.slots, key=lambda s: (s.number, s.direction != "Across"))
        return [f"{s.number} {s.direction}: {self.clues[s.word]} -> {s.word}" for s in ordered if s.word]

    def render(self) -> str:
        return "\n".join(" ".join(row) for row in self.board)


def parse_board(lines: list[str]) -> list[list[str]]:
    return [list(line.replace(" ", "")) for line in lines]


if __name__ == "__main__":
    words = {
        "TIRE": "A wheel on a car",
        "RATS": "Small rodents",
        "BATH": "A tub to clean in",
        "BE": "To, or not to",
        # decoys, to show the solver has to choose
        "TARS": "Sailors",
        "BOTH": "The two together",
        "ME": "Myself",
    }
    # 1 = TIRE (down), 2 = RATS (across), 3 = BE (across) / BATH (down).
    # 'T' in RATS is pre-filled.
    board = parse_board([
        "# _ # # #",
        "# _ # # #",
        "# _ _ T _",
        "_ _ # # #",
        "_ # # # #",
        "_ # # # #",
        "_ # # # #",
    ])

    puzzle = Crossword(board, words)
    if puzzle.solve():
        print("\n".join(puzzle.answers()))
        print()
        print(puzzle.render())
    else:
        print("No solution")
