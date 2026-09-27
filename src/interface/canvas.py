import sys
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, replace

from .interface import Interface as Core
from .visual_consts import Elements


@dataclass(slots=True)
class CanvasCell:
    """ Store the display and saved state of one canvas cell. """
    ch: str = " "
    color: str = ""
    utf_cont: bool = False
    built_ch: str = ""
    built_color: str = ""
    built_utf_cont: bool = False


class Canvas:
    """ Manage and render a terminal canvas backed by a matrix of cells. """
    def __init__(
            self,
            core: Core,
            width: int,
            height: int,
            default: CanvasCell | None = None,
            ) -> None:
        """ Initialize the canvas dimensions, offsets, and cell matrix. """
        self.core = core
        self.colors = core.colors
        self.width = width
        self.height = height
        self.xoffset = 2
        self.yoffset = 9
        self.active_ui = self.core.active_ui
        base = default if default is not None else CanvasCell(" ", "")
        self._grid: list[list[CanvasCell]] = [
            [CanvasCell(base.ch, base.color) for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self._prev_cells: list[list[tuple[str, str, bool]]] | None = None

    @staticmethod
    def utfchar_len(s: str) -> int:
        """ Return the terminal display width of a Unicode character. """
        if not s:
            return 0
        o = ord(s)
        if 0xFE00 <= o <= 0xFE0F:
            return 0
        if unicodedata.combining(s):
            return 0
        eaw = unicodedata.east_asian_width(s)
        if eaw in ("W", "F"):
            return 2
        if (
            0x1F300 <= o <= 0x1FAFF   # pictos / emojis
            or 0x2600 <= o <= 0x26FF  # misc symbols
            or 0x2700 <= o <= 0x27BF  # dingbats
        ):
            return 2
        return 1

    def set_canvas_cell(self, x: int, y: int, ch: str,
                        color: str | None = None) -> None:
        """ Write a character and optional color into one canvas cell. """
        cell = self._grid[y][x]

        if cell.utf_cont and x > 0:
            previous_cell = self._grid[y][x - 1]
            previous_cell.ch = " "
            previous_cell.utf_cont = False

        if x + 1 < self.width:
            next_cell = self._grid[y][x + 1]
            if next_cell.utf_cont:
                next_cell.ch = " "
                next_cell.color = ""
                next_cell.utf_cont = False

        char_width = self.utfchar_len(ch)

        if char_width == 2 and x + 1 >= self.width:
            ch = " "
            char_width = 1

        cell.ch = ch
        cell.utf_cont = False

        if color is not None:
            cell.color = color

        if char_width == 2:
            continuation_cell = self._grid[y][x + 1]
            continuation_cell.ch = ""
            continuation_cell.color = ""
            continuation_cell.utf_cont = True

    def color_canvas_cell(self, x: int, y: int,
                          color: str | None = None) -> None:
        """ Set the ANSI color code of one canvas cell. """
        if color is not None:
            self._grid[y][x].color = color

    def color_canvas_block(self, x1: int, y1: int, x2: int, y2: int,
                           color: str = "") -> None:
        """ Set the ANSI color code of every cell in a rectangular area. """
        for dy in range(y2 - y1 + 1):
            for dx in range(x2 - x1 + 1):
                self.color_canvas_cell(x1 + dx, y1 + dy, color)

    def get_canvas_cell(self, x: int, y: int) -> CanvasCell:
        """ Return the canvas cell at the specified coordinates. """
        return self._grid[y][x]

    def clear_canvas(self, ch: str = " ", color: str = "") -> None:
        """ Reset every canvas cell to the specified character and color. """
        for y in range(self.height):
            row = self._grid[y]
            for x in range(self.width):
                row[x].ch = ch
                row[x].color = color
                row[x].utf_cont = False

    def store_canvas(self) -> None:
        """ Store the current state of every cell as its built state. """
        for y in range(self.height):
            for x in range(self.width):
                cell = self._grid[y][x]
                cell.built_ch = cell.ch
                cell.built_color = cell.color
                cell.built_utf_cont = cell.utf_cont

    def restore_canvas(
        self,
        x_start: int | None = None,
        y_start: int | None = None,
        x_end: int | None = None,
        y_end: int | None = None,
    ) -> None:
        """ Restore the built state of every cell in a rectangular area. """
        if x_start is None:
            x_start = 1
        if y_start is None:
            y_start = self.yoffset
        if x_end is None:
            x_end = self.width - 1
        if y_end is None:
            y_end = self.height - 2

        x_start = max(0, x_start)
        y_start = max(0, y_start)
        x_end = min(self.width - 1, x_end)
        y_end = min(self.height - 1, y_end)

        if x_end < x_start or y_end < y_start:
            return

        for y in range(y_start, y_end + 1):
            for x in range(x_start, x_end + 1):
                self.restore_cell(x, y)

    def store_cell(self, x: int, y: int) -> None:
        """ Store the current state of one cell as its built state. """
        cell = self._grid[y][x]
        cell.built_ch = cell.ch
        cell.built_color = cell.color
        cell.built_utf_cont = cell.utf_cont

    def restore_cell(self, x: int, y: int) -> None:
        """ Restore one cell from its built state. """
        cell = self._grid[y][x]
        cell.ch = cell.built_ch
        cell.color = cell.built_color
        cell.utf_cont = cell.built_utf_cont

    def copy_cell(self, x_source: int, y_source: int,
                  x_dest: int, y_dest: int) -> None:
        """ Copy one canvas cell into another location. """
        cell_source = self._grid[y_source][x_source]
        cell_dest = self._grid[y_dest][x_dest]
        cell_dest.ch = cell_source.ch
        cell_dest.color = cell_source.color
        cell_dest.utf_cont = cell_source.utf_cont

    def measure_block(self, block: str | Iterable[str]) -> tuple[int, int]:
        """ Return the display width and height of a text block. """
        if isinstance(block, str):
            lines = block.splitlines()
        else:
            lines = list(block)

        if not lines:
            return (0, 0)

        width = max(sum(self.utfchar_len(character) for character in line)
                    for line in lines)
        height = len(lines)
        return (width, height)

    def center_block(
        self,
        block: str | list[str],
        x_start: int = 0,
        x_end: int = 0,
        y_start: int = 0,
        y_end: int = 0,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> tuple[int, int]:
        """
        Return the top-left coordinates that center a text block in an area.
        """
        block_width, block_height = self.measure_block(block)
        xs = max(0, min(self.width, x_start))
        xe = max(0, min(self.width, x_end))
        ys = max(0, min(self.height, y_start))
        ye = max(0, min(self.height, y_end))
        if xe < xs:
            xs, xe = xe, xs
        if ye < ys:
            ys, ye = ye, ys
        zone_width = max(0, xe - xs)
        zone_height = max(0, ye - ys)
        x = xs + (zone_width - block_width) // 2 + offset_x
        y = ys + (zone_height - block_height) // 2 + offset_y
        return (x, y)

    def deco_zone(self, x1: int, y1: int, x2: int, y2: int,
                  source: str | Iterable[str], color: str = "",
                  transparent: bool = False) -> None:
        """ Fill a rectangular area by repeating a text pattern. """
        if x2 < x1:
            return
        if y2 < y1:
            return
        width: int = x2 - x1 + 1
        height: int = y2 - y1 + 1
        if isinstance(source, str):
            src_lines = source.splitlines()
        else:
            src_lines = list(source)
        if not src_lines:
            return
        src_h = len(src_lines)
        src_w = max((len(line) for line in src_lines), default=0)
        if src_w == 0:
            return
        for dy in range(height):
            sy = dy % src_h
            motif_line = src_lines[sy]
            if not motif_line:
                continue
            reps = (width + len(motif_line) - 1) // len(motif_line)
            tiled = (motif_line * reps)[:width]
            self.add_block(x1, y1 + dy, tiled, color, transparent=transparent)

    def add_block(
                self,
                x: int,
                y: int,
                block: str | Iterable[str],
                color: str | None = None,
                transparent: bool = False,
                transparent_chars: set[str] | None = None,
            ) -> None:
        """
        Write a text block into the canvas at the specified coordinates.
        Ignore configured transparent characters when transparency is enabled.
        """
        if isinstance(block, str):
            lines = block.splitlines()
        else:
            lines = list(block)
        if transparent_chars is None:
            transparent_chars = {" "}
        for dy, line in enumerate(lines):
            if not line:
                continue
            gy = y + dy
            if gy < 0 or gy >= self.height:
                continue
            gx = x
            for ch in line:
                char_width = self.utfchar_len(ch)
                if char_width == 0:
                    continue
                if transparent and ch in transparent_chars:
                    gx += char_width
                    if gx >= self.width:
                        break
                    continue
                if 0 <= gx < self.width:
                    self.set_canvas_cell(gx, gy, ch, color)
                gx += char_width
                if gx >= self.width:
                    break

    def capture_block(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
    ) -> list[str]:
        """ Capture the textual content of a rectangular canvas area. """
        block: list[str] = []

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(self.width - 1, x2)
        y2 = min(self.height - 1, y2)

        for y in range(y1, y2 + 1):
            line_chars: list[str] = []
            x = x1

            while x <= x2:
                cell = self._grid[y][x]

                if cell.utf_cont:
                    x += 1
                    continue

                ch = cell.ch
                line_chars.append(ch)

                char_width = self.utfchar_len(ch)
                x += max(1, char_width)

            block.append("".join(line_chars))

        return block

    def capture_snapshot(self, x1: int, y1: int, x2: int,
                         y2: int) -> list[list[CanvasCell]]:
        """
        Capture a rectangular area as a matrix of complete canvas cells.
        """
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(self.width - 1, x2)
        y2 = min(self.height - 1, y2)

        if x2 < x1 or y2 < y1:
            return []

        snapshot: list[list[CanvasCell]] = []

        for y in range(y1, y2 + 1):
            row: list[CanvasCell] = []
            for x in range(x1, x2 + 1):
                row.append(replace(self._grid[y][x]))
            snapshot.append(row)

        return snapshot

    def restore_snapshot(
        self,
        x: int,
        y: int,
        snapshot: list[list[CanvasCell]],
        x_start: int = 0,
        y_start: int = 0,
        x_end: int | None = None,
        y_end: int | None = None,
        store_ref: bool = False,
        store_new: bool = False,
        store_discrete: bool = False
    ) -> None:
        """
        Restore a matrix of canvas cells into a rectangular canvas area.
        """
        if not snapshot or not snapshot[0]:
            return

        snap_h = len(snapshot)
        snap_w = len(snapshot[0])

        if x_start < 0:
            x_start = 0
        if y_start < 0:
            y_start = 0
        if x_end is None or x_end >= snap_w:
            x_end = snap_w - 1
        if y_end is None or y_end >= snap_h:
            y_end = snap_h - 1

        if x_end < x_start or y_end < y_start:
            return

        for sy in range(y_start, y_end + 1):
            gy = y + (sy - y_start)
            if gy < 0 or gy >= self.height:
                continue

            for sx in range(x_start, x_end + 1):
                gx = x + (sx - x_start)
                if gx < 0 or gx >= self.width:
                    continue

                src = snapshot[sy][sx]
                dst = self._grid[gy][gx]

                if store_discrete is False:
                    dst.ch = src.ch
                    dst.color = src.color
                    dst.utf_cont = src.utf_cont
                if store_ref is True:
                    dst.built_ch = src.built_ch
                    dst.built_color = src.built_color
                    dst.built_utf_cont = src.built_utf_cont
                elif store_new is True or store_discrete is True:
                    dst.built_ch = src.ch
                    dst.built_color = src.color
                    dst.built_utf_cont = src.utf_cont

    def large_counter_block(
        self,
        value: int,
        min_digits: int = 1,
        pad_char: str = "0",
    ) -> str:
        """ Build a large digit block using the configured digit glyphs. """
        s = str(max(0, value))
        if len(s) < min_digits:
            s = s.rjust(min_digits, pad_char)
        block_lines = ["", "", ""]
        for ch in s:
            if "0" <= ch <= "9":
                d = ord(ch) - ord("0")
                start = d * 3
                end = start + 3
                block_lines[0] += Elements.LARGE_DIGITS[0][start:end]
                block_lines[1] += Elements.LARGE_DIGITS[1][start:end]
                block_lines[2] += Elements.LARGE_DIGITS[2][start:end]
            else:
                block_lines[0] += " " * 3
                block_lines[1] += " " * 3
                block_lines[2] += " " * 3
        return "\n".join(block_lines)

    def large_text_block(self, text: str) -> str:
        """ Build a large text block using the configured printable glyphs. """
        result = []

        for line in text.split("\n"):
            block = ["", "", ""]

            for ch in line:
                if 32 <= ord(ch) <= 126:
                    idx = ord(ch) - 32
                    group = idx // 19
                    pos = idx % 19

                    start = pos * 3
                    end = start + 3
                    base = group * 3

                    block[0] += Elements.LARGE_PRINTABLE[base][start:end]
                    block[1] += Elements.LARGE_PRINTABLE[base + 1][start:end]
                    block[2] += Elements.LARGE_PRINTABLE[base + 2][start:end]
                else:
                    for i in range(3):
                        block[i] += " " * 3

            result.extend(block)

        return "\n".join(result)

    def render_canvas(self, reset_each_cell: bool = False) -> str:
        """ Render the complete canvas as a single terminal string. """
        lines: list[str] = []
        rows_in_line: list[str] = []
        if reset_each_cell:
            for y in range(self.height):
                rows_in_line = []
                for x in range(self.width):
                    cell = self._grid[y][x]
                    if cell.utf_cont:
                        continue
                    if cell.color:
                        rows_in_line.append(cell.color)
                        rows_in_line.append(cell.ch)
                        rows_in_line.append(self.colors.RESET)
                    else:
                        rows_in_line.append(cell.ch)
                lines.append("".join(rows_in_line) + self.colors.RESET)
            return "\n".join(lines)

        for y in range(self.height):
            current_color = ""
            rows_in_line = []
            for x in range(self.width):
                cell = self._grid[y][x]
                if cell.utf_cont:
                    continue
                c = cell.color
                if c and c != current_color:
                    rows_in_line.append(c)
                    current_color = c
                elif not c and current_color:
                    rows_in_line.append(self.colors.RESET)
                    current_color = ""
                rows_in_line.append(cell.ch)
            if current_color:
                rows_in_line.append(self.colors.RESET)
            lines.append("".join(rows_in_line))
        return "\n".join(lines)

    def _render_span(self, y: int, x_start: int, x_end: int) -> str:
        """ Render part of one canvas row as a terminal string. """
        row = self._grid[y]
        parts: list[str] = []
        current_color = ""

        for x in range(x_start, x_end + 1):
            cell = row[x]

            if cell.utf_cont:
                continue

            c = cell.color or ""
            if c != current_color:
                if c:
                    parts.append(c)
                elif current_color:
                    parts.append(self.colors.RESET)
                current_color = c

            parts.append(cell.ch)

        if current_color:
            parts.append(self.colors.RESET)

        return "".join(parts)

    def print_canvas(self, force_prev: bool = False,
                     std_err: bool = False) -> None:
        """
        Print the canvas while updating only cells changed
        since the last display.
        """
        write = sys.stdout.write
        flush = sys.stdout.flush
        if std_err is True:
            write = sys.stderr.write
            flush = sys.stderr.flush
        grid = self._grid
        height = self.height
        width = self.width
        base_row = 2

        if force_prev is True:
            self._prev_cells = [
                [(grid[y][x].ch, grid[y][x].color or "", grid[y][x].utf_cont)
                 for x in range(width)]
                for y in range(height)
            ]

        if self._prev_cells is None:
            canvas = self.render_canvas()
            write("\33[H\33[2J\33[?25l\33[1m\n")
            write(canvas)
            flush()

            self._prev_cells = [
                [(grid[y][x].ch, grid[y][x].color or "", grid[y][x].utf_cont)
                 for x in range(width)]
                for y in range(height)
            ]
            return

        prev_cells = self._prev_cells
        out: list[str] = ["\33[?25l\33[1m"]
        any_change = False

        for y in range(height):
            row = grid[y]
            prev_row = prev_cells[y]
            x = 0

            while x < width:
                cell = row[x]
                ch = cell.ch
                color = cell.color or ""
                utf_cont = cell.utf_cont
                pch, pcolor, putf = prev_row[x]

                if ch == pch and color == pcolor and utf_cont == putf:
                    x += 1
                    continue

                any_change = True
                start = x
                x += 1

                while x < width:
                    cell = row[x]
                    ch = cell.ch
                    color = cell.color or ""
                    utf_cont = cell.utf_cont
                    pch, pcolor, putf = prev_row[x]
                    if ch == pch and color == pcolor and utf_cont == putf:
                        break
                    x += 1

                end = x - 1
                if (end + 1 < width and row[end + 1].utf_cont):
                    end += 1

                while start > 0 and row[start].utf_cont:
                    start -= 1

                span = self._render_span(y, start, end)
                out.append(f"\33[{base_row + y};{start + 1}H")
                out.append(span)

                for i in range(start, end + 1):
                    c = row[i]
                    prev_row[i] = (c.ch, c.color or "", c.utf_cont)

        if not any_change:
            return

        out.append(f"\33[H\33[{self.height + 1};1H")
        write("".join(out))
        flush()
