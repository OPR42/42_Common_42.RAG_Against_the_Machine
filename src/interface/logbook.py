import time
from collections.abc import Iterable
from dataclasses import dataclass

from .interface import Interface


@dataclass(slots=True)
class LogBookCell:
    """ Store the display state of one logbook cell. """
    ch: str = " "
    color: str = ""
    utf_cont: bool = False


class LogBook:
    """ Manage the scrollable logbook displayed in the right panel. """
    MIN_HEIGHT = 28

    def __init__(
            self,
            interface: Interface,
            default: LogBookCell | None = None,
            ) -> None:
        """ Initialize the logbook dimensions, viewport, and cell grid. """
        self.interface = interface
        self.canvas = interface.canvas
        self.key_control = interface.key_control
        self.width = 136
        self.height = self.MIN_HEIGHT
        self.canvas_x_start = interface.x_start
        self.canvas_y_start = interface.y_start + 3
        self.canvas_x_end = interface.x_end - 2
        self.canvas_y_end = interface.y_end - 3
        self.disp_height = self.canvas_y_end - self.canvas_y_start + 1
        base = default if default is not None else LogBookCell(" ", "")
        self.default_cell = LogBookCell(base.ch, base.color, base.utf_cont)
        self.grid: list[list[LogBookCell]] = [
            self._new_row()
            for _ in range(self.height)
        ]
        self.last_line: int = 0
        self.top_view: int = 0
        self.bot_view: int = self.MIN_HEIGHT - 1

    def _new_row(self) -> list[LogBookCell]:
        """ Create an empty logbook row from the default cell state. """
        return [
            LogBookCell(self.default_cell.ch, self.default_cell.color,
                        self.default_cell.utf_cont) for _ in range(self.width)]

    def _ensure_height(self, required_height: int) -> None:
        """ Extend the logbook grid to contain the required number of rows. """
        if required_height <= self.height:
            return
        missing_rows = required_height - self.height
        self.grid.extend(self._new_row() for _ in range(missing_rows))
        self.height = required_height

    def clear(self) -> None:
        """ Clear the logbook and restore its minimum height. """
        self.height = self.MIN_HEIGHT
        self.grid = [self._new_row() for _ in range(self.height)]
        self.last_line = 0
        self.top_view = 0
        self.bot_view = self.MIN_HEIGHT - 1

    def is_at_bottom(self) -> bool:
        """ Return whether the last log line is currently visible. """
        max_top_view = max(0, self.last_line - self.disp_height + 1)
        return self.top_view >= max_top_view

    def scroll_to_bottom(self) -> None:
        """ Scroll until the last log line becomes visible. """
        missing = (self.last_line - self.top_view - self.disp_height + 1)
        if missing > 0:
            self.scroll_logbook(missing)

    def add_log_block(self, x: int, y: int, block: str | Iterable[str],
                      color: str | None = None,
                      transparent: bool = False) -> None:
        """
        Write a text block into the logbook at the specified coordinates.
        Ignore spaces when transparency is enabled.
        """
        if isinstance(block, str):
            lines = block.splitlines()
        else:
            lines = list(block)
        for dy, line in enumerate(lines):
            if not line:
                continue
            gy = y + dy
            if gy < 0:
                continue
            self._ensure_height(gy + 1)
            self.last_line = max(self.last_line, gy)
            gx = x
            for ch in line:
                char_width = self.canvas.utfchar_len(ch)
                if char_width == 0:
                    continue
                if 0 <= gx < self.width and not (transparent and ch == " "):
                    self.set_logbook_cell(gx, gy, ch, color)
                gx += char_width
                if gx >= self.width:
                    break
        self.scroll_to_bottom()

    def add_empty_log_line(self, qty: int = 1) -> None:
        """ Append the specified number of empty log lines. """
        if qty <= 0:
            return
        self.last_line += qty
        self._ensure_height(self.last_line + 1)
        self.scroll_to_bottom()

    def add_separator_line(self, y: int, color: str) -> None:
        """ Draw a layered separator line at the specified logbook row. """
        self.add_log_block(2, y, "─" * 130, color)
        self.add_log_block(22, y, "━" * 90, color)
        self.add_log_block(42, y, "═" * 50, color)

    def next_empty_log_line(self) -> int:
        """ Return the index of the next empty logbook line. """
        was_at_bottom = self.is_at_bottom()
        next_y = self.last_line + 1
        next_y_disp = next_y - self.top_view
        if next_y_disp >= self.disp_height:
            missing = next_y_disp - (self.disp_height - 1)
            if missing > 0 and was_at_bottom:
                self.scroll_logbook(missing)
        return next_y

    def log_y_to_screen_y(self, log_y: int) -> int:
        """ Convert a logbook row index into a canvas row index. """
        return self.canvas_y_start + log_y - self.top_view

    def set_logbook_cell(self, x: int, y: int, ch: str,
                         color: str | None = None) -> None:
        """ Write a character and optional color into one logbook cell. """
        cell = self.grid[y][x]

        if cell.utf_cont and x > 0:
            previous_cell = self.grid[y][x - 1]
            previous_cell.ch = " "
            previous_cell.utf_cont = False

        if x + 1 < self.width:
            next_cell = self.grid[y][x + 1]
            if next_cell.utf_cont:
                next_cell.ch = " "
                next_cell.color = ""
                next_cell.utf_cont = False

        char_width = self.canvas.utfchar_len(ch)

        if char_width == 2 and x + 1 >= self.width:
            ch = " "
            char_width = 1

        cell.ch = ch
        cell.utf_cont = False

        if color is not None:
            cell.color = color

        if char_width == 2:
            continuation_cell = self.grid[y][x + 1]
            continuation_cell.ch = ""
            continuation_cell.color = ""
            continuation_cell.utf_cont = True

    def clean_logbook_panel(self) -> None:
        """ Restore the canvas area occupied by the logbook panel. """
        for y in range(self.canvas_y_start, self.canvas_y_end + 1):
            for x in range(self.canvas_x_start, self.canvas_x_end + 1):
                self.canvas.restore_cell(x, y)

    def display_logbook(self) -> None:
        """
        Display the visible logbook rows according to the
        current scroll position.
        """
        self.clean_logbook_panel()
        for y in range(self.canvas_y_start, self.canvas_y_end + 1):
            y_src = self.top_view + y - self.canvas_y_start
            if y_src >= self.height:
                break
            for x in range(self.canvas_x_start, self.canvas_x_end + 1):
                cell_src = self.grid[y_src][x - self.canvas_x_start]
                if cell_src.ch == " ":
                    continue
                cell_dst = self.canvas._grid[y][x]
                cell_dst.ch = cell_src.ch
                cell_dst.color = cell_src.color
                cell_dst.utf_cont = cell_src.utf_cont
        self.interface.canvas.print_canvas()

    def scroll_logbook(self, move: int) -> None:
        """ Scroll the logbook by the specified number of rows. """
        way = 1
        if move < 0:
            way = -1
            move = -move
        for _ in range(move):
            self.top_view += way
            self.top_view = max(0, min(self.top_view,
                                       self.last_line - self.disp_height + 1))
            self.scroll_bar()
            self.display_logbook()
            time.sleep(self.interface.base_wait * 5)

    def scroll_bar(self) -> None:
        """ Display the logbook scroll thumb and navigation indicators. """
        sb_x_start = self.canvas_x_end + 2
        sb_x_end = self.canvas_x_end + 2
        sb_y_start = self.canvas_y_start + 1
        sb_y_end = self.canvas_y_end - 1
        color = self.interface.cl_scroll_bar
        content_height = max(1, self.last_line + 1)
        visible_height = self.disp_height
        max_scroll = max(0, content_height - visible_height)
        color_up = self.interface.cl_dim_labels

        if self.top_view > 0:
            color_up = self.interface.cl_labels

        self.canvas.set_canvas_cell(sb_x_start, sb_y_start - 1, "◢", color_up)
        color_down = self.interface.cl_dim_labels

        if self.top_view < max_scroll:
            color_down = self.interface.cl_labels

        self.canvas.set_canvas_cell(sb_x_start, sb_y_end + 1, "◥", color_down)

        for y in range(sb_y_start, sb_y_end + 1):
            for x in range(sb_x_start, sb_x_end + 1):
                self.canvas.restore_cell(x, y)
                self.canvas.color_canvas_cell(
                    x, y, self.interface.cl_main_background)

        track_height = sb_y_end - sb_y_start + 1
        logical_track_height = track_height * 2
        logical_margin = 1
        usable_logical_height = (logical_track_height - logical_margin * 2)

        if usable_logical_height <= 0:
            return

        size_ratio = min(1.0, visible_height / content_height)
        logical_thumb_height = max(
            2,
            int(round(size_ratio * usable_logical_height)))
        logical_thumb_height = min(logical_thumb_height, usable_logical_height)
        max_logical_offset = max(
            0,
            usable_logical_height - logical_thumb_height)

        if max_scroll == 0:
            logical_thumb_offset = 0
        else:
            logical_thumb_offset = int(round(
                (self.top_view / max_scroll) * max_logical_offset))

        logical_thumb_offset = min(max(logical_thumb_offset, 0),
                                   max_logical_offset)
        thumb_start = logical_margin + logical_thumb_offset
        thumb_end = thumb_start + logical_thumb_height

        for row in range(track_height):
            upper_half = row * 2
            lower_half = upper_half + 1
            upper_occupied = thumb_start <= upper_half < thumb_end
            lower_occupied = thumb_start <= lower_half < thumb_end

            if upper_occupied and lower_occupied:
                fragment = "█"
            elif upper_occupied:
                fragment = "▀"
            elif lower_occupied:
                fragment = "▄"
            else:
                continue

            self.canvas.add_block(sb_x_start, sb_y_start + row,
                                  fragment, color)
