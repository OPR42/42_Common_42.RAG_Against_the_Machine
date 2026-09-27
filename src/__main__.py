import sys

import fire

from src.command.cli import CLI
from src.interface.colors import Colors as colors


def draw_banner() -> None:
    """ Display the application startup banner. """
    print("\33[2J\33[48;2;0;0;0m\33[37m\33[0m")
    print("\33[H")
    print(f"{colors.BASE_BROWN} ╔" + "═" * 136 + "╗")
    print(f"{colors.BASE_BROWN} ║{colors.BLUE42}  ◢◤ ◤█"
          f"{colors.BASE_BR_PURPLE}       ▁▁▁▁  ▁▁▁   ▁▁▁▁▁▁   ▁▁▁            "
          "   ▁▁           ▁▁     ▁▁  ▁▁            ▁▁  ▁▁▁           ▁▁    ▁▁"
          f"            {colors.BLUE42}█◥ ◥◣  {colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ║{colors.BLUE42} ◢◤  ◢◤"
          f"{colors.BASE_BR_PURPLE}      ╱ ▁▁ ╲╱   │ ╱ ▁▁▁▁╱  ╱   │ ▁▁▁▁▁▁▁▁▁▁"
          "▁▁╱▁╱▁▁▁  ▁▁▁▁▁╱ ╱▁   ╱ ╱▁╱ ╱▁  ▁▁▁     ╱  │╱  ╱▁▁▁▁▁▁▁▁▁▁╱ ╱▁  ╱▁╱"
          f"▁▁▁  ▁▁▁    {colors.BLUE42}◥◣  ◥◣ {colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ║{colors.BLUE42} ███ █◢"
          f"{colors.BASE_BR_PURPLE}     ╱ ╱▁╱ ╱ ╱│ │╱ ╱ ▁▁   ╱ ╱│ │╱ ▁▁  ╱ ▁▁ "
          " ╱ ╱ ▁▁ ╲╱ ▁▁▁╱ ▁▁╱  ╱ ▁▁╱ ▁▁ ╲╱ ▁ ╲   ╱ ╱│▁╱ ╱ ▁▁  ╱ ▁▁▁╱ ▁▁ ╲╱ ╱ "
          f"▁▁ ╲╱ ▁ ╲   {colors.BLUE42}◣█ ███ {colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ║{colors.BLUE42}   █   "
          f"{colors.BASE_BR_PURPLE}    ╱ ▁  ▁╱ ▁▁▁ ╱ ╱▁╱ ╱  ╱ ▁▁▁ ╱ ╱▁╱ ╱ ╱▁╱ "
          "╱ ╱ ╱ ╱ ╱▁▁  ╱ ╱▁   ╱ ╱▁╱ ╱ ╱ ╱  ▁▁╱  ╱ ╱  ╱ ╱ ╱▁╱ ╱ ╱▁▁╱ ╱ ╱ ╱ ╱ ╱"
          f" ╱ ╱  ▁▁╱   {colors.BLUE42}   █   {colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ║{colors.BLUE42}  2026 "
          f"{colors.BASE_BR_PURPLE}   ╱▁╱ │▁╱▁╱  │▁╲▁▁▁▁╱  ╱▁╱  │▁╲▁▁  ╱╲▁▁▁▁╱"
          "▁╱▁╱ ╱▁╱▁▁▁▁╱╲▁▁╱   ╲▁▁╱▁╱ ╱▁╱╲▁▁▁╱  ╱▁╱  ╱▁╱╲▁▁▁▁╱╲▁▁▁╱▁╱ ╱▁╱▁╱▁╱ "
          f"╱▁╱╲▁▁▁╱    {colors.BLUE42} 2026  {colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ║" + " " * 37 +
          f"{colors.BASE_BR_PURPLE}╱▁▁▁▁╱" + " " * 93 +
          f"{colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ║{colors.BLUE42}  OPR" + " " * 53 +
          f"{colors.BASE_BR_CYAN}42 {colors.BASE_BROWN}- "
          f"{colors.BASE_BR_PURPLE}orobert {colors.BASE_BROWN}- "
          f"{colors.BASE_BR_CYAN}2026" + " " * 54 +
          f"{colors.BLUE42}OPR  {colors.BASE_BROWN}║")
    print(f"{colors.BASE_BROWN} ╚" + "═" * 136 + "╝")
    print(f"{colors.RESET}")


def main() -> None:
    """ Launch the command-line interface. """
    if len(sys.argv) > 1 and sys.argv[1] != "interface":
        draw_banner()
    fire.Fire(CLI)
    print()


if __name__ == "__main__":
    main()
