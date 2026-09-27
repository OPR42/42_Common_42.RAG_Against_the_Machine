import configparser
import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from types import TracebackType
from typing import Any

from src.base.models import LogEvent, ColorTheme
from src.base.utils import RagUtils as utils
from src.command.cli import CLI

from .colors import Colors
from .visual_consts import Banners, Elements, Panels


BASE_WAIT = 0.002
NBSP = "\u00A0"
CONFIG_PATH = Path("data/config.ini")


class SuppressStderr(object):
    """ Temporarily redirect stderr to the null device. """
    def __enter__(self) -> "SuppressStderr":
        """ Redirect stderr until leaving the context. """
        self.errnull_file = open(os.devnull, 'w')
        self.old_stderr_fileno_undup = sys.stderr.fileno()
        self.old_stderr_fileno = os.dup(sys.stderr.fileno())
        self.old_stderr = sys.stderr
        os.dup2(self.errnull_file.fileno(), self.old_stderr_fileno_undup)
        sys.stderr = self.errnull_file
        return self

    def __exit__(self,
                 exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType | None,
                 ) -> None:
        """ Restore the original stderr stream. """
        sys.stderr = self.old_stderr
        os.dup2(self.old_stderr_fileno, self.old_stderr_fileno_undup)
        os.close(self.old_stderr_fileno)
        self.errnull_file.close()


class Interface:
    """ Provide the terminal user interface for the RAG application. """
    def __init__(self,
                 cli: CLI,
                 data_path: str,
                 index_path: str,
                 chunks_path: str,
                 dataset_path: str,
                 dataset_answered: str,
                 save_directory: str,
                 search_result_path: str,
                 save_results_answer_dir: str) -> None:
        """ Initialize the terminal interface and its default state. """
        self.cli: CLI = cli
        self.default_data_path: str = data_path
        self.default_index_path: str = index_path
        self.default_chunks_path: str = chunks_path
        self.default_dataset_path: str = dataset_path
        self.default_dataset_answered: str = dataset_answered
        self.default_search_result_path: str = search_result_path
        self.default_save_dir: str = save_directory
        self.default_save_results_answer_dir: str = save_results_answer_dir
        self.default_max_chunk_size: int = 800
        self.default_k: int = 10
        self.default_dataset_index: int = 0
        self.default_color_theme_index: int = 0
        self.default_hybrid_retrieval: bool = False
        self.data_path: str = self.default_data_path
        self.index_path: str = self.default_index_path
        self.chunks_path: str = self.default_chunks_path
        self.dataset_path: str = self.default_dataset_path
        self.dataset_answered: str = self.default_dataset_answered
        self.search_result_path: str = self.default_search_result_path
        self.save_dir: str = self.default_save_dir
        self.save_results_answer_dir: str = (
            self.default_save_results_answer_dir
            )
        self.max_chunk_size: int = self.default_max_chunk_size
        self.k: int = self.default_k
        self.dataset_index: int = self.default_dataset_index
        self.hybrid_retrieval: bool = self.default_hybrid_retrieval
        self.color_theme_index: int = self.default_color_theme_index
        self.load_settings()
        self.k_query: int = self.k
        self.query: str = ""
        self.k_question: int = self.k
        self.question: str = ""
        self.active_ui: bool = True
        self.step: int = 0
        self.active_ribbon_thumb: int = 1
        self.base_wait = BASE_WAIT
        self.colors = Colors()
        self.width: int = 139
        self.height: int = 44
        self.x_start, self.x_end = 2, self.width - 2
        self.x_mid = (self.x_end - self.x_start) // 2 + 2
        self.y_start, self.y_end = 9, self.height - 2
        self.y_bot_panel = self.y_end - 9
        self.event_progbar_y: int = 0
        self.event_progbar_title: str = ""
        self.event_progbar_value: float = 0.0
        self.settings_focus: int = 1
        self.settings_value: list[str | int | bool] = []
        self.settings_save_button: bool = False
        self.settings_default_button: bool = False
        self.cl_frame = self.colors.BROWN
        self.cl_main_background = self.colors.scale_color(self.cl_frame, 0.2)
        self.cl_labels = self.colors.LIGHT_BEIGE
        self.cl_dim_labels = self.colors.scale_color(self.cl_labels, 0.5)
        self.cl_inv_labels = self.colors.reverse_foreback_colors(
            self.cl_labels
            )
        self.cl_text = self.colors.MEDIUM_TEAL_GREEN
        self.cl_ita_text = self.colors.italic_color(self.cl_text)
        self.cl_inv_text = self.colors.reverse_foreback_colors(self.cl_text)
        self.cl_dim_text = self.colors.scale_color(self.cl_text, 0.75)
        self.cl_highlight_text = self.colors.scale_color(self.cl_text, 1.5)
        self.cl_alt_text = self.colors.MEDIUM_CYAN
        self.cl_alt_inv_text = self.colors.reverse_foreback_colors(
            self.cl_alt_text
            )
        self.cl_dim_alt_text = self.colors.scale_color(self.cl_alt_text, 0.75)
        self.cl_highlight_alt_text = self.colors.scale_color(self.cl_alt_text,
                                                             1.5)
        # Adapt the log background intensity to the brightness
        # of the current theme.
        fr, fg, fb, br, bg, bb = self.colors.decode_color(self.cl_text)
        sum_rgb = fr + fg + fb + br + bg + bb
        scale = 0.16
        if 256 <= sum_rgb < 512:
            scale = 0.18
        elif sum_rgb < 256:
            scale = 0.2
        # Adapt done
        self.cl_log_background = self.colors.scale_color(self.cl_text, scale)
        self.cl_button = self.colors.reverse_foreback_colors(self.cl_text)
        self.cl_disabled_button = self.colors.scale_color(self.cl_button, 0.4)
        self.cl_scroll_bar = self.colors.scale_color_fore(self.cl_text,
                                                          0.8)
        self.cl_log_item = self.colors.average_colors(
            self.colors.scale_color(self.colors.GREY, 1),
            self.colors.scale_color(self.cl_text, 0.25))
        self.color_theme(index=self.color_theme_index, command="activate")
        from .termkeys import TerminalManager, KeyControl
        self.terminal_manager = TerminalManager(self)
        self.key_control = KeyControl(self, self.terminal_manager)
        self.key_control.start()

    def run(self) -> None:
        """ Run the terminal interface event loop. """
        with SuppressStderr():
            from .launcher import Launcher
            launcher = Launcher(self)
            launcher.present()
            from .canvas import Canvas
            self.canvas = Canvas(self, self.width, self.height)
            from .logbook import LogBook
            self.logbooks: dict[int, LogBook] = {
                i: LogBook(self) for i in range(1, 8)
            }
            self.build()
            self.build_home_text()
            self.build_settings_tab()
            self.step = 1
            self.call_evaluate()
            self.open_ribbon_thumb()

            function_keys = {
                "f1": 1,
                "f2": 2,
                "f3": 3,
                "f4": 4,
                "f5": 5,
                "f6": 6,
                "f7": 7,
            }

            while True:
                time.sleep(self.base_wait * 10)
                key = self.key_control.key_control()
                if key == "left" or key == "right":
                    if key == "left" and self.active_ribbon_thumb > 1:
                        self.active_ribbon_thumb -= 1
                    elif key == "right" and self.active_ribbon_thumb < 7:
                        self.active_ribbon_thumb += 1
                    self.open_ribbon_thumb()
                elif key in function_keys:
                    self.active_ribbon_thumb = function_keys[key]
                    self.open_ribbon_thumb()
                elif key == "enter" and 1 <= self.active_ribbon_thumb <= 6:
                    if self.active_ribbon_thumb == 1:
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "CLEAR DATA", "⊲━━┛", False)
                        self.clear_data()
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "CLEAR DATA", "⊲━━┛", True)

                    elif self.active_ribbon_thumb == 2:
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "MAKE INDEX", "⊲━━┛", False)
                        self.cli.index(max_chunk_size=self.max_chunk_size,
                                       data_path=self.data_path,
                                       index_path=self.index_path,
                                       chunks_path=self.chunks_path,
                                       basic_print=False,
                                       tui_display=True,
                                       hybrid_retrieval=self.hybrid_retrieval)
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "MAKE INDEX", "⊲━━┛", True)

                    elif self.active_ribbon_thumb == 3:
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "SEARCH KEY", "⊲━━┛", False)
                        new_query = self.input_box(
                            message="Which keyword are you looking for?",
                            message_color=self.cl_labels,
                            field_color=self.cl_inv_labels,
                            field_size=60,
                            field_default=self.query,
                            field_type="keyword",
                            active_btn_color=self.cl_button,
                            inactive_btn_color=self.cl_disabled_button,
                            frame_color=self.cl_frame,
                            default_item=1)
                        panel = self.logbooks[self.active_ribbon_thumb]
                        panel.display_logbook()
                        if new_query is not None and new_query != "":
                            self.query = new_query
                        else:
                            self.place_button(self.x_start + 61,
                                              self.y_end - 1,
                                              14, "SEARCH KEY", "⊲━━┛", True)
                            panel = self.logbooks[self.active_ribbon_thumb]
                            panel.display_logbook()
                            if 2 <= self.active_ribbon_thumb <= 6:
                                panel.scroll_bar()
                            self.canvas.print_canvas()
                            continue
                        if self.k_query <= 0:
                            self.k_query = 10
                        new_k = self.input_box(
                            message="From how many sources?",
                            message_color=self.cl_labels,
                            field_color=self.cl_inv_labels,
                            field_size=4,
                            field_default=f"{self.k_query}",
                            field_type="number",
                            active_btn_color=self.cl_button,
                            inactive_btn_color=self.cl_disabled_button,
                            frame_color=self.cl_frame,
                            default_item=1)
                        panel = self.logbooks[self.active_ribbon_thumb]
                        panel.display_logbook()
                        if new_k is not None and new_k:
                            self.k_query = int(new_k)
                        else:
                            self.place_button(self.x_start + 61,
                                              self.y_end - 1,
                                              14, "SEARCH KEY", "⊲━━┛", True)
                            panel = self.logbooks[self.active_ribbon_thumb]
                            panel.display_logbook()
                            if 2 <= self.active_ribbon_thumb <= 6:
                                panel.scroll_bar()
                            self.canvas.print_canvas()
                            continue
                        if (self.query and self.query != ""
                           and self.k_query > 0):
                            self.cli.search(query=self.query,
                                            k=self.k_query,
                                            index_path=self.index_path,
                                            basic_print=False,
                                            tui_display=True,
                                            hybrid_retrieval=(
                                                self.hybrid_retrieval),
                                            docs_bonus=0.0)
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "SEARCH KEY", "⊲━━┛", True)

                    elif self.active_ribbon_thumb == 4:
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "SEARCH SET", "⊲━━┛", False)
                        self.cli.search_dataset(dataset_path=self.dataset_path,
                                                k=self.k,
                                                save_directory=self.save_dir,
                                                index_path=self.index_path,
                                                basic_print=False,
                                                tui_display=True,
                                                expand_query=False,
                                                use_cache=True,
                                                use_ast_bonus=True,
                                                hybrid_retrieval=(
                                                    self.hybrid_retrieval),
                                                docs_bonus=0.05)
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "SEARCH SET", "⊲━━┛", True)

                    elif self.active_ribbon_thumb == 5:
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "ANSWER QUERY", "⊲━━┛", False)
                        new_question = self.input_box(
                            message="What is your request?",
                            message_color=self.cl_labels,
                            field_color=self.cl_inv_labels,
                            field_size=60,
                            field_default=self.question,
                            field_type="text",
                            active_btn_color=self.cl_button,
                            inactive_btn_color=self.cl_disabled_button,
                            frame_color=self.cl_frame,
                            default_item=1)
                        panel = self.logbooks[self.active_ribbon_thumb]
                        panel.display_logbook()
                        if new_question is not None and new_question != "":
                            self.question = new_question
                        else:
                            self.place_button(self.x_start + 61,
                                              self.y_end - 1,
                                              14, "ANSWER QUERY", "⊲━━┛", True)
                            panel = self.logbooks[self.active_ribbon_thumb]
                            panel.display_logbook()
                            if 2 <= self.active_ribbon_thumb <= 6:
                                panel.scroll_bar()
                            self.canvas.print_canvas()
                            continue
                        if self.k_question <= 0:
                            self.k_question = 10
                        new_k = self.input_box(
                            message="How many sources?",
                            message_color=self.cl_labels,
                            field_color=self.cl_inv_labels,
                            field_size=4,
                            field_default=f"{self.k_question}",
                            field_type="number",
                            active_btn_color=self.cl_button,
                            inactive_btn_color=self.cl_disabled_button,
                            frame_color=self.cl_frame,
                            default_item=1)
                        panel = self.logbooks[self.active_ribbon_thumb]
                        panel.display_logbook()
                        if new_k is not None and new_k:
                            self.k_question = int(new_k)
                        else:
                            self.place_button(self.x_start + 61,
                                              self.y_end - 1,
                                              14, "ANSWER QUERY", "⊲━━┛", True)
                            panel = self.logbooks[self.active_ribbon_thumb]
                            panel.display_logbook()
                            if 2 <= self.active_ribbon_thumb <= 6:
                                panel.scroll_bar()
                            self.canvas.print_canvas()
                            continue
                        if (self.question and self.question != ""
                           and self.k_question > 0):
                            self.cli.answer(query=self.question,
                                            k=self.k_question,
                                            index_path=self.index_path,
                                            basic_print=False,
                                            tui_display=True,
                                            hybrid_retrieval=(
                                                self.hybrid_retrieval),
                                            docs_bonus=0.05)
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "ANSWER QUERY", "⊲━━┛", True)

                    elif self.active_ribbon_thumb == 6:
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "ANSWER SET", "⊲━━┛", False)
                        p = self.search_result_path
                        self.cli.answer_dataset(student_search_results_path=p,
                                                save_directory=self.save_dir,
                                                max_context_chars=700,
                                                basic_print=False,
                                                tui_display=True)
                        self.place_button(self.x_start + 61, self.y_end - 1,
                                          14, "ANSWER SET", "⊲━━┛", True)
                    self.call_evaluate()
                    panel = self.logbooks[self.active_ribbon_thumb]
                    panel.display_logbook()
                    if 2 <= self.active_ribbon_thumb <= 6:
                        panel.scroll_bar()
                    self.canvas.print_canvas()
                elif key == "delete" and 2 <= self.active_ribbon_thumb <= 6:
                    panel = self.logbooks[self.active_ribbon_thumb]
                    panel.clear()
                    panel.display_logbook()
                    panel.scroll_bar()
                    self.canvas.print_canvas()
                elif (self.active_ribbon_thumb == 7
                      and (key == "up" or key == "down" or key == "="
                           or key == "f12" or key == "enter" or key == "+"
                           or key == "-" or key == "/" or key == "*")):
                    self.manage_settings(key=key)
                elif ((key == "up" or key == "down"
                       or key == "top" or key == "bottom"
                       or key == "pgup" or key == "pgdown")
                      and 2 <= self.active_ribbon_thumb <= 6):
                    panel = self.logbooks[self.active_ribbon_thumb]
                    topview_on_bottom = panel.height - panel.disp_height
                    scroll_moves = 0
                    if key == "up" and panel.top_view > 0:
                        scroll_moves = -1
                    elif key == "down" and panel.top_view < topview_on_bottom:
                        scroll_moves = 1
                    elif key == "top" and panel.top_view > 0:
                        scroll_moves = -panel.top_view
                    elif (key == "bottom"
                          and panel.top_view < topview_on_bottom):
                        scroll_moves = topview_on_bottom - panel.top_view
                    elif key == "pgup" and panel.top_view > 0:
                        scroll_moves = max(-20, -panel.top_view)
                    elif (key == "pgdown"
                          and panel.top_view < topview_on_bottom):
                        scroll_moves = min(
                            20,
                            topview_on_bottom - panel.top_view
                            )
                    if scroll_moves != 0:
                        panel.scroll_logbook(scroll_moves)
                        panel.display_logbook()
                        panel.scroll_bar()
                        self.canvas.print_canvas()

    def clear_data(self) -> None:
        """
        Clear all generated indices, caches, results, and logbook contents.
        """
        confirm: bool = self.confirmation_box(
            message="Do you really want to clear all current data?",
            message_color=self.cl_labels,
            active_btn_color=self.cl_button,
            inactive_btn_color=self.cl_disabled_button,
            frame_color=self.cl_frame,
            default_btn=1)

        if not confirm:
            return

        def clear_directory(directory: str) -> None:
            """
            Delete every entry inside a directory while preserving
            the directory itself.
            """
            path = Path(directory)
            if not path.exists():
                return
            for entry in path.iterdir():
                if entry.is_dir() and not entry.is_symlink():
                    shutil.rmtree(entry)
                else:
                    entry.unlink()

        def clear_file(filename: str) -> None:
            """
            Delete a file if it exists.
            """
            path = Path(filename)
            if path.exists() and path.is_file():
                path.unlink()

        clear_directory(self.index_path)
        clear_directory(self.chunks_path)
        clear_directory(self.save_dir)
        clear_directory(self.save_results_answer_dir)
        clear_directory("data/processed/query_cache")
        if self.hybrid_retrieval:
            clear_directory("data/vector")
        clear_file(self.search_result_path)
        clear_file("data/processed/index_manifest.json")
        for i in range(2, 7):
            panel = self.logbooks[i]
            panel.clear()

    def input_box(self,
                  message: str = "message",
                  message_color: str = "",
                  field_color: str = "",
                  field_size: int = 60,
                  field_default: str = "",
                  field_type: str = "text",
                  active_btn_color: str = "",
                  inactive_btn_color: str = "",
                  frame_color: str = "",
                  default_item: int = 1) -> str | None:
        """
        Display an editable input dialog and return the submitted text.
        Return an empty string when the dialog is declined or cancelled.
        """
        current_item = default_item
        current_blinker = 0
        field_text = field_default + " "
        field_pos = len(field_text) - 1
        field_view = 0
        field_inv = "\33[7m" + field_color
        field_color = "\33[0m" + field_color
        btn_a_label = "CONFIRM"
        btn_b_label = "DECLINE"
        width = 8 + max(len(message), len(btn_a_label) + len(btn_b_label) + 5,
                        field_size)
        width += 1 if width % 2 == 0 else 0
        height = 11
        x_pos = (self.x_end + 1 - self.x_start - width) // 2 + self.x_start
        y_pos = (self.y_end - 2 - self.y_start - height) // 2 + self.y_start
        x_field = x_pos + (width - field_size) // 2
        ret: str = ""

        def draw_input_buttons() -> None:
            """
            Draw the input dialog buttons according to the current selection.
            """
            btn_a_color = inactive_btn_color
            if current_item == 2:
                btn_a_color = active_btn_color
            btn_b_color = inactive_btn_color
            if current_item == 3:
                btn_b_color = active_btn_color
            btn_a_width = len(btn_a_label) + 2
            btn_b_width = len(btn_b_label) + 2
            btn_a_x = x_pos + width // 2 - 2 - btn_a_width
            btn_a_x += 1 if width % 2 == 1 else 0
            btn_b_x = x_pos + width // 2 + 2
            btn_a_txt = ("◤" + " " * (btn_a_width - 2) + "◥\n"
                         + " " + btn_a_label + " \n"
                         + "◣" + " " * (btn_a_width - 2) + "◢")
            btn_b_txt = ("◤" + " " * (btn_b_width - 2) + "◥\n"
                         + " " + btn_b_label + " \n"
                         + "◣" + " " * (btn_b_width - 2) + "◢")
            self.canvas.add_block(btn_a_x, y_pos + 6, btn_a_txt,
                                  btn_a_color, transparent=False)
            self.canvas.add_block(btn_b_x, y_pos + 6, btn_b_txt,
                                  btn_b_color, transparent=False)
            self.canvas.print_canvas()

        frame_txt = (" ╔" + "═" * (width - 4) + "╗ \n"
                     + (" ║" + " " * (width - 4) + "║ \n") * (height - 2)
                     + " ╚" + "═" * (width - 4) + "╝ ")
        self.canvas.add_block(x_pos, y_pos, frame_txt, frame_color,
                              transparent=False)
        self.canvas.add_block(x_pos + 3, y_pos + 2, message,
                              message_color, transparent=False)
        field_frame = ("▀" * (field_size + 2) + "\n"
                       + " " * (field_size + 2) + "\n"
                       + "▄" * (field_size + 2))
        self.canvas.add_block(x_field - 1, y_pos + 3, field_frame,
                              field_color, transparent=False)
        draw_input_buttons()

        self.key_control.set_input_mode(True)
        keyword_chars = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                         "0123456789_-.:/")
        path_chars = ("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
                      "0123456789/._-~' ")
        try:
            while True:
                time.sleep(self.base_wait * 2)
                current_blinker += 1
                self.canvas.add_block(x_field - 1, y_pos + 3, field_frame,
                                      field_color, transparent=False)

                if field_pos < field_view:
                    field_view = field_pos
                elif field_pos >= field_view + field_size:
                    field_view = field_pos - field_size + 1
                max_field_view = max(0, len(field_text) - field_size)
                field_view = min(field_view, max_field_view)

                visible_text = field_text[
                    field_view:field_view + field_size
                    ].ljust(field_size)
                visible_field_pos = field_pos - field_view

                if field_view > 0:
                    self.canvas.add_block(x_field - 1, y_pos + 4, "⟪",
                                          field_color, transparent=False)
                if field_view + field_size < len(field_text):
                    self.canvas.add_block(x_field + field_size,
                                          y_pos + 4, "⟫",
                                          field_color, transparent=False)

                self.canvas.add_block(x_field, y_pos + 4,
                                      visible_text, field_color,
                                      transparent=False)
                if current_blinker < 75 and current_item == 1:
                    self.canvas.add_block(x_field + visible_field_pos,
                                          y_pos + 4,
                                          visible_text[visible_field_pos],
                                          field_inv, transparent=False)
                if current_blinker >= 150:
                    current_blinker = 0
                self.canvas.print_canvas()
                key = self.key_control.key_control()
                if key == "tab":
                    current_item += 1
                    if current_item > 3:
                        current_item = 1
                    draw_input_buttons()
                elif key == "backtab":
                    current_item -= 1
                    if current_item < 1:
                        current_item = 3
                    draw_input_buttons()
                elif key == "enter":
                    if current_item == 3:
                        return ""
                    else:
                        ret = field_text[:-1]
                        break
                elif key == "esc":
                    return ""
                elif key == "left" and current_item == 1:
                    field_pos = max(field_pos - 1, 0)
                elif key == "right" and current_item == 1:
                    field_pos = min(field_pos + 1, len(field_text) - 1)
                elif key == "home" and current_item == 1:
                    field_pos = 0
                elif key == "end" and current_item == 1:
                    field_pos = len(field_text) - 1
                elif key == "delete" and current_item == 1:
                    if field_pos < len(field_text) - 1:
                        field_text = (field_text[:field_pos]
                                      + field_text[field_pos + 1:])
                elif key == "backspace" and current_item == 1:
                    if field_pos > 0:
                        field_text = (field_text[:field_pos - 1]
                                      + field_text[field_pos:])
                        field_pos -= 1
                elif key and len(key) == 1 and current_item == 1:
                    valid = ((field_type == "text" and 32 <= ord(key) <= 126)
                             or (field_type == "number" and key.isdigit())
                             or (field_type == "path" and key in path_chars)
                             or (field_type == "keyword"
                                 and key in keyword_chars))
                    if valid:
                        field_text = (field_text[:field_pos] + key
                                      + field_text[field_pos:])
                        field_pos += 1
        finally:
            self.key_control.set_input_mode(False)

        return ret

    def confirmation_box(self,
                         message: str = "message",
                         message_color: str = "",
                         active_btn_color: str = "",
                         inactive_btn_color: str = "",
                         frame_color: str = "",
                         default_btn: int = 1) -> bool:
        """ Display a confirmation dialog and return the selected response. """
        current_btn = default_btn
        btn_a_label = "CONFIRM"
        btn_b_label = "DECLINE"
        width = max(len(message), len(btn_a_label) + len(btn_b_label) + 5) + 6
        width += 1 if width % 2 == 0 else 0
        height = 9
        x_pos = (self.x_end + 1 - self.x_start - width) // 2 + self.x_start
        y_pos = (self.y_end - 2 - self.y_start - height) // 2 + self.y_start
        ret: bool = False

        def draw_confirmation_buttons() -> None:
            """
            Draw the confirmation buttons according to the current selection.
            """
            btn_a_color = inactive_btn_color
            if current_btn == 1:
                btn_a_color = active_btn_color
            btn_b_color = inactive_btn_color
            if current_btn == 2:
                btn_b_color = active_btn_color
            btn_a_width = len(btn_a_label) + 2
            btn_b_width = len(btn_b_label) + 2
            btn_a_x = x_pos + width // 2 - 1 - btn_a_width
            btn_a_x -= 1 if width % 2 == 0 else 0
            btn_b_x = x_pos + width // 2 + 2
            btn_a_txt = ("◤" + " " * (btn_a_width - 2) + "◥\n"
                         + " " + btn_a_label + " \n"
                         + "◣" + " " * (btn_a_width - 2) + "◢")
            btn_b_txt = ("◤" + " " * (btn_b_width - 2) + "◥\n"
                         + " " + btn_b_label + " \n"
                         + "◣" + " " * (btn_b_width - 2) + "◢")
            self.canvas.add_block(btn_a_x, y_pos + 4, btn_a_txt,
                                  btn_a_color, transparent=False)
            self.canvas.add_block(btn_b_x, y_pos + 4, btn_b_txt,
                                  btn_b_color, transparent=False)
            self.canvas.print_canvas()

        frame_txt = (" ╔" + "═" * (width - 4) + "╗ \n"
                     + (" ║" + " " * (width - 4) + "║ \n") * (height - 2)
                     + " ╚" + "═" * (width - 4) + "╝ ")
        self.canvas.add_block(x_pos, y_pos, frame_txt, frame_color,
                              transparent=False)
        self.canvas.add_block(x_pos + 3, y_pos + 2, message,
                              message_color, transparent=False)
        draw_confirmation_buttons()

        self.key_control.set_input_mode(True)
        try:
            while True:
                time.sleep(self.base_wait * 20)
                key = self.key_control.key_control()
                if (key == "left" or key == "right"
                   or key == "tab" or key == "backtab"):
                    current_btn += 1
                    if current_btn > 2:
                        current_btn = 1
                    draw_confirmation_buttons()
                elif key == "enter":
                    if current_btn == 1:
                        ret = True
                    break
                elif key == "esc":
                    break
        finally:
            self.key_control.set_input_mode(False)
        return ret

    def build_settings_tab(self) -> None:
        """ Build the settings panel and initialize its displayed values. """
        panel = self.logbooks[7]
        frame = ("╭" + "─" * 20 + "┬" + "─" * 12 + "┬" + "─" * 70 + "┬"
                 + "─" * 25 + "╮\n"
                 + ("│" + " " * 20 + "│" + " " * 12 + "│" + " " * 70 + "│"
                    + " " * 25 + "│\n") * 13
                 + "╰" + "─" * 20 + "┴" + "─" * 12 + "┴" + "─" * 70 + "┴"
                 + "─" * 25 + "╯")
        panel.add_log_block(2, 2, frame, self.cl_log_item)
        panel.add_log_block(47, 0,
                            self.canvas.large_text_block("Location Paths"),
                            self.cl_highlight_text, transparent=True)
        frame = ("╭" + "─" * 20 + "┬" + "─" * 12 + "┬" + "─" * 8 + "┬"
                 + "─" * 18 + "╮ ╭" + "─" * 66 + "╮\n"
                 + ("│" + " " * 20 + "│" + " " * 12 + "│" + " " * 8 + "│"
                    + " " * 18 + "│ │" + " " * 66 + "│\n") * 7
                 + "╰" + "─" * 20 + "┴" + "─" * 12 + "┴" + "─" * 8 + "┴"
                 + "─" * 18 + "╯ ╰" + "─" * 66 + "╯")
        panel.add_log_block(2, 19, frame, self.cl_log_item)
        panel.add_log_block(4, 17,
                            self.canvas.large_text_block("Values"),
                            self.cl_highlight_text, transparent=True)
        panel.add_log_block(99, 17,
                            self.canvas.large_text_block("Color Theme"),
                            self.cl_highlight_text, transparent=True)
        labels_tl = ("Raw Data", "BM25 Index", "Chunks", "Unanswered Dataset",
                     "Answered Dataset", "Search Results", "Answer Results")
        labels_tr = ("data_path", "index_path", "chunks_path",
                     "dataset_path", "dataset_answered",
                     "save_directory (search)", "save_directory (answer)")
        y = 3
        for i in range(7):
            panel.add_log_block(4, y + i * 2, labels_tl[i], self.cl_text)
            panel.add_log_block(109, y + i * 2, labels_tr[i], self.cl_ita_text)
        labels_bl = ("Dataset Name", "Chunk Limit",
                     "Number of Results", "Search Mode")
        labels_br = ("dataset_scope", "max_chunk_size", "k",
                     "hybrid_retrieval")
        y = 20
        for i in range(4):
            panel.add_log_block(4, y + i * 2, labels_bl[i], self.cl_text)
            panel.add_log_block(47, y + i * 2, labels_br[i], self.cl_ita_text)
        self.manage_settings(key="init")

    def manage_settings(self, key: str = "") -> None:
        """ Handle user interactions within the settings panel. """
        panel = self.logbooks[7]
        datasets_shortnames: list[str] = ["docs", "code", "custom"]
        confirm: bool = False

        def draw_settings_buttons() -> None:
            """
            Draw the settings action buttons according to the current focus.
            """
            buttons = (("edit", 3), ("edit", 5), ("edit", 7), ("edit", 9),
                       ("edit", 11), ("edit", 13), ("edit", 15), ("-+", 20),
                       ("edit", 22), ("edit", 24), ("-+", 26))
            for i in range(11):
                color = self.cl_disabled_button
                if self.settings_focus == i + 1:
                    color = self.cl_button
                label, y = buttons[i]
                if label == "edit":
                    panel.add_log_block(25, y,
                                        f"{NBSP}" * 3 + "EDIT" + f"{NBSP}" * 3,
                                        color)
                elif label == "-+":
                    panel.add_log_block(26, y, f"{NBSP}" + "-" + f"{NBSP}",
                                        color)
                    panel.add_log_block(31, y, f"{NBSP}" + "+" + f"{NBSP}",
                                        color)
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()

        def display_settings_fields() -> None:
            """
            Display every editable setting and update the action buttons.
            """
            rows = (3, 5, 7, 9, 11, 13, 15, 20, 22, 24, 26)
            txt = ""
            for i, y in enumerate(rows):
                if 0 <= i <= 6:
                    panel.add_log_block(37, y, " " * 70,
                                        self.cl_alt_text)
                    txt = str(self.settings_value[i])
                    if len(txt) > 68:
                        txt = txt[:67] + "⟫"
                elif i == 7:
                    panel.add_log_block(37, y, " " * 8,
                                        self.cl_alt_text)
                    txt = datasets_shortnames[int(self.settings_value[i])]
                    txt = f"{txt.capitalize():^6}"
                elif 8 <= i <= 9:
                    panel.add_log_block(37, y, " " * 8,
                                        self.cl_alt_text)
                    txt = str(self.settings_value[i])
                    if len(txt) > 6:
                        txt = txt[:5] + "⟫"
                    else:
                        txt = f"{txt:^6}"
                elif i == 10:
                    panel.add_log_block(37, y, " " * 8,
                                        self.cl_alt_text)
                    txt = "BM25"
                    if self.settings_value[i] is True:
                        txt = "Hybrid"
                panel.add_log_block(38, y, f"{txt:^6}",
                                    self.cl_alt_text)
            if (self.settings_value[0] == self.default_data_path
                and self.settings_value[1] == self.default_index_path
                and self.settings_value[2] == self.default_chunks_path
                and self.settings_value[3]
                    == str(Path(self.default_dataset_path).parent)
                and self.settings_value[4]
                    == str(Path(self.default_dataset_answered).parent)
                and self.settings_value[5] == self.default_save_dir
                and self.settings_value[6]
                    == self.default_save_results_answer_dir
                and self.settings_value[7] == self.default_dataset_index
                and self.settings_value[8]
                    == f"{self.default_max_chunk_size}"
                and self.settings_value[9] == f"{self.default_k}"
                and self.settings_value[10]
                    == self.default_hybrid_retrieval
                and self.settings_value[11]
                    == self.default_color_theme_index):
                self.settings_default_button = False
            else:
                self.settings_default_button = True
            if self.active_ribbon_thumb == 7:
                self.place_button(self.x_start + 61, self.y_end - 1, 7,
                                  "RESET", "=",
                                  self.settings_default_button,
                                  cut_right=True)

            if (self.settings_value[0] == self.data_path
                and self.settings_value[1] == self.index_path
                and self.settings_value[2] == self.chunks_path
                and self.settings_value[3]
                    == str(Path(self.dataset_path).parent)
                and self.settings_value[4]
                    == str(Path(self.dataset_answered).parent)
                and self.settings_value[5] == self.save_dir
                and self.settings_value[6]
                    == self.save_results_answer_dir
                and self.settings_value[7] == self.dataset_index
                and self.settings_value[8]
                    == f"{self.max_chunk_size}"
                and self.settings_value[9] == f"{self.k}"
                and self.settings_value[10] == self.hybrid_retrieval
                and self.settings_value[11]
                    == self.color_theme_index):
                self.settings_save_button = False
            else:
                self.settings_save_button = True
            if self.active_ribbon_thumb == 7:
                self.place_button(self.x_start + 68, self.y_end - 1, 6,
                                  "APPLY", " F12 ",
                                  self.settings_save_button,
                                  cut_left=True)

        def display_color_preview(theme: ColorTheme) -> None:
            """ Render a preview of the currently selected color theme. """
            for y in range(20, 27):
                for x in range(67, 133):
                    cell = self.canvas._grid[y + 12][x + 2]
                    panel.add_log_block(x, y, cell.built_ch,
                                        theme.log_background)
            y = 21
            for x in range(68, 101):
                cell = self.canvas._grid[y + 12][x + 2]
                panel.add_log_block(x, y, cell.built_ch, theme.main_background)
            x = 131
            for y in range(21, 26):
                cell = self.canvas._grid[y + 12][x + 2]
                panel.add_log_block(x, y, cell.built_ch, theme.main_background)
            panel.add_log_block(67, 20, "╔═════════════════════════════════"
                                + "╤════════════════════════════╤═╗",
                                theme.frame)
            panel.add_log_block(67, 26, "╚═════════════════════════════════"
                                + "═════════════════════════════╧═╝",
                                theme.frame)
            for y in range(21, 26):
                panel.add_log_block(67, y, "║", theme.frame)
                panel.add_log_block(132, y, "║", theme.frame)
                panel.add_log_block(130, y, "│", theme.frame)
            panel.add_log_block(101, 21, "│", theme.frame)
            panel.add_log_block(67, 22, "╟─────────────────────────────────╯",
                                theme.frame)
            panel.add_log_block(69, 21, f"{"CYCLE  THEMES":^31}", theme.labels,
                                transparent=True)
            panel.add_log_block(72, 21, f"◤{NBSP}/{NBSP}◥", theme.inv_labels,
                                transparent=True)
            panel.add_log_block(92, 21, f"◤{NBSP}*{NBSP}◥", theme.inv_labels,
                                transparent=True)
            txt = ""
            tmp = self.color_theme(index=int(self.settings_value[11]),
                                   command="tell_name")
            if isinstance(tmp, str):
                txt = tmp
            panel.add_log_block(102, 21, f"{txt:^28}", theme.highlight_text,
                                transparent=True)
            panel.add_log_block(131, 21, "◢", theme.labels)
            panel.add_log_block(131, 25, "◥", theme.dim_labels)
            panel.add_log_block(131, 23, "▄\n▀", theme.scroll_bar)
            panel.add_log_block(69, 24,
                                f"◤{NBSP}ACTIVE{NBSP}◥\n◣{NBSP}BUTTON{NBSP}◢",
                                theme.button)
            panel.add_log_block(119, 24, f"◤INACTIVE◥\n◣{NBSP}BUTTON{NBSP}◢",
                                theme.disabled_button)
            panel.add_log_block(80, 25,
                                "───━━━══              (     ) ══━━━───",
                                theme.log_item, transparent=True)
            panel.add_log_block(89, 25, "Reading done",
                                theme.dim_text, transparent=True)
            panel.add_log_block(103, 25, "0.42s", theme.dim_alt_text)
            panel.add_log_block(80, 24, "∎" * 38, theme.alt_text)
            txt = ("dataset_"
                   + datasets_shortnames[int(self.settings_value[7])]
                   + "_public.json")
            x = 82 - len(datasets_shortnames[int(self.settings_value[7])]) // 2
            panel.add_log_block(x, 23, "Reading file", theme.text,
                                transparent=True)
            panel.add_log_block(x + 13, 23, txt, theme.alt_text,
                                transparent=True)
            panel.add_log_block(x + 13 + len(txt), 23, ".", theme.text)

        if key == "init":
            self.settings_value = [
                self.data_path,
                self.index_path,
                self.chunks_path,
                str(Path(self.dataset_path).parent),
                str(Path(self.dataset_answered).parent),
                self.save_dir,
                self.save_results_answer_dir,
                self.dataset_index,
                f"{self.max_chunk_size}",
                f"{self.k}",
                self.hybrid_retrieval,
                self.color_theme_index,
            ]
            view_theme = self.color_theme(index=int(self.settings_value[11]),
                                          command="pack_theme")
            if isinstance(view_theme, ColorTheme):
                display_color_preview(view_theme)
            draw_settings_buttons()
            display_settings_fields()

        elif key == "up":
            self.settings_focus -= 1
            if self.settings_focus <= 0:
                self.settings_focus = 11
            draw_settings_buttons()

        elif key == "down":
            self.settings_focus += 1
            if self.settings_focus > 11:
                self.settings_focus = 1
            draw_settings_buttons()

        elif key == "enter":
            labels = ("Raw Data", "BM25 Index", "Chunks", "Unanswered Dataset",
                      "Answered Dataset", "Search Results", "Answer Results",
                      "Dataset Name", "Chunk Limit", "Number of Results",
                      "Search Mode")
            focus = self.settings_focus - 1
            if 1 <= self.settings_focus <= 7:
                txt = str(
                    self.input_box(
                        message=f"Enter {labels[focus]} path:",
                        message_color=self.cl_labels,
                        field_color=self.cl_inv_labels,
                        field_size=70,
                        field_default=str(self.settings_value[focus]),
                        field_type="path",
                        active_btn_color=self.cl_button,
                        inactive_btn_color=self.cl_disabled_button,
                        frame_color=self.cl_frame,
                        default_item=1
                        )
                    )
                if txt and txt != "":
                    self.settings_value[focus] = txt
            if 9 <= self.settings_focus <= 10:
                txt = str(
                    self.input_box(
                        message=f"Enter {labels[focus]} value:",
                        message_color=self.cl_labels,
                        field_color=self.cl_inv_labels,
                        field_size=6,
                        field_default=str(self.settings_value[focus]),
                        field_type="number",
                        active_btn_color=self.cl_button,
                        inactive_btn_color=self.cl_disabled_button,
                        frame_color=self.cl_frame,
                        default_item=1
                        )
                    )
                if txt and txt != "":
                    self.settings_value[focus] = txt
            draw_settings_buttons()
            display_settings_fields()
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()

        elif key == "+" or key == "-":
            focus = self.settings_focus - 1
            if self.settings_focus == 8:
                nb_items = 3
                val = int(self.settings_value[focus])
                if key == "+":
                    val += 1
                elif key == "-":
                    val -= 1
                if val < 0:
                    val = nb_items - 1
                elif val >= nb_items:
                    val = 0
                self.settings_value[focus] = val
            elif self.settings_focus == 11:
                nb_items = 2
                val = 1 if self.settings_value[focus] else 0
                if key == "+":
                    val += 1
                elif key == "-":
                    val -= 1
                if val < 0:
                    val = nb_items - 1
                elif val >= nb_items:
                    val = 0
                if val == 0:
                    self.settings_value[focus] = False
                elif val == 1:
                    self.settings_value[focus] = True
            view_theme = self.color_theme(index=int(self.settings_value[11]),
                                          command="pack_theme")
            if isinstance(view_theme, ColorTheme):
                display_color_preview(view_theme)
            draw_settings_buttons()
            display_settings_fields()
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()

        elif key == "*" or key == "/":
            nb_items = 16
            val = int(self.settings_value[11])
            if key == "*":
                val += 1
            elif key == "/":
                val -= 1
            if val < 0:
                val = nb_items - 1
            elif val >= nb_items:
                val = 0
            self.settings_value[11] = val
            view_theme = self.color_theme(index=int(self.settings_value[11]),
                                          command="pack_theme")
            if isinstance(view_theme, ColorTheme):
                display_color_preview(view_theme)
            draw_settings_buttons()
            display_settings_fields()
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()

        elif key == "=" and self.settings_default_button:
            confirm = self.confirmation_box(
                message="Do you really want to reset all values to defaults?",
                message_color=self.cl_labels,
                active_btn_color=self.cl_button,
                inactive_btn_color=self.cl_disabled_button,
                frame_color=self.cl_frame,
                default_btn=1)
            if confirm:
                self.settings_value = [
                    self.default_data_path,
                    self.default_index_path,
                    self.default_chunks_path,
                    str(Path(self.default_dataset_path).parent),
                    str(Path(self.default_dataset_answered).parent),
                    self.default_save_dir,
                    self.default_save_results_answer_dir,
                    self.default_dataset_index,
                    f"{self.default_max_chunk_size}",
                    f"{self.default_k}",
                    self.default_hybrid_retrieval,
                    self.default_color_theme_index,
                ]
            view_theme = self.color_theme(index=int(self.settings_value[11]),
                                          command="pack_theme")
            if isinstance(view_theme, ColorTheme):
                display_color_preview(view_theme)
            draw_settings_buttons()
            display_settings_fields()
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()

        elif key == "f12" and self.settings_save_button:
            confirm = self.confirmation_box(
                message="Do you really want to save and apply these values?",
                message_color=self.cl_labels,
                active_btn_color=self.cl_button,
                inactive_btn_color=self.cl_disabled_button,
                frame_color=self.cl_frame,
                default_btn=1)
            draw_settings_buttons()
            display_settings_fields()
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()
            if confirm:
                self.color_theme(index=int(self.settings_value[11]),
                                 old_index=self.color_theme_index,
                                 command="switch")
                filename = ("/dataset_"
                            + datasets_shortnames[int(self.settings_value[7])]
                            + "_public.json")
                self.data_path = str(self.settings_value[0])
                self.index_path = str(self.settings_value[1])
                self.chunks_path = str(self.settings_value[2])
                self.dataset_path = str(self.settings_value[3]) + filename
                self.dataset_answered = str(self.settings_value[4]) + filename
                self.search_result_path = (str(self.settings_value[5])
                                           + filename)
                self.save_dir = str(self.settings_value[5])
                self.save_results_answer_dir = str(self.settings_value[6])
                self.max_chunk_size = int(self.settings_value[8])
                self.k = int(self.settings_value[9])
                self.dataset_index = int(self.settings_value[7])
                if isinstance(self.settings_value[10], bool):
                    self.hybrid_retrieval = self.settings_value[10]
                self.color_theme_index = int(self.settings_value[11])
                self.k_query = self.k
                self.k_question = self.k
                self.save_settings()
            draw_settings_buttons()
            display_settings_fields()
            if self.active_ribbon_thumb == 7:
                panel.display_logbook()
            self.call_evaluate()

    def save_settings(self) -> None:
        """Save the current interface settings to data/config.ini."""
        config = configparser.ConfigParser()
        config["paths"] = {
            "data_path": self.data_path,
            "index_path": self.index_path,
            "chunks_path": self.chunks_path,
            "dataset_path": self.dataset_path,
            "dataset_answered": self.dataset_answered,
            "search_result_path": self.search_result_path,
            "save_dir": self.save_dir,
            "save_results_answer_dir": self.save_results_answer_dir,
        }
        hybrid_retrieval_txt = "True" if self.hybrid_retrieval else "False"
        config["values"] = {
            "max_chunk_size": str(self.max_chunk_size),
            "k": str(self.k),
            "dataset_index": str(self.dataset_index),
            "hybrid_retrieval": hybrid_retrieval_txt,
            "color_theme_index": str(self.color_theme_index),
        }
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with CONFIG_PATH.open("w", encoding="utf-8") as config_file:
            config.write(config_file)

    def load_settings(self) -> bool:
        """Load interface settings from data/config.ini if it exists."""
        if not CONFIG_PATH.is_file():
            return False
        config = configparser.ConfigParser()

        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
                config.read_file(config_file)
            paths = config["paths"]
            values = config["values"]

            data_path = paths.get("data_path", self.data_path)
            index_path = paths.get("index_path", self.index_path)
            chunks_path = paths.get("chunks_path", self.chunks_path)
            dataset_path = paths.get("dataset_path", self.dataset_path)
            dataset_answered = paths.get("dataset_answered",
                                         self.dataset_answered)
            search_result_path = paths.get("search_result_path",
                                           self.search_result_path)
            save_dir = paths.get("save_dir", self.save_dir)
            save_results_answer_dir = paths.get("save_results_answer_dir",
                                                self.save_results_answer_dir)
            max_chunk_size = values.getint("max_chunk_size",
                                           fallback=self.max_chunk_size)
            k = values.getint("k", fallback=self.k)
            dataset_index = values.getint("dataset_index",
                                          fallback=self.dataset_index)
            hybrid_retrieval = values.getboolean(
                "hybrid_retrieval",
                fallback=self.hybrid_retrieval)
            color_theme_index = values.getint("color_theme_index",
                                              fallback=self.color_theme_index)
        except (OSError, configparser.Error, KeyError, ValueError):
            return False

        if max_chunk_size <= 0:
            raise ValueError("max_chunk_size must be positive")
        if k <= 0:
            raise ValueError("k must be positive")
        if not 0 <= dataset_index < 3:
            raise ValueError("Invalid dataset index")
        if not 0 <= color_theme_index < 16:
            raise ValueError("Invalid color theme index")

        self.data_path = data_path
        self.index_path = index_path
        self.chunks_path = chunks_path
        self.dataset_path = dataset_path
        self.dataset_answered = dataset_answered
        self.search_result_path = search_result_path
        self.save_dir = save_dir
        self.save_results_answer_dir = save_results_answer_dir
        self.max_chunk_size = max_chunk_size
        self.k = k
        self.dataset_index = dataset_index
        self.hybrid_retrieval = hybrid_retrieval
        self.color_theme_index = color_theme_index
        return True

    def color_theme(self, index: int = 0, old_index: int = 0,
                    command: str = "") -> str | ColorTheme | None:
        """ Return, activate, preview, or switch the selected color theme. """
        colors = self.colors
        themes = [
            ["Matrix", colors.MEDIUM_TEAL_GREEN, colors.MEDIUM_CYAN],
            ["Volcano", colors.MEDIUM_RED, colors.ORANGE],
            ["Retina Break", colors.ORANGE, colors.VIOLET],
            ["Canopy", colors.MEDIUM_GREEN, colors.MEDIUM_BEIGE],
            ["Deep Blue", colors.MEDIUM_BLUE, colors.MEDIUM_CYAN],
            ["Nuka Cola", colors.LIGHT_DEEP_RED, colors.LIGHTER_BEIGE],
            ["Vault Tec", colors.BLUE, colors.PALE_GOLD],
            ["Dry Grassland", colors.encode_color(215, 185, 60, 0, 0, 0),
             colors.encode_color(60, 140, 70, 0, 0, 0)],
            ["Witch Lace", colors.MEDIUM_PURPLE, colors.LIGHT_VIOLET],
            ["Gingerbread", colors.WARM_LIGHT_BROWN, colors.MEDIUM_GOLD],
            ["Lemonade", colors.LIGHT_YELLOW, colors.LIGHT_LIME],
            ["GLaDOS Legacy", colors.encode_color(0, 140, 255, 0, 0, 0),
             colors.encode_color(255, 140, 0, 0, 0, 0)],
            ["T.A.R.D.I.S", colors.encode_color(0, 70, 165, 0, 0, 0),
             colors.encode_color(245, 240, 220, 0, 0, 0)],
            ["Synthwave", colors.encode_color(255, 45, 180, 0, 0, 0),
             colors.encode_color(0, 220, 255, 0, 0, 0)],
            ["Weyland-Yutani", colors.encode_color(90, 255, 120, 0, 0, 0),
             colors.encode_color(145, 160, 170, 0, 0, 0)],
            ["IBM's CGA", colors.PINK, colors.CYAN],
        ]

        def switch_color(code: str, theme: ColorTheme, label: bool) -> str:
            """
            Convert a color code between a theme value and
            its semantic field name.
            """
            if code == self.colors.BASE_RED:
                return self.colors.BASE_RED
            values = theme.model_dump()
            if label:
                color_to_field = {
                    color: field_name for field_name, color in values.items()
                    }
                field_name = color_to_field.get(code)
                if field_name is not None:
                    return str(field_name)
                return code
            else:
                color = values.get(code)
                if color is not None:
                    return str(color)
                return code

        def replace_colors_in_grids(theme: ColorTheme, label: bool) -> None:
            """
            Replace theme-dependent colors throughout the canvas
            and logbook grids.
            """
            for y in range(self.canvas.yoffset - 1, self.canvas.height):
                for x in range(self.canvas.xoffset - 1, self.canvas.width):
                    cell = self.canvas._grid[y][x]
                    cell.color = switch_color(cell.color, theme, label)
                    cell.built_color = switch_color(cell.built_color,
                                                    theme, label)
            for i in range(1, 8):
                panel = self.logbooks[i]
                for y in range(panel.height):
                    for x in range(panel.width):
                        if (i == 7 and 20 <= y <= 26 and 67 <= x <= 132):
                            continue
                        logcell = panel.grid[y][x]
                        logcell.color = switch_color(logcell.color,
                                                     theme, label)

        if command == "tell_name":
            return themes[index][0]
        elif command == "pack_theme":
            theme = ColorTheme()
            theme.frame = self.colors.BROWN
            theme.main_background = self.colors.scale_color(theme.frame, 0.2)
            theme.labels = self.colors.LIGHT_BEIGE
            theme.dim_labels = self.colors.scale_color(theme.labels, 0.5)
            theme.inv_labels = self.colors.reverse_foreback_colors(
                theme.labels
                )
            theme.text = themes[index][1]
            theme.ita_text = self.colors.italic_color(theme.text)
            theme.inv_text = self.colors.reverse_foreback_colors(theme.text)
            theme.dim_text = self.colors.scale_color(theme.text, 0.75)
            theme.highlight_text = self.colors.scale_color(theme.text, 1.5)
            theme.alt_text = themes[index][2]
            theme.alt_inv_text = self.colors.reverse_foreback_colors(
                theme.alt_text
                )
            theme.dim_alt_text = self.colors.scale_color(theme.alt_text, 0.75)
            theme.highlight_alt_text = self.colors.scale_color(theme.alt_text,
                                                               1.5)
            fr, fg, fb, br, bg, bb = self.colors.decode_color(theme.text)
            sum_rgb = fr + fg + fb + br + bg + bb
            scale = 0.16
            if 256 <= sum_rgb < 512:
                scale = 0.18
            elif sum_rgb < 256:
                scale = 0.2
            theme.log_background = self.colors.scale_color(theme.text, scale)
            theme.button = self.colors.reverse_foreback_colors(theme.text)
            theme.disabled_button = self.colors.scale_color(theme.button, 0.4)
            theme.scroll_bar = self.colors.scale_color_fore(theme.text, 0.8)
            theme.log_item = self.colors.average_colors(
                self.colors.scale_color(self.colors.GREY, 1),
                self.colors.scale_color(theme.text, 0.25))
            return theme
        elif command == "switch":
            old_theme = self.color_theme(index=old_index, command="pack_theme")
            new_theme = self.color_theme(index=index, command="pack_theme")
            if isinstance(old_theme, ColorTheme):
                replace_colors_in_grids(theme=old_theme, label=True)
            if isinstance(new_theme, ColorTheme):
                replace_colors_in_grids(theme=new_theme, label=False)
                self.color_theme(index=index, command="activate")
            return None
        elif command == "activate":
            new_theme = self.color_theme(index=index, command="pack_theme")
            if isinstance(new_theme, ColorTheme):
                self.cl_frame = new_theme.frame
                self.cl_main_background = new_theme.main_background
                self.cl_labels = new_theme.labels
                self.cl_dim_labels = new_theme.dim_labels
                self.cl_inv_labels = new_theme.inv_labels
                self.cl_text = new_theme.text
                self.cl_ita_text = new_theme.ita_text
                self.cl_inv_text = new_theme.inv_text
                self.cl_dim_text = new_theme.dim_text
                self.cl_highlight_text = new_theme.highlight_text
                self.cl_alt_text = new_theme.alt_text
                self.cl_alt_inv_text = new_theme.alt_inv_text
                self.cl_dim_alt_text = new_theme.dim_alt_text
                self.cl_highlight_alt_text = new_theme.highlight_alt_text
                self.cl_log_background = new_theme.log_background
                self.cl_button = new_theme.button
                self.cl_disabled_button = new_theme.disabled_button
                self.cl_scroll_bar = new_theme.scroll_bar
                self.cl_log_item = new_theme.log_item
            return None
        return None

    def build_home_text(self) -> None:
        """ Build the usage instructions displayed on the Home tab. """
        panel = self.logbooks[1]
        txt: list[str] = ["Meet the ", "RAG against the machine",
                          " interface"]
        txt_len = sum(len(part) for part in txt)
        offset = (self.x_end + 1 - self.x_start - (txt_len * 3)) // 2
        for i, part in enumerate(txt):
            large_part = self.canvas.large_text_block(part)
            color = self.cl_alt_text if i == 1 else self.cl_text
            panel.add_log_block(offset, 1, large_part, color)
            offset += len(txt[i]) * 3
        txt = ["Where ", "CLIs", " come to ", "Life"]
        txt_len = sum(len(part) for part in txt)
        offset = (self.x_end + 1 - self.x_start - txt_len) // 2
        for i, part in enumerate(txt):
            color = self.cl_alt_text if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 5, part, color)
            offset += len(part)
        panel.add_log_block(2, 7, "HOW TO USE IT:", self.cl_highlight_text)
        for y in {9, 11, 14, 17, 19, 22, 24, 26}:
            panel.add_log_block(2, y, "●", self.cl_alt_text)
        txt = ["Use the horizontal arrows ", f"◤{NBSP}⇦{NBSP}◥", " ",
               f"◤{NBSP}⇨{NBSP}◥", " to browse between tabs or press the "
               "function keys ",
               "◤F1◥", "...", "◤F7◥", " to jump directly to a tab."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 9, part, color)
            offset += len(part)
        txt = ["When available, use the vertical arrows ", f"◤{NBSP}⇧{NBSP}◥",
               " ", f"◤{NBSP}⇩{NBSP}◥", " and Page Up/Page Down ",
               f"◤{NBSP}↟{NBSP}◥ ◤{NBSP}↡{NBSP}◥",
               " to scroll through the log,"]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 11, part, color)
            offset += len(part)
        txt = ["or press the Home/End ", f"◤{NBSP}⤒{NBSP}◥",
               " ", f"◤{NBSP}⤓{NBSP}◥",
               " keys to scroll to the top or the bottom of the log."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 12, part, color)
            offset += len(part)
        txt = ["Each tab provides a main action triggered by pressing Enter ",
               f"◤{NBSP}⊲━━┛{NBSP}◥", " or Space ",
               f"◤{NBSP}{NBSP}⌞{NBSP}{NBSP}{NBSP}{NBSP}⌟{NBSP}{NBSP}◥", "."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 14, part, color)
            offset += len(part)
        txt = ["Depending on the tab's purpose, a text field may appear."]
        panel.add_log_block(5, 15, txt, self.cl_text)
        txt = ["On this Home tab, the main action ", "ERASES",
               " all previous results. Use it with ", "EXTREME",
               " caution. Or don't. Your call."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_alt_text if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 17, part, color)
            offset += len(part)
        txt = ["On each processing tab, press Del ",
               f"◤{NBSP}⊏≻{NBSP}◥", " or Backspace ", f"◤{NBSP}⊲━━━{NBSP}◥",
               " to clear the tab's log."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 19, part, color)
            offset += len(part)
        txt = ["There will be no confirmation. You are trusted."]
        panel.add_log_block(5, 20, txt, self.cl_text)
        txt = ["The Settings tab allows you to change paths, values and "
               "color themes. Use ", f"◤{NBSP}={NBSP}◥",
               " to restore defaults and ", "◤F12◥", " to save settings."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 22, part, color)
            offset += len(part)
        txt = ["The ", "statistics", " below are updated after each ",
               "action", "."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_alt_text if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 24, part, color)
            offset += len(part)
        txt = ["You can press ", f"◤{NBSP}ESC{NBSP}◥",
               " at any time to exit this program."]
        offset = 5
        for i, part in enumerate(txt):
            color = self.cl_inv_labels if i % 2 == 1 else self.cl_text
            panel.add_log_block(offset, 26, part, color)
            offset += len(part)

    def receive_event(self, event: LogEvent) -> None:
        """ Display one log event in the corresponding interface panel. """
        panel_by_source = {
            "index": self.logbooks[2],
            "search": self.logbooks[3],
            "search_dataset": self.logbooks[4],
            "answer": self.logbooks[5],
            "answer_dataset": self.logbooks[6],
        }

        panel = panel_by_source.get(event.source)
        if panel is None:
            return

        if event.type == "start":
            y = panel.next_empty_log_line() - 1
            panel.add_separator_line(y + 1, self.cl_log_item)
            msg_len = len(event.message)
            offset = (130 - msg_len) // 2 + 2
            msg_box = ("╭" + "─" * msg_len + "╮\n╡" + " " * msg_len
                       + "╞\n╰" + "─" * msg_len + "╯")
            panel.add_log_block(offset, y, msg_box, self.cl_log_item)
            panel.add_log_block(offset + 1, y + 1, event.message,
                                self.cl_dim_text)
            panel.add_empty_log_line(1)

        elif event.type == "info":
            y = panel.next_empty_log_line()
            offset = 2
            panel.add_log_block(offset, y, event.message, self.cl_text)
            offset += len(event.message)
            panel.add_log_block(offset, y, event.text_var,
                                self.cl_alt_text)
            offset += len(event.text_var)
            panel.add_log_block(offset, y, event.message_end, self.cl_text)
            panel.add_empty_log_line(1)

        elif event.type == "error" or event.type == "warning":
            color = self.colors.BASE_RED
            label = "ERROR: "
            if event.type == "warning":
                color = self.colors.MEDIUM_ORANGE
                label = "WARNING: "
            width = len(event.message) + len(label) + 3
            y = panel.next_empty_log_line()
            panel.add_log_block(2, y, "╭" + "─" * (width - 2) + "╮", color)
            panel.add_log_block(2, y + 1, "│" + " " * (width - 2) + "│", color)
            panel.add_log_block(2, y + 2, "╰" + "─" * (width - 2) + "╯", color)
            offset = 4
            panel.add_log_block(offset, y + 1, label, color)
            offset += len(label)
            panel.add_log_block(offset, y + 1, event.message, self.cl_text)
            panel.add_empty_log_line(1)

        elif event.type == "progbar":
            if event.value == -1000.0:
                self.event_progbar_y = panel.next_empty_log_line()
                self.event_progbar_title = event.message
                self.event_progbar_value = 0
                panel.add_log_block(2, self.event_progbar_y,
                                    f"{event.message}:", self.cl_text)
            elif (1000.0 > event.value > 0.0
                  and event.message == self.event_progbar_title
                  and event.value > self.event_progbar_value):
                self.event_progbar_value = max(0.0, min(event.value, 100.0))
                nb_bricks = int(
                    (128 - len(event.message))
                    * (self.event_progbar_value / 100)
                    )
                panel.add_log_block(len(event.message) + 4,
                                    self.event_progbar_y,
                                    "∎" * nb_bricks,
                                    self.cl_alt_text)
            elif event.value == 1000.0:
                self.event_progbar_value = 100.0
                nb_bricks = (128 - len(event.message))
                panel.add_log_block(len(event.message) + 4,
                                    self.event_progbar_y,
                                    "∎" * nb_bricks,
                                    self.cl_alt_text)
                self.event_progbar_y = 0
                self.event_progbar_title = ""
                self.event_progbar_value = 0.0

        elif event.type == "extract":
            source_file_path = event.message
            query = event.text_var
            extract = event.message_end
            score = event.value
            i = event.int_a
            first_index = event.int_b
            last_index = event.int_c
            extract_lines = utils.split_words(extract, 126)
            frame_height = len(extract_lines) + 2
            max_line_len = max(
                (len(line) for line in extract_lines),
                default=0,
                ) + 4
            y = panel.next_empty_log_line()
            panel.add_log_block(2, y, "Result ", self.cl_text)
            i_txt = f"{i:02}"
            panel.add_log_block(9, y, i_txt, self.cl_alt_text)
            panel.add_log_block(9 + len(i_txt), y, " - Score ", self.cl_text)
            panel.add_log_block(18 + len(i_txt), y, f"{score:.2f}",
                                self.cl_alt_text)
            panel.add_log_block(2, y + 1, "Found in ", self.cl_text)
            panel.add_log_block(11, y + 1, source_file_path, self.cl_alt_text)
            x = 11 + len(source_file_path)
            panel.add_log_block(x, y + 1, " (", self.cl_log_item)
            panel.add_log_block(x + 2, y + 1, f"{first_index}",
                                self.cl_dim_text)
            x += 2 + len(f"{first_index}")
            panel.add_log_block(x, y + 1, " to ", self.cl_log_item)
            panel.add_log_block(x + 4, y + 1, f"{last_index}",
                                self.cl_dim_text)
            x += 4 + len(f"{last_index}")
            panel.add_log_block(x, y + 1, ")", self.cl_log_item)
            y += 2
            x = 2
            extract_box = ("╭" + "─" * (max_line_len - 2) + "╮\n"
                           + ("│" + " " * (max_line_len - 2) + "│\n")
                           * (frame_height - 2)
                           + "╰" + "─" * (max_line_len - 2) + "╯")
            panel.add_log_block(x, y, extract_box, self.cl_log_item)
            x += 2
            y += 1
            panel.add_log_block(x, y, "\n".join(extract_lines),
                                self.cl_text)
            if query:
                pattern = re.compile(
                    rf"(?<!\w){re.escape(query)}(?!\w)",
                    re.IGNORECASE,
                    )
                for line_index, line in enumerate(extract_lines):
                    for match in pattern.finditer(line):
                        panel.add_log_block(x + match.start(), y + line_index,
                                            match.group(0),
                                            self.cl_alt_inv_text)
            panel.add_empty_log_line(1)

        elif event.type == "json":
            def natural_key(key: str) -> str:
                """ Convert a snake_case key into a human-readable label. """
                return key.replace("_", " ").capitalize()

            def format_source(source: dict[str, Any]) -> tuple[str, str, str]:
                """
                Extract the displayable fields from one retrieved source.
                """
                file_path = str(source.get("file_path", ""))
                first_index = str(source.get("first_character_index", ""))
                last_index = str(source.get("last_character_index", ""))
                return file_path, first_index, last_index

            try:
                data = json.loads(event.message)
            except json.JSONDecodeError:
                y = panel.next_empty_log_line()
                panel.add_log_block(2, y, event.message, self.cl_log_item)
                panel.add_empty_log_line(1)
                return

            DisplayValue = str | tuple[str, str, str]
            lines: list[tuple[int, str, DisplayValue, bool]] = []
            search_results = data.get("search_results", [])
            if search_results:
                lines.append((0, "Search results", "", False))
                for result in search_results:
                    question_id = result.get("question_id", "")
                    question = result.get("question", "")
                    sources = result.get("retrieved_sources", [])
                    answer = result.get("answer", "")
                    lines.append((1, f"{natural_key('question_id')}: ",
                                  str(question_id), False))
                    lines.append((1, f"{natural_key('question')}: ",
                                  str(question), False))
                    lines.append((1, f"{natural_key('retrieved_sources')}:",
                                  "", False))
                    for source in sources:
                        file_path, source_first_index, source_last_index = (
                            format_source(source)
                            )
                        lines.append((2, f"{natural_key('file_path')}: ",
                                      (file_path, source_first_index,
                                       source_last_index),
                                      False))
                    lines.append((1, f"{natural_key('answer')}: ",
                                  str(answer), True))
            if "k" in data:
                lines.append((1, f"{natural_key('k')}: ",
                              str(data["k"]), False))

            def has_next_sibling(line_index: int, level: int) -> bool:
                """
                Return whether another node exists at the same tree level.
                """
                for next_line in lines[line_index + 1:]:
                    next_indent = next_line[0]
                    if next_indent < level:
                        return False
                    if next_indent == level:
                        return True
                return False

            def tree_column(level: int) -> int:
                """
                Return the canvas column corresponding to one tree depth.
                """
                return base_offset + (level - 1) * indent_size + 1

            def draw_tree(line_index: int, indent: int, y_pos: int) -> None:
                """
                Draw the tree branches for one structured output line.
                """
                if indent <= 0:
                    return
                for level in range(1, indent):
                    if has_next_sibling(line_index, level):
                        panel.add_log_block(tree_column(level), y_pos,
                                            "│", self.cl_log_item)
                branch_x = tree_column(indent)
                label_x = base_offset + indent * indent_size
                if has_next_sibling(line_index, indent):
                    branch_char = "├"
                else:
                    branch_char = "╰"
                arrow_x = label_x - 2
                horizontal_size = max(0, arrow_x - branch_x - 1)
                branch = branch_char + "─" * horizontal_size + "⊳"
                panel.add_log_block(branch_x, y_pos, branch, self.cl_log_item)

            def draw_tree_continuation(line_index: int, indent: int,
                                       y_pos: int,) -> None:
                """
                Draw the vertical tree branches beside a wrapped value line.
                """
                if indent <= 0:
                    return
                for level in range(1, indent + 1):
                    if has_next_sibling(line_index, level):
                        panel.add_log_block(tree_column(level), y_pos,
                                            "│", self.cl_log_item)

            y = panel.next_empty_log_line()
            base_offset = 2
            indent_size = 6
            right_margin = 2
            for line_index, line_parts in enumerate(lines):
                indent, label, value, wrap_value = line_parts
                label_x = base_offset + indent * indent_size
                draw_tree(line_index, indent, y)
                panel.add_log_block(label_x, y, label, self.cl_dim_text)
                if not value:
                    y += 1
                    continue
                value_x = label_x + len(label)
                if isinstance(value, tuple):
                    source_path_value = value[0]
                    source_first_value = value[1]
                    source_last_value = value[2]
                    current_x = value_x
                    panel.add_log_block(current_x, y, source_path_value,
                                        self.cl_dim_alt_text)
                    current_x += len(source_path_value)
                    panel.add_log_block(current_x, y, " (",
                                        self.cl_dim_text)
                    current_x += 2
                    panel.add_log_block(current_x, y, source_first_value,
                                        self.cl_dim_alt_text)
                    current_x += len(source_first_value)
                    panel.add_log_block(current_x, y, " to ",
                                        self.cl_dim_text)
                    current_x += 4
                    panel.add_log_block(current_x, y, source_last_value,
                                        self.cl_dim_alt_text)
                    current_x += len(source_last_value)
                    panel.add_log_block(current_x, y, ")",
                                        self.cl_dim_text)
                    y += 1
                elif wrap_value:
                    available_width = panel.width - value_x - right_margin - 2
                    value_lines = utils.split_words(value, available_width)
                    for value_line_index, value_line in enumerate(value_lines):
                        if value_line_index > 0:
                            draw_tree_continuation(line_index=line_index,
                                                   indent=indent, y_pos=y)
                        panel.add_log_block(value_x, y, value_line,
                                            self.cl_dim_alt_text)
                        y += 1
                else:
                    panel.add_log_block(value_x, y, value,
                                        self.cl_dim_alt_text)
                    y += 1
            panel.add_empty_log_line(1)

        elif event.type == "noanswer":
            top_score = event.float_a
            avg_score = event.float_b
            dominance_ratio = event.float_c
            y = panel.next_empty_log_line()
            x = 2
            noanswer_box = ("╭" + "─" * 44 + "╮\n"
                            + ("│" + " " * 44 + "│\n") * 5
                            + "╰" + "─" * 44 + "╯")
            panel.add_log_block(x, y, noanswer_box, self.cl_log_item)
            x += 2
            y += 1
            noanswer_text = ("No relevant informations found,\n"
                             + "can't answer efficiently on this question.\n"
                             + "Top score:       \n"
                             + "Average score:   \n"
                             + "Dominance ratio: ")
            panel.add_log_block(x, y, noanswer_text, self.cl_text)
            x += 17
            panel.add_log_block(x, y + 2, f"{top_score:.2f}",
                                self.cl_alt_text)
            panel.add_log_block(x, y + 3, f"{avg_score:.2f}",
                                self.cl_alt_text)
            panel.add_log_block(x, y + 4, f"{dominance_ratio:.2f}",
                                self.cl_alt_text)
            panel.add_empty_log_line(1)

        elif event.type == "files_analysis_sheet":
            left_col: list[str] = []
            right_col: list[str] = []
            left_txt: str = ""
            right_txt: str = ""
            for i in range(len(event.fields)):
                if i % 2 == 0:
                    left_col.append(event.fields[i])
                elif i % 2 == 1:
                    right_col.append(event.fields[i])
            left_width = 2
            for item in left_col:
                left_width = max(left_width, len(item) + 2)
                left_txt += item + "\n"
            right_width = 2
            for item in right_col:
                right_width = max(right_width, len(item) + 2)
            for item in right_col:
                right_txt += f"{item:>{right_width - 2}}" + "\n"
            sheet_box = ("╭" + "─" * left_width + "┬"
                         + "─" * right_width + "╮\n"
                         + ("│" + " " * left_width + "│" + " " * right_width
                            + "│\n") * len(left_col)
                         + "╰" + "─" * left_width + "┴"
                         + "─" * right_width + "╯")
            y, x = panel.next_empty_log_line(), 2
            panel.add_log_block(x, y, sheet_box, self.cl_log_item)
            panel.add_log_block(x + 3, y + 4, "├──⊳\n╰──⊳", self.cl_log_item)
            panel.add_log_block(x + 2, y, event.message.upper(),
                                self.cl_log_item, transparent=True)
            y, x = y + 1, x + 2
            panel.add_log_block(x, y, left_txt, self.cl_text, transparent=True)
            panel.add_log_block(x + left_width + 1, y, right_txt,
                                self.cl_alt_text)
            panel.add_empty_log_line(1)

        elif event.type == "bubbles":
            question_id = event.message
            question = event.left_box
            answer = event.right_box
            duration = event.duration
            nb_items = event.int_a
            count_items = event.int_b
            question_lines = utils.split_words(question, 86)
            answer_lines = utils.split_words(answer, 86)
            left_bubble_height = len(question_lines) + 3
            right_bubble_height = len(answer_lines) + 3
            bubbles_height = left_bubble_height + right_bubble_height + 1
            y = panel.next_empty_log_line()
            if self.event_progbar_title != "":
                y -= 1
                panel.add_log_block(2, y, " " * 130, self.cl_text)
                self.event_progbar_y += bubbles_height
                panel.add_log_block(2, self.event_progbar_y,
                                    f"{self.event_progbar_title}:",
                                    self.cl_text)
            question_box = "◢" + "█" * 88 + "◣\n"
            question_block = ""
            for question_line in question_lines:
                question_box += ("█" + " " * 88 + "█\n")
                question_block += f"{question_line:^88}" + "\n"
            question_box += ("█" + "█" * 88 + "◤\n█◤\n◤")
            panel.add_log_block(2, y, question_box, self.cl_text)
            question_block = question_block.replace(" ", f"{NBSP}")
            panel.add_log_block(3, y + 1, question_block, self.cl_inv_text)
            answer_box = ("◢" + "█" * 88 + "◣\n")
            answer_block = ""
            for answer_line in answer_lines:
                answer_box += ("█" + " " * 88 + "█\n")
                answer_block += f"{answer_line:^88}" + "\n"
            answer_box += ("◥" + "█" * 88 + "█\n"
                           + " " * 88 + "◥█\n" + " " * 89 + "◥")
            panel.add_log_block(42, y + left_bubble_height,
                                answer_box, self.cl_alt_text)
            answer_block = answer_block.replace(" ", f"{NBSP}")
            panel.add_log_block(43, y + left_bubble_height + 1,
                                answer_block, self.cl_alt_inv_text)
            if (count_items != 0 and nb_items != 0
               and question_id != "unique question"):
                txt = (f"{question_id} ({count_items:03}/{nb_items:03}) "
                       + f"generated in {duration:.2f}s")
            else:
                txt = (f"generated in {duration:.2f}s")
            panel.add_log_block(129 - len(txt), y + bubbles_height - 2,
                                txt, self.cl_log_item)

        elif event.type == "finish":
            y = panel.next_empty_log_line()
            panel.add_separator_line(y + 1, self.cl_log_item)
            txt = event.message + f"({event.duration:.2f}s) "
            msg_len = len(txt)
            offset = (130 - msg_len) // 2 + 2
            msg_box = ("╭" + "─" * msg_len + "╮\n╡" + " " * msg_len
                       + "╞\n╰" + "─" * msg_len + "╯")
            panel.add_log_block(offset, y, msg_box, self.cl_log_item)
            panel.add_log_block(offset + 1, y + 1, txt, self.cl_dim_text)
            panel.add_log_block(offset + 1 + len(event.message), y + 1,
                                f"({event.duration:.2f}s) ",
                                self.cl_log_item)
            panel.add_log_block(offset + 1 + len(event.message) + 1, y + 1,
                                f"{event.duration:.2f}s",
                                self.cl_dim_alt_text)
            panel.add_empty_log_line(1)

        panel.display_logbook()
        panel.scroll_bar()
        self.canvas.print_canvas()

    def call_evaluate(self) -> None:
        """
        Update the evaluation summary displayed at the bottom of the interface.
        """
        for y in range(self.y_end - 1, self.y_end + 1):
            for x in range(self.x_start, self.x_start + 59):
                self.canvas.restore_cell(x, y)
            for x in range(self.x_start + 77, self.x_end + 1):
                self.canvas.restore_cell(x, y)

        color = self.cl_labels
        if self.k <= 0:
            color = self.colors.BASE_RED
        txt = f"{self.k}"
        self.canvas.add_block(self.x_start + 132, self.y_end - 1, txt, color,
                              transparent=True)

        evaluate = self.cli.evaluate(
            student_search_results_path=self.search_result_path,
            dataset_path=self.dataset_answered,
            k=self.k,
            basic_print=False,
            tui_display=True
            )

        if evaluate is not None and evaluate.student_valid:
            self.canvas.add_block(self.x_start, self.y_end - 1,
                                  "   Valid\n    data", self.cl_text,
                                  transparent=True)
        else:
            self.canvas.add_block(self.x_start, self.y_end - 1,
                                  "  Invalid\n    data", self.colors.BASE_RED,
                                  transparent=True)

        if evaluate is not None:
            color = self.cl_text
            if evaluate.total_questions <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.total_questions:^15}"
            self.canvas.add_block(self.x_start + 12, self.y_end, txt, color,
                                  transparent=True)
            color = self.cl_text
            if evaluate.questions_with_sources <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.questions_with_sources:^15}"
            self.canvas.add_block(self.x_start + 28, self.y_end, txt, color,
                                  transparent=True)
            color = self.cl_text
            if evaluate.questions_with_student_sources <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.questions_with_student_sources:^15}"
            self.canvas.add_block(self.x_start + 44, self.y_end, txt, color,
                                  transparent=True)

        else:
            self.canvas.add_block(self.x_start + 18, self.y_end, "N/A",
                                  self.cl_text, transparent=True)
            self.canvas.add_block(self.x_start + 34, self.y_end, "N/A",
                                  self.cl_text, transparent=True)
            self.canvas.add_block(self.x_start + 50, self.y_end, "N/A",
                                  self.cl_text, transparent=True)

        if evaluate is None or evaluate.recall1 is None:
            self.canvas.add_block(self.x_start + 83, self.y_end, "N/A",
                                  self.cl_text, transparent=True)
        else:
            color = self.cl_text
            if evaluate.recall1 <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.recall1:^14.2f}"
            self.canvas.add_block(self.x_start + 77, self.y_end, txt, color,
                                  transparent=True)

        if evaluate is None or evaluate.recall3 is None:
            self.canvas.add_block(self.x_start + 98, self.y_end, "N/A",
                                  self.cl_text, transparent=True)
        else:
            color = self.cl_text
            if evaluate.recall3 <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.recall3:^14.2f}"
            self.canvas.add_block(self.x_start + 92, self.y_end, txt, color,
                                  transparent=True)

        if evaluate is None or evaluate.recall5 is None:
            self.canvas.add_block(self.x_start + 113, self.y_end, "N/A",
                                  self.cl_text, transparent=True)
        else:
            color = self.cl_text
            if evaluate.recall5 <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.recall5:^14.2f}"
            self.canvas.add_block(self.x_start + 107, self.y_end, txt, color,
                                  transparent=True)

        if evaluate is None or evaluate.recallk is None:
            self.canvas.add_block(self.x_start + 128, self.y_end, "N/A",
                                  self.cl_text, transparent=True)
        else:
            color = self.cl_text
            if evaluate.recallk <= 0:
                color = self.colors.BASE_RED
            txt = f"{evaluate.recallk:^14.2f}"
            self.canvas.add_block(self.x_start + 122, self.y_end, txt, color,
                                  transparent=True)

        self.canvas.print_canvas()

    def open_ribbon_thumb(self) -> None:
        """ Display the currently selected ribbon tab. """
        for x in range(self.x_start, self.x_end + 1):
            for y in range(2):
                cell = self.canvas._grid[self.y_start + y][x]
                if cell.ch.isalnum() or cell.ch in "_-<>":
                    cell.color = self.cl_labels
                elif cell.ch in "║│":
                    cell.color = self.cl_frame
                else:
                    cell.color = self.cl_main_background
        left_arrow_color: str = self.cl_labels
        if self.active_ribbon_thumb <= 1:
            left_arrow_color = self.cl_dim_labels
        right_arrow_color: str = self.cl_labels
        if self.active_ribbon_thumb >= 7:
            right_arrow_color = self.cl_dim_labels
        self.canvas.color_canvas_block(self.x_start, self.y_start,
                                       self.x_start, self.y_start + 1,
                                       left_arrow_color)
        self.canvas.color_canvas_block(self.x_end, self.y_start,
                                       self.x_end, self.y_start + 1,
                                       right_arrow_color)
        for x in range(self.x_start, self.x_end + 1):
            self.canvas.set_canvas_cell(x, self.y_start + 2,
                                        "─", self.cl_frame)
        for x in range(self.x_start + 1, self.x_end, 19):
            self.canvas.set_canvas_cell(x, self.y_start + 2,
                                        "┴", self.cl_frame)
        x_offset = (self.active_ribbon_thumb - 1) * 19 + self.x_start + 1
        self.canvas.set_canvas_cell(x_offset, self.y_start + 2,
                                    "╯", self.cl_frame)
        self.canvas.set_canvas_cell(x_offset + 19, self.y_start + 2,
                                    "╰", self.cl_frame)
        for i in range(18):
            self.canvas.restore_cell(x_offset + i + 1, self.y_start + 2)
            for y in range(2):
                cell = self.canvas._grid[self.y_start + y][x_offset + i + 1]
                if cell.ch.isalnum() or cell.ch in "_-<>":
                    cell.color = self.cl_highlight_text
                else:
                    cell.color = self.cl_log_background
        for y in range(self.y_start + 3, self.y_end - 2):
            for x in range(self.x_start, self.x_end + 1):
                self.canvas.restore_cell(x, y)
        for x in range(self.x_start + 60, self.x_start + 77):
            for y in range(2):
                self.canvas.restore_cell(x, self.y_end - y)

        if self.active_ribbon_thumb == 1:
            self.canvas.set_canvas_cell(self.x_end - 1, self.y_start + 2,
                                        "┴", self.cl_frame)
        elif self.active_ribbon_thumb == 7:
            self.canvas.set_canvas_cell(self.x_end - 1, self.y_start + 2,
                                        "╰", self.cl_frame)
        if self.active_ribbon_thumb == 1 or self.active_ribbon_thumb == 7:
            self.canvas.set_canvas_cell(self.x_end - 1, self.y_end - 2,
                                        "═", self.cl_frame)
        else:
            self.canvas.set_canvas_cell(self.x_end - 1, self.y_start + 2,
                                        "┼", self.cl_frame)
            self.canvas.set_canvas_cell(self.x_end - 1, self.y_end - 2,
                                        "╧", self.cl_frame)
            self.canvas.color_canvas_block(self.x_end - 1, self.y_start + 3,
                                           self.x_end, self.y_end - 3,
                                           self.cl_main_background)
            for y in range(self.y_start + 3, self.y_end - 2):
                self.canvas.set_canvas_cell(self.x_end - 1, y,
                                            "│", self.cl_frame)

        if self.active_ribbon_thumb == 1:
            self.place_button(self.x_start + 61, self.y_end - 1, 14,
                              "CLEAR DATA", "⊲━━┛", True)
        elif self.active_ribbon_thumb == 2:
            self.place_button(self.x_start + 61, self.y_end - 1, 14,
                              "MAKE INDEX", "⊲━━┛", True)
        elif self.active_ribbon_thumb == 3:
            self.place_button(self.x_start + 61, self.y_end - 1, 14,
                              "SEARCH KEY", "⊲━━┛", True)
        elif self.active_ribbon_thumb == 4:
            self.place_button(self.x_start + 61, self.y_end - 1, 14,
                              "SEARCH SET", "⊲━━┛", True)
        elif self.active_ribbon_thumb == 5:
            self.place_button(self.x_start + 61, self.y_end - 1, 14,
                              "ANSWER QUERY", "⊲━━┛", True)
        elif self.active_ribbon_thumb == 6:
            self.place_button(self.x_start + 61, self.y_end - 1, 14,
                              "ANSWER SET", "⊲━━┛", True)
        elif self.active_ribbon_thumb == 7:
            self.place_button(self.x_start + 61, self.y_end - 1, 7,
                              "RESET", "=", self.settings_default_button,
                              cut_right=True)
            self.place_button(self.x_start + 68, self.y_end - 1, 6,
                              "APPLY", " F12 ", self.settings_save_button,
                              cut_left=True)

        if 1 <= self.active_ribbon_thumb <= 7:
            current_logbook = self.logbooks.get(self.active_ribbon_thumb)
            if current_logbook is not None:
                current_logbook.display_logbook()
            if 2 <= self.active_ribbon_thumb <= 6:
                if current_logbook is not None:
                    current_logbook.scroll_bar()

        self.canvas.print_canvas()

    def place_button(self, x: int, y: int, width: int,
                     line1: str, line2: str, active: bool,
                     cut_left: bool = False, cut_right: bool = False) -> None:
        """ Draw a two-line action button. """
        color = self.cl_disabled_button
        if active:
            color = self.cl_button
        top_l = "▌" if cut_left else "◤"
        bot_l = "▌" if cut_left else "◣"
        top_r = "▐" if cut_right else "◥"
        bot_r = "▐" if cut_right else "◢"
        txt = (top_l + f"{line1:^{width - 2}}" + top_r + "\n"
               + bot_l + f"{line2:^{width - 2}}" + bot_r)
        self.canvas.add_block(x, y, txt, color, transparent=False)

    def build(self) -> None:
        """ Build the complete terminal interface. """
        trans_steps = 28
        self.build_base_by_size(78, 23)
        time.sleep(self.base_wait * 50)
        for i in range(trans_steps):
            trans_width = int(((139 - 78) / trans_steps) * (i + 1) + 78)
            trans_height = int(((44 - 23) / trans_steps) * (i + 1) + 23)
            self.build_base_by_size(trans_width, trans_height)
            time.sleep(self.base_wait * 20)
        self.build_base_by_size(self.width, self.height)

        self.canvas.set_canvas_cell(self.x_start - 1, self.y_end - 2,
                                    "╠", self.cl_frame)
        self.canvas.set_canvas_cell(self.x_end + 1, self.y_end - 2,
                                    "╣", self.cl_frame)
        for x in range(self.x_start, self.x_start + 59):
            self.canvas.set_canvas_cell(x, self.y_end - 2,
                                        "═", self.cl_frame)
        for x in range(self.x_start + 77, self.x_end + 1):
            self.canvas.set_canvas_cell(x, self.y_end - 2,
                                        "═", self.cl_frame)
        self.canvas.set_canvas_cell(self.x_start + 59, self.y_end - 2,
                                    "╗", self.cl_frame)
        self.canvas.set_canvas_cell(self.x_start + 76, self.y_end - 2,
                                    "╔", self.cl_frame)
        self.canvas.add_block(self.x_start, self.y_end - 1,
                              Panels.BOT_EVAL, self.cl_labels,
                              transparent=True)
        for x in range(self.x_start + 11, self.x_end // 2 - 8, 16):
            self.canvas.set_canvas_cell(x, self.y_end - 2,
                                        "╤", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end - 1,
                                        "│", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end,
                                        "│", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end + 1,
                                        "╧", self.cl_frame)
        for x in range(self.x_end - 14, self.x_end // 2 + 15, -15):
            self.canvas.set_canvas_cell(x, self.y_end - 2,
                                        "╤", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end - 1,
                                        "│", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end,
                                        "│", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end + 1,
                                        "╧", self.cl_frame)
        for x in range(self.x_start + 59, self.x_start + 77, 17):
            self.canvas.set_canvas_cell(x, self.y_end - 1,
                                        "║", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end,
                                        "║", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_end + 1,
                                        "╩", self.cl_frame)

        self.canvas.set_canvas_cell(self.x_start - 1, self.y_start + 2,
                                    "╟", self.cl_frame)
        self.canvas.set_canvas_cell(self.x_end + 1, self.y_start + 2,
                                    "╢", self.cl_frame)

        self.canvas.add_block(self.x_start, self.y_start,
                              Panels.TOP_RIBBON, self.cl_labels,
                              transparent=True)
        self.canvas.color_canvas_block(self.x_start, self.y_start,
                                       self.x_end, self.y_end - 3,
                                       self.cl_log_background)
        self.canvas.color_canvas_block(self.x_start + 60, self.y_end - 2,
                                       self.x_start + 75, self.y_end,
                                       self.cl_log_background)

        self.canvas.store_canvas()

        for x in range(self.x_start, self.x_end + 1):
            self.canvas.set_canvas_cell(x, self.y_start + 2,
                                        "─", self.cl_frame)
        for x in range(self.x_start + 1, self.x_end, 19):
            self.canvas.set_canvas_cell(x, self.y_start - 1,
                                        "╤", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_start,
                                        "│", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_start + 1,
                                        "│", self.cl_frame)
            self.canvas.set_canvas_cell(x, self.y_start + 2,
                                        "┴", self.cl_frame)

        self.canvas.print_canvas()

    def build_base_by_size(self, width: int, height: int) -> None:
        """
        Build the interface frame during the launcher transition animation.
        """
        self.canvas.clear_canvas()
        self.canvas.deco_zone(-2, 0, width - 1, height - 1,
                              Elements.DECO_FILL, self.cl_main_background)
        for y in range(height):
            self.canvas.add_block(0, y, " ", self.cl_frame)
        self.canvas.color_canvas_block(2, 1, width - 2, 7,
                                       self.colors.DEEP_PURPLE)
        for x in range(width):
            if x > 0:
                self.canvas.set_canvas_cell(x, 0, "═", self.cl_frame)
                self.canvas.set_canvas_cell(x, 8, "═", self.cl_frame)
                self.canvas.set_canvas_cell(x, height - 1, "═",
                                            self.cl_frame)
        for y in range(height):
            self.canvas.set_canvas_cell(1, y, "║", self.cl_frame)
            self.canvas.set_canvas_cell(width - 1, y, "║", self.cl_frame)
        self.canvas.set_canvas_cell(1, 0, "╔", self.cl_frame)
        self.canvas.set_canvas_cell(width - 1, 0, "╗", self.cl_frame)
        self.canvas.set_canvas_cell(1, height - 1, "╚", self.cl_frame)
        self.canvas.set_canvas_cell(width - 1, height - 1,
                                    "╝", self.cl_frame)
        self.canvas.set_canvas_cell(1, 8, "╠", self.cl_frame)
        self.canvas.set_canvas_cell(width - 1, 8, "╣", self.cl_frame)
        self.canvas.add_block(2, 1, Banners.LEFT_BANNER,
                              self.colors.BLUE42, transparent=True)
        self.canvas.add_block(width - 8, 1, Banners.RIGHT_BANNER,
                              self.colors.BLUE42, transparent=True)

        x, _ = self.canvas.center_block(Banners.SIGNATURE_BANNER,
                                        x_start=8, x_end=width - 7)
        self.canvas.add_block(x, 7, Banners.SIGNATURE_BANNER,
                              self.cl_frame, transparent=True)
        for i in range(len(Banners.SIGNATURE_COLORS)):
            if Banners.SIGNATURE_COLORS[i] != "0":
                if Banners.SIGNATURE_COLORS[i] == "3":
                    color = f"\33[3{Banners.SIGNATURE_COLORS[i]}m"
                else:
                    color = f"\33[9{Banners.SIGNATURE_COLORS[i]}m"
                self.canvas.color_canvas_cell(x + i, 7, color)

        if width >= 139:
            x, _ = self.canvas.center_block(Banners.CENTER_BANNER,
                                            x_start=8, x_end=width - 7)
            self.canvas.add_block(x, 1, Banners.CENTER_BANNER,
                                  self.colors.BASE_BR_PURPLE, transparent=True)
            x, y = x + 93, 6
            self.canvas.add_block(x, y, Banners.EDITION_BANNER_A,
                                  self.colors.BASE_WHITE, transparent=True)
            for i in range(len(Banners.EDITION_COLORS_A)):
                if Banners.EDITION_COLORS_A[i] != "0":
                    color = f"\33[0;3m\33[9{Banners.EDITION_COLORS_A[i]}m"
                    self.canvas.color_canvas_cell(x + i, y, color)

        self.canvas.print_canvas()
