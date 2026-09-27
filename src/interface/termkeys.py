import atexit
import os
import select
import signal
import sys
import termios
import time
import tty
from typing import Any

from .interface import Interface as Core

# ANSI escape codes
CURSOR_SHOW = "\33[?25h"
COLOR_RESET = "\33[48;2;0;0;0m\33[37m"
RESET_FORMATTING = "\33[0m"


KEYMAP = {
    "\x1bOP": "f1",
    "\x1bOQ": "f2",
    "\x1bOR": "f3",
    "\x1bOS": "f4",
    "\x1b[15~": "f5",
    "\x1b[17~": "f6",
    "\x1b[18~": "f7",
    "\x1b[24~": "f12",
    "\x1b[A": "up", "\x1bOA": "up",
    "Z": "up", "z": "up", "W": "up", "w": "up",
    "\x1b[H": "top", "\x1bOH": "top",
    "\x1b[B": "down", "\x1bOB": "down",
    "S": "down", "s": "down",
    "\x1b[F": "bottom", "\x1bOF": "bottom",
    "\x1b[5~": "pgup", "\x1b[6~": "pgdown",
    "\x1b[C": "right", "\x1bOC": "right",
    "D": "right", "d": "right",
    "\x1b[D": "left", "\x1bOD": "left",
    "Q": "left", "q": "left", "A": "left", "a": "left",
    " ": "space",
    "\n": "enter", "\r": "enter",
    "\x1b[3~": "delete", "\x7f": "backspace",
    "/": "/", "*": "*", "+": "+", "-": "-", "=": "=",
    "\x1b": "esc",
}

INPUT_KEYMAP = {
    "\x1b[D": "left", "\x1bOD": "left",
    "\x1b[C": "right", "\x1bOC": "right",
    "\x1b[H": "home", "\x1bOH": "home",
    "\x1b[F": "end", "\x1bOF": "end",
    "\x1b[3~": "delete", "\x7f": "backspace",
    "\n": "enter", "\r": "enter",
    "\t": "tab", "\x1b[Z": "backtab",
    "\x1b": "esc",
}


class KeyControlError(Exception):
    """ Raised when terminal or keyboard handling fails. """
    pass


class TerminalManager:
    """ Manage the terminal state during program execution. """
    def __init__(self, core: Core) -> None:
        """ Initialize the terminal manager and register cleanup handlers. """
        self.core = core
        self.fd: int | None = None
        self.old: list[Any] | None = None
        atexit.register(self.cleanup)

    def setup(self) -> None:
        """ Configure the terminal for immediate keyboard input. """
        try:
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        except (termios.error, OSError) as e:
            raise KeyControlError(f"Unable to configure terminal: {e}") from e

    def restore(self) -> None:
        """ Restore the terminal to its previous state. """
        if self.fd is None or self.old is None:
            raise KeyControlError("Invalid terminal state")
        try:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        except termios.error as e:
            raise KeyControlError(
                f"Error during terminal restoration: {e}"
            ) from e

    def cleanup(self) -> None:
        """ Restore the terminal and reset its display attributes. """
        try:
            if self.old is not None and self.fd is not None:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        except (termios.error, OSError):
            os.system("stty sane")
        if self.core.active_ui:
            sys.stdout.write(f"{CURSOR_SHOW}{COLOR_RESET}{RESET_FORMATTING}\n")
            sys.stdout.flush()
        else:
            sys.stderr.write(f"{CURSOR_SHOW}{COLOR_RESET}{RESET_FORMATTING}\n")
            sys.stderr.flush()


class KeyControl:
    """ Handle keyboard input and translate it into interface actions. """
    def __init__(self, core: Core,
                 terminal_manager: TerminalManager) -> None:
        """ Initialize keyboard handling. """
        self.core = core
        self.terminal = terminal_manager
        self.enabled: bool = False
        self.input_mode: bool = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """ Register signal handlers for clean program termination. """
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, _signum: int, _frame: Any) -> None:
        """ Handle termination signals. """
        self.exit_program()

    def start(self) -> None:
        """ Enable keyboard handling. """
        if self.enabled:
            return
        self.terminal.setup()
        self.enabled = True

    def stop(self) -> None:
        """ Disable keyboard handling. """
        if not self.enabled:
            return
        self.terminal.restore()
        self.enabled = False

    def set_input_mode(self, enabled: bool) -> None:
        """ Enable or disable text input translation. """
        self.input_mode = enabled

    def exit_program(self, code: int = 0) -> None:
        """ Restore the terminal and terminate the program. """
        try:
            self.stop()
        finally:
            self.terminal.cleanup()
            os.system("stty sane")
            sys.exit(code)

    def __enter__(self) -> "KeyControl":
        """ Enable keyboard handling when entering the context. """
        self.start()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """ Restore the terminal when leaving the context. """
        try:
            self.stop()
        finally:
            self.terminal.cleanup()

    def poll(self) -> str | None:
        """
        Return the next raw key sequence if available.

        Read complete ANSI escape sequences to distinguish standalone Escape
        from special keys such as arrows or function keys.
        """
        if not self.enabled:
            raise KeyControlError("KeyControl is not enabled. Call start() "
                                  "first.")
        try:
            fd = sys.stdin.fileno()
            r, _, _ = select.select([fd], [], [], 0)
            if not r:
                return None
            data = os.read(fd, 1)
            if not data:
                return None
            key = data.decode(errors="ignore")
            if key != "\x1b":
                return key
            time.sleep(0.01)
            seq = key
            while True:
                r, _, _ = select.select([fd], [], [], 0)
                if not r:
                    break
                seq += os.read(fd, 1).decode(errors="ignore")
            return seq
        except (OSError, select.error) as e:
            raise KeyControlError(f"Error during read: {e}") from e

    def key_control(self) -> str | None:
        """ Translate raw keyboard input into interface commands. """
        key_poll = self.poll()
        if key_poll is None:
            return None

        if self.input_mode:
            if len(key_poll) == 1 and 32 <= ord(key_poll) <= 126:
                return key_poll
            return INPUT_KEYMAP.get(key_poll)

        key = KEYMAP.get(key_poll)
        if self.core.step >= 1:
            if (key == "left" or key == "right" or key == "up" or key == "down"
               or key == "top" or key == "bottom" or key == "pgup"
               or key == "pgdown" or key == "enter" or key == "delete"
               or key == "f1" or key == "f2" or key == "f3" or key == "f4"
               or key == "f5" or key == "f6" or key == "f7" or key == "f12"
               or key == "+" or key == "-" or key == "*" or key == "/"
               or key == "="):
                return key
            elif key == "space":
                return "enter"
            elif key == "backspace":
                return "delete"
        if key == "esc" and not self.input_mode:
            if self.core.active_ui:
                print(f"{CURSOR_SHOW}{COLOR_RESET}{RESET_FORMATTING}")
            self.exit_program()
        return None
