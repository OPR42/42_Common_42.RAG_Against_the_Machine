import shutil
import time

from .canvas import Canvas
from .colors import Colors
from .interface import Interface
from .visual_consts import Banners, Elements


BASE_WAIT = 0.002


class Launcher:
    """ Display the startup screen and validate terminal dimensions. """
    def __init__(self, core: Interface) -> None:
        """ Initialize the launcher interface. """
        self.core = core
        self.colors = core.colors
        self.width: int = 78
        self.height: int = 23
        self.base_wait = BASE_WAIT
        self.launcher_canvas = Canvas(self.core, self.width, self.height)
        self.key_control = self.core.key_control

    def present(self) -> None:
        """ Display the launcher and wait for a suitable terminal size. """
        self.build_launcher()
        self.launcher_canvas.print_canvas()
        self.manage_dimensions()

    def manage_dimensions(self) -> None:
        """
        Wait until the terminal reaches the required dimensions.
        Display the current and required terminal sizes while updating the
        launcher animation.
        """
        valid_count: int = 0

        self.launcher_canvas.add_block(
            26, 10,
            "Needed terminal dimensions:",
            self.core.cl_labels, transparent=True
            )
        self.launcher_canvas.add_block(
            24, 15,
            "Available terminal dimensions:",
            self.core.cl_labels, transparent=True
            )

        need_x, need_y = 139, 46
        need_x_large = self.launcher_canvas.large_text_block(str(need_x))
        need_y_large = self.launcher_canvas.large_text_block(str(need_y))
        need_x_large_w, _ = self.launcher_canvas.measure_block(need_x_large)
        need_y_large_w, _ = self.launcher_canvas.measure_block(need_y_large)
        need_offset = ((self.width - 6 - need_x_large_w - need_y_large_w)
                       // 2) + 2
        self.launcher_canvas.add_block(need_offset, 11, need_x_large,
                                       Colors.LIGHT_BLUE, transparent=True)
        self.launcher_canvas.add_block(need_offset + need_x_large_w, 11,
                                       Elements.LARGE_X, Colors.LIGHT_BLUE,
                                       transparent=True)
        self.launcher_canvas.add_block(need_offset + need_x_large_w + 3, 11,
                                       need_y_large, Colors.LIGHT_BLUE,
                                       transparent=True)

        prev_term_x, prev_term_y = 0, 0

        while True:
            _ = self.key_control.key_control()
            term_x, term_y = shutil.get_terminal_size(fallback=(80, 24))
            term_x_large = self.launcher_canvas.large_text_block(str(term_x))
            term_y_large = self.launcher_canvas.large_text_block(str(term_y))
            term_x_large_w, _ = self.launcher_canvas.measure_block(
                term_x_large
                )
            term_y_large_w, _ = self.launcher_canvas.measure_block(
                term_y_large
                )
            term_offset = ((self.width - 6 - term_x_large_w - term_y_large_w)
                           // 2) + 2
            if term_x < need_x or term_y < need_y:
                valid_count = 0
                color = Colors.ORANGE
                self.launcher_canvas.restore_canvas(x_start=2, y_start=20,
                                                    x_end=self.width - 2,
                                                    y_end=21)
                self.launcher_canvas.add_block(
                    10, 20, "Please increase "
                    + "terminal dimensions by resizing this window\n"
                    + "               or use            to de-zoom.",
                    self.core.cl_labels, transparent=True)
                self.launcher_canvas.add_block(
                    32, 21, "◤Ctrl◥ ◤━◥",
                    Colors.INV_GOLD, transparent=True)
            else:
                valid_count += 1
                color = Colors.MEDIUM_TEAL_GREEN
                self.launcher_canvas.restore_canvas(x_start=2, y_start=20,
                                                    x_end=self.width - 2,
                                                    y_end=21)
                self.launcher_canvas.add_block(
                    6, 20, "Terminal dimensions are "
                    "large enough, Interface will start shortly.",
                    self.core.cl_labels, transparent=True)

            self.launcher_canvas.restore_canvas(
                x_start=term_offset - 6,
                y_start=16,
                x_end=self.width - term_offset + 6,
                y_end=18
                )
            self.launcher_canvas.add_block(term_offset, 16, term_x_large,
                                           color, transparent=True)
            self.launcher_canvas.add_block(term_offset + term_x_large_w, 16,
                                           Elements.LARGE_X, color,
                                           transparent=True)
            self.launcher_canvas.add_block(term_offset + term_x_large_w + 3,
                                           16, term_y_large, color,
                                           transparent=True)

            if valid_count >= 25:
                grid = self.launcher_canvas._grid
                for i in range(self.height - 9):
                    for y in range(self.height - 10 - i):
                        for x in range(self.width - 3):
                            cell_src = grid[y + 10][x + 2]
                            cell_dst = grid[y + 9][x + 2]
                            cell_dst.ch = cell_src.ch
                            cell_dst.color = cell_src.color
                            cell_dst.utf_cont = cell_src.utf_cont
                    self.launcher_canvas.add_block(1, self.height - i - 2,
                                                   "╠", self.core.cl_frame)
                    self.launcher_canvas.add_block(self.width - 1,
                                                   self.height - i - 2,
                                                   "╣", self.core.cl_frame)
                    for x in range(self.width - 1):
                        self.launcher_canvas.restore_cell(1 + x,
                                                          self.height - i - 1)
                    if i != 0:
                        self.launcher_canvas.color_canvas_block(
                            2, self.height - i - 1,
                            self.width - 2, self.height - i - 1,
                            self.core.cl_main_background)

                    for y in range(3):
                        for x in range(3):
                            self.launcher_canvas.restore_cell(i * 3 + 8 + x,
                                                              y + 2)
                            self.launcher_canvas.restore_cell(
                                self.width - 8 - i * 3 + x,
                                y + 2
                                )
                    self.launcher_canvas.print_canvas()
                    time.sleep(self.base_wait * 20)
                break

            time.sleep(self.base_wait * 20)
            if prev_term_x != term_x or prev_term_y != term_y:
                prev_term_x, prev_term_y = term_x, term_y
                self.launcher_canvas._prev_cells = None
            self.launcher_canvas.print_canvas()

    def build_launcher(self) -> None:
        """ Build the launcher screen on the canvas. """
        self.launcher_canvas.clear_canvas()
        self.launcher_canvas.deco_zone(-2, 0, self.width - 1, self.height - 1,
                                       Elements.DECO_FILL,
                                       self.core.cl_main_background)
        for y in range(self.height):
            self.launcher_canvas.add_block(0, y, " ",
                                           self.core.cl_main_background)
        self.launcher_canvas.color_canvas_block(2, 1, self.width - 2, 7,
                                                self.colors.DEEP_PURPLE)
        for x in range(self.width):
            if x > 0:
                self.launcher_canvas.set_canvas_cell(x, 0, "═",
                                                     self.core.cl_frame)
                self.launcher_canvas.set_canvas_cell(x, 8, "═",
                                                     self.core.cl_frame)
                self.launcher_canvas.set_canvas_cell(x, self.height - 1, "═",
                                                     self.core.cl_frame)
        for y in range(self.height):
            self.launcher_canvas.set_canvas_cell(1, y, "║", self.core.cl_frame)
            self.launcher_canvas.set_canvas_cell(self.width - 1, y, "║",
                                                 self.core.cl_frame)
        self.launcher_canvas.set_canvas_cell(1, 0, "╔", self.core.cl_frame)
        self.launcher_canvas.set_canvas_cell(self.width - 1, 0, "╗",
                                             self.core.cl_frame)
        self.launcher_canvas.set_canvas_cell(1, self.height - 1, "╚",
                                             self.core.cl_frame)
        self.launcher_canvas.set_canvas_cell(self.width - 1, self.height - 1,
                                             "╝", self.core.cl_frame)
        self.launcher_canvas.set_canvas_cell(1, 8, "╠", self.core.cl_frame)
        self.launcher_canvas.set_canvas_cell(self.width - 1, 8, "╣",
                                             self.core.cl_frame)
        self.launcher_canvas.add_block(2, 1, Banners.LEFT_BANNER,
                                       self.colors.BLUE42, transparent=True)
        self.launcher_canvas.add_block(self.width - 8, 1, Banners.RIGHT_BANNER,
                                       self.colors.BLUE42, transparent=True)
        x, _ = self.launcher_canvas.center_block(Banners.SIGNATURE_BANNER,
                                                 x_start=8,
                                                 x_end=self.width - 7)
        self.launcher_canvas.add_block(x, 7, Banners.SIGNATURE_BANNER,
                                       self.core.cl_frame, transparent=True)
        for i in range(len(Banners.SIGNATURE_COLORS)):
            color_id = Banners.SIGNATURE_COLORS[i]
            if color_id != "0":
                if color_id == "3":
                    color = f"\33[3{color_id}m"
                else:
                    color = f"\33[9{color_id}m"
                self.launcher_canvas.color_canvas_cell(x + i, 7, color)
        self.launcher_canvas.store_canvas()
        x, _ = self.launcher_canvas.center_block(Banners.SMALL_BANNER,
                                                 x_start=8,
                                                 x_end=self.width - 7)
        self.launcher_canvas.add_block(x, 2, Banners.SMALL_BANNER,
                                       self.colors.BASE_BR_PURPLE,
                                       transparent=True)
