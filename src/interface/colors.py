import re

COLOR_RE = re.compile(r"\033\[(?:\d+;)*38;2;(\d+);(\d+);(\d+)m"
                      r"\033\[48;2;(\d+);(\d+);(\d+)m")


class Colors:
    """ Define ANSI color codes and provide RGB color operations. """
    BASE_BLACK = "\33[1;30m\33[48;2;0;0;0m"
    BASE_RED = "\33[1;31m\33[48;2;0;0;0m"
    BASE_GREEN = "\33[1;32m\33[48;2;0;0;0m"
    BASE_BROWN = "\33[1;33m\33[48;2;0;0;0m"
    BASE_BLUE = "\33[1;34m\33[48;2;0;0;0m"
    BASE_PURPLE = "\33[1;35m\33[48;2;0;0;0m"
    BASE_CYAN = "\33[1;36m\33[48;2;0;0;0m"
    BASE_WHITE = "\33[1;37m\33[48;2;0;0;0m"
    BASE_BR_BLACK = "\33[1;90m\33[48;2;0;0;0m"
    BASE_BR_RED = "\33[1;91m\33[48;2;0;0;0m"
    BASE_BR_GREEN = "\33[1;92m\33[48;2;0;0;0m"
    BASE_BR_BROWN = "\33[1;93m\33[48;2;0;0;0m"
    BASE_BR_BLUE = "\33[1;94m\33[48;2;0;0;0m"
    BASE_BR_PURPLE = "\33[1;95m\33[48;2;0;0;0m"
    BASE_BR_CYAN = "\33[1;96m\33[48;2;0;0;0m"
    BASE_BR_WHITE = "\33[1;97m\33[48;2;0;0;0m"
    BASE_IT_BR_BLACK = "\33[3;90m\33[48;2;0;0;0m"
    MEDIUM_RED = "\33[1;38;2;191;0;0m\33[48;2;0;0;0m"
    LIGHT_DEEP_RED = "\33[1;38;2;167;0;0m\33[48;2;0;0;0m"
    DEEP_RED = "\33[1;38;2;143;0;0m\33[48;2;0;0;0m"
    INV_RED = "\33[1;38;2;0;0;0m\33[48;2;255;0;0m"
    GREEN = "\33[1;38;2;0;255;0m\33[48;2;0;0;0m"
    MEDIUM_GREEN = "\33[1;38;2;0;127;0m\33[48;2;0;0;0m"
    MEDIUM_TEAL_GREEN = "\33[1;38;2;0;159;79m\33[48;2;0;0;0m"
    DIM_TEAL_GREEN = "\33[1;38;2;0;119;59m\33[48;2;0;0;0m"
    DEEP_TEAL_GREEN = "\33[1;38;2;0;79;39m\33[48;2;0;0;0m"
    INV_GREEN = "\33[1;38;2;0;0;0m\33[48;2;0;255;0m"
    DEEP_GREEN = "\33[1;38;2;0;63;0m\33[48;2;0;0;0m"
    DARK_GREEN = "\33[1;38;2;0;31;0m\33[48;2;0;0;0m"
    DARKER_GREEN = "\33[1;38;2;0;15;0m\33[48;2;0;0;0m"
    BROWN = "\33[1;38;2;162;115;76m\33[48;2;0;0;0m"
    INV_BROWN = "\33[1;38;2;0;0;0m\33[48;2;162;115;76m"
    YELLOW = "\33[1;38;2;255;255;0m\33[48;2;0;0;0m"
    DEEP_YELLOW = "\33[1;38;2;191;191;0m\33[48;2;0;0;0m"
    LIGHT_YELLOW = "\33[1;38;2;255;255;127m\33[48;2;0;0;0m"
    INV_YELLOW = "\33[1;38;2;0;0;0m\33[48;2;255;255;0m"
    GOLD = "\33[1;38;2;255;191;31m\33[48;2;0;0;0m"
    PALE_GOLD = "\33[1;38;2;223;191;31m\33[48;2;0;0;0m"
    MEDIUM_GOLD = "\33[1;38;2;223;167;27m\33[48;2;0;0;0m"
    DEEP_GOLD = "\33[1;38;2;127;95;15m\33[48;2;0;0;0m"
    DIM_GOLD = "\33[1;38;2;191;143;23m\33[48;2;0;0;0m"
    INV_GOLD = "\33[1;38;2;0;0;0m\33[48;2;255;191;31m"
    INV_DIM_GOLD = "\33[1;38;2;0;0;0m\33[48;2;191;143;23m"
    ORANGE = "\33[1;38;2;255;127;0m\33[48;2;0;0;0m"
    MEDIUM_ORANGE = "\33[1;38;2;191;95;0m\33[48;2;0;0;0m"
    INV_ORANGE = "\33[1;38;2;0;0;0m\33[48;2;255;127;0m"
    BLUE = "\33[1;38;2;31;63;191m\33[48;2;0;0;0m"
    MEDIUM_BLUE = "\33[1;38;2;31;63;127m\33[48;2;0;0;0m"
    MEDLGT_BLUE = "\33[1;38;2;47;95;191m\33[48;2;0;0;0m"
    LIGHT_BLUE = "\33[1;38;2;63;127;255m\33[48;2;0;0;0m"
    INV_LIGHT_BLUE = "\33[1;38;2;0;0;0m\33[48;2;63;127;255m"
    INV_DIM_LIGHT_BLUE = "\33[1;38;2;0;0;0m\33[48;2;31;63;127m"
    BRIGHT_BLUE_IT = "\33[3;94m\33[48;2;0;0;0m"
    MAGENTA = "\33[1;38;2;207;0;207m\33[48;2;0;0;0m"
    MEDIUM_MAGENTA = "\33[1;38;2;155;0;155m\33[48;2;0;0;0m"
    PINK = "\33[1;38;2;245;169;184m\33[48;2;0;0;0m"
    CYAN = "\33[1;38;2;91;206;250m\33[48;2;0;0;0m"
    MEDIUM_CYAN = "\33[1;38;2;0;191;191m\33[48;2;0;0;0m"
    DEEP_CYAN = "\33[1;38;2;0;95;95m\33[48;2;0;0;0m"
    FULL_WHITE = "\33[1;38;2;255;255;255m\33[48;2;0;0;0m"
    DARKER_BEIGE = "\33[0;1;38;2;31;23;15m\33[48;2;0;0;0m"
    DARK_BEIGE = "\33[0;1;38;2;63;47;31m\33[48;2;0;0;0m"
    DEEP_BEIGE = "\33[0;1;38;2;127;95;63m\33[48;2;0;0;0m"
    BEIGE = "\33[0;1;38;2;255;191;127m\33[48;2;0;0;0m"
    MEDIUM_BEIGE = "\33[1;38;2;191;143;95m\33[48;2;0;0;0m"
    LIGHT_BEIGE = "\33[1;38;2;255;239;191m\33[48;2;0;0;0m"
    LIGHTER_BEIGE = "\33[1;38;2;255;247;223m\33[48;2;0;0;0m"
    LIGHT_BEIGE_IT = "\33[0;3;38;2;255;255;191m\33[48;2;0;0;0m"
    INV_LIGHT_BEIGE = "\33[0;1;38;2;0;0;0m\33[48;2;255;239;191m"
    GREY = "\33[1;38;2;127;127;127m\33[48;2;0;0;0m"
    LIGHT_GREY = "\33[1;38;2;191;191;191m\33[48;2;0;0;0m"
    GREYED_GREEN = "\33[1;38;2;63;95;63m\33[48;2;0;0;0m"
    DEEP_GREY_IT = "\33[0;3;38;2;63;63;63m\33[48;2;0;0;0m"
    DEEP_GREY = "\33[0;1;38;2;63;63;63m\33[48;2;0;0;0m"
    DARK_GREY_INV = "\33[0;1;38;2;0;0;0m\33[48;2;31;31;31m"
    DARK_GREY = "\33[1;38;2;31;31;31m\33[48;2;0;0;0m"
    BLUE42 = "\33[0;1;38;2;16;32;96m\33[48;2;0;0;0m"
    MEDIUM_PURPLE = "\33[1;38;2;127;31;127m\33[48;2;0;0;0m"
    DEEP_PURPLE = "\33[1;38;2;54;18;72m\33[48;2;0;0;0m"
    DARK_PURPLE = "\33[1;38;2;27;9;36m\33[48;2;0;0;0m"
    VIOLET = "\33[1;38;2;127;63;255m\33[48;2;0;0;0m"
    LIGHT_VIOLET = "\33[1;38;2;191;95;255m\33[48;2;0;0;0m"
    LIGHT_LIME = "\33[1;38;2;191;255;95m\33[48;2;0;0;0m"
    WARM_BROWN = "\33[1;38;2;96;48;24m\33[48;2;0;0;0m"
    WARM_LIGHT_BROWN = "\33[1;38;2;191;95;47m\33[48;2;0;0;0m"
    INV_WARM_BROWN = "\33[1;38;2;0;0;0m\33[48;2;96;48;24m"
    WARM_DEEP_BROWN = "\33[1;38;2;48;24;12m\33[48;2;0;0;0m"
    DEEP_BROWN = "\33[1;38;2;60;45;30m\33[48;2;0;0;0m"
    DARK_BROWN = "\33[1;38;2;30;22;15m\33[48;2;0;0;0m"
    DARKER_BROWN = "\33[1;38;2;15;11;7m\33[48;2;0;0;0m"
    WALL = "\33[1;38;2;47;47;47m\33[48;2;0;0;0m"
    DARK_WALL = "\33[1;38;2;23;23;23m\33[48;2;0;0;0m"
    TEST_WALKABLE = "\33[1;38;2;15;127;15m\33[48;2;7;63;7m"
    TEST_LIGHTABLE = "\33[1;38;2;0;127;127m\33[48;2;0;63;63m"
    TEST_UNDERGROUND = "\33[1;38;2;60;45;30m\33[48;2;30;22;15m"
    NEUTRAL_BAR = "\33[1;38;2;63;63;63m\33[48;2;15;7;3m"
    GOLD_ON_WARM_BROWN = "\33[1;38;2;255;191;31m\33[48;2;96;48;24m"
    MEDIUM_TEAL_GREEN_ON_DARKER_BROWN = "\33[1;38;2;0;159;79m\33[48;2;15;11;7m"
    DARKER_BROWN_ON_MEDIUM_TEAL_GREEN = "\33[1;38;2;15;11;7m\33[48;2;0;159;79m"
    MEDIUM_TEAL_GREEN_ON_DARK_BROWN = "\33[1;38;2;0;159;79m\33[48;2;30;22;15m"
    DARK_BROWN_ON_MEDIUM_TEAL_GREEN = "\33[1;38;2;30;22;15m\33[48;2;0;159;79m"
    MEDIUM_GOLD_ON_DARKER_BROWN = "\33[1;38;2;223;167;27m\33[48;2;15;11;7m"
    DARKER_BROWN_ON_MEDIUM_GOLD = "\33[1;38;2;15;11;7m\33[48;2;223;167;27m"

    BOLD = "\33[0;1m"
    ITALIC = "\33[0;3m"
    REVERSE = "\33[0;7m"
    RESET = "\33[0m"

    COLOR_DICT: dict[str, tuple[int, int, int]] = {
        "darkred": (95, 0, 0),
        "maroon": (127, 0, 0),
        "red": (255, 0, 0),
        "crimson": (255, 47, 95),
        "lightbrown": (255, 127, 63),
        "brown": (127, 63, 31),
        "deepbrown": (63, 31, 15),
        "darkbrown": (31, 15, 7),
        "darkerbrown": (15, 7, 3),
        "orange": (255, 127, 0),
        "gold": (255, 191, 31),
        "beige": (255, 191, 127),
        "lightbeige": (255, 255, 191),
        "yellow": (255, 255, 0),
        "lime": (127, 255, 63),
        "darklime": (63, 127, 31),
        "green": (0, 255, 0),
        "darkgreen": (0, 127, 0),
        "tealgreen": (0, 159, 79),
        "teal": (0, 127, 127),
        "cyan": (0, 255, 255),
        "lightblue": (63, 127, 255),
        "blue": (31, 63, 255),
        "navy": (15, 31, 127),
        "violet": (127, 63, 255),
        "magenta": (207, 0, 207),
        "purple": (127, 31, 127),
        "lightpurple": (191, 47, 191),
        "white": (255, 255, 255),
        "lightgrey": (191, 191, 191),
        "grey": (95, 95, 95),
        "darkgrey": (63, 63, 63),
        "black": (31, 31, 31),
    }

    def reverse_foreback_colors(self, code: str) -> str:
        """ Swap the foreground and background colors of an ANSI color code """
        match = COLOR_RE.fullmatch(code)
        if not match:
            raise ValueError(f"invalid ANSI color code: {code}")
        fr, fg, fb, br, bg, bb = map(int, match.groups())
        return (f"\33[1;38;2;{br};{bg};{bb}m\33[48;2;{fr};{fg};{fb}m")

    def decode_color(self, code: str) -> tuple[int, int, int, int, int, int]:
        """
        Decode an ANSI color code into foreground and background RGB values.
        """
        match = COLOR_RE.fullmatch(code)
        if not match:
            raise ValueError(f"invalid ANSI color code: {code}")
        fr, fg, fb, br, bg, bb = map(int, match.groups())
        return fr, fg, fb, br, bg, bb

    def decode_forecolor(self, code: str) -> tuple[int, int, int]:
        """ Decode the foreground RGB values of an ANSI color code. """
        match = COLOR_RE.fullmatch(code)
        if not match:
            raise ValueError(f"invalid ANSI color code: {code}")
        fr, fg, fb, _, _, _ = map(int, match.groups())
        return fr, fg, fb

    def encode_color(self, fr: int, fg: int, fb: int,
                     br: int, bg: int, bb: int, italic: bool = False) -> str:
        """
        Encode foreground and background RGB values as an ANSI color code.
        Remove bold and enable italic styling when requested.
        """
        fr = min(255, max(0, fr))
        fg = min(255, max(0, fg))
        fb = min(255, max(0, fb))
        br = min(255, max(0, br))
        bg = min(255, max(0, bg))
        bb = min(255, max(0, bb))
        if italic is True:
            return (f"\33[0;3;38;2;{fr};{fg};{fb}m\33[48;2;{br};{bg};{bb}m")
        return (f"\33[1;38;2;{fr};{fg};{fb}m\33[48;2;{br};{bg};{bb}m")

    def color_to_rgb(self, name: str) -> tuple[int, int, int]:
        """ Return the RGB value associated with a color name. """
        try:
            return Colors.COLOR_DICT[name.lower()]
        except KeyError:
            raise ValueError(f"unknown color name: {name}")

    def clamp_rgb(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        """ Clamp RGB components to the valid range from 0 to 255. """
        return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))

    def normalize_rgb(self, rgb: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Scale RGB components proportionally to prevent upper saturation """
        r, g, b = (max(0, rgb[0]), max(0, rgb[1]), max(0, rgb[2]))
        maximum = max(r, g, b)
        if maximum <= 255:
            return r, g, b
        scale = 255 / maximum
        return (int(r * scale), int(g * scale), int(b * scale))

    def add_rgb(self, rgb1: tuple[int, int, int],
                rgb2: tuple[int, int, int]) -> tuple[int, int, int]:
        """ Add two RGB colors while limiting each component to 255. """
        return (min(255, rgb1[0] + rgb2[0]), min(255, rgb1[1] + rgb2[1]),
                min(255, rgb1[2] + rgb2[2]))

    def attenuate_rgb(self, rgb: tuple[int, int, int],
                      amount: int) -> tuple[int, int, int]:
        """ Reduce every RGB component by the specified amount. """
        amount = max(0, amount)
        return (max(0, rgb[0] - amount), max(0, rgb[1] - amount),
                max(0, rgb[2] - amount))

    def scale_rgb(self, rgb: tuple[int, int, int],
                  factor: float) -> tuple[int, int, int]:
        """ Scale RGB components by the specified factor. """
        return (max(0, min(255, int(rgb[0] * factor))),
                max(0, min(255, int(rgb[1] * factor))),
                max(0, min(255, int(rgb[2] * factor))))

    def scale_color_back(self, code: str, factor: float) -> str:
        """ Scale the background RGB components of an ANSI color code. """
        fr, fg, fb, br, bg, bb = self.decode_color(code)
        br, bg, bb = self.scale_rgb((br, bg, bb), factor)
        return self.encode_color(fr, fg, fb, br, bg, bb)

    def scale_color_fore(self, code: str, factor: float) -> str:
        """ Scale the foreground RGB components of an ANSI color code. """
        fr, fg, fb, br, bg, bb = self.decode_color(code)
        fr, fg, fb = self.scale_rgb((fr, fg, fb), factor)
        return self.encode_color(fr, fg, fb, br, bg, bb)

    def scale_color(self, code: str, factor: float) -> str:
        """
        Scale both foreground and background RGB components of
        an ANSI color code.
        """
        fr, fg, fb, br, bg, bb = self.decode_color(code)
        fr, fg, fb = self.scale_rgb((fr, fg, fb), factor)
        br, bg, bb = self.scale_rgb((br, bg, bb), factor)
        return self.encode_color(fr, fg, fb, br, bg, bb)

    def italic_color(self, code: str) -> str:
        """ Replace bold styling with italic styling in an ANSI color code. """
        fr, fg, fb, br, bg, bb = self.decode_color(code)
        return self.encode_color(fr, fg, fb, br, bg, bb, italic=True)

    def compose_foreback_color(self, forecode: str, backcode: str) -> str:
        """
        Combine the foreground colors of two ANSI color codes.
        Use the first code as the resulting foreground and the second code
        as the resulting background.
        """
        fr, fg, fb, _, _, _ = self.decode_color(forecode)
        br, bg, bb, _, _, _ = self.decode_color(backcode)
        return self.encode_color(fr, fg, fb, br, bg, bb)

    def average_colors(self, code_a: str, code_b: str) -> str:
        """ Return the component-wise average of two ANSI color codes. """
        fr_a, fg_a, fb_a, br_a, bg_a, bb_a = self.decode_color(code_a)
        fr_b, fg_b, fb_b, br_b, bg_b, bb_b = self.decode_color(code_b)
        fr_avg, br_avg = (fr_a + fr_b) // 2, (br_a + br_b) // 2
        fg_avg, bg_avg = (fg_a + fg_b) // 2, (bg_a + bg_b) // 2
        fb_avg, bb_avg = (fb_a + fb_b) // 2, (bb_a + bb_b) // 2
        return self.encode_color(fr_avg, fg_avg, fb_avg,
                                 br_avg, bg_avg, bb_avg)
