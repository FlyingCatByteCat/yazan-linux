"""GRUB theme generator for Yazan Linux.

Writes a black-background theme with the Tux logo rendered as blue text on
a generated PNG and highlights all menu entries in the Arch blue accent.

The PNG is produced with the standard library only (struct + zlib) so no
image tooling is required on the live media or in the chroot.
"""

import os
import struct
import zlib

BLUE = (23, 147, 209)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

TUX = [
    "        .--.",
    "       |o_o |",
    "       |:_/ |",
    "      //   \\ \\",
    "     (|     | )",
    "    /'\\_   _/`\\",
    "    \\___)=(___/",
]

# 5x7 bitmap glyphs for every character used by the Tux logo.
# Each glyph is a row-major list of 7 strings, width 5, '#' = filled.
GLYPHS = {}


def _glyph(ch, rows):
    global GLYPHS
    packed = []
    for row in rows:
        packed.append(row.ljust(5))
    GLYPHS[ch] = packed


_glyph(".", [".....", ".....", ".....", ".....", ".....", "##...", "##..."])
_glyph("-", [".....", ".....", ".....", "#####", ".....", ".....", "....."])
_glyph("_", [".....", ".....", ".....", ".....", ".....", "..##.", "####."])
_glyph("/", ["....#", "...#.", "...#.", "..#..", "..#..", ".#...", ".#..."])
_glyph("\\", ["#....", ".#...", ".#...", "..#..", "..#..", "...#.", "...#."])
_glyph("(", ["...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."])
_glyph(")", [".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."])
_glyph("=", [".....", "#####", ".....", ".....", ".....", "#####", "....."])
_glyph("|", ["..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."])
_glyph("o", [".....", ".##..", "#..#.", "#..#.", "#..#.", ".##..", "....."])
_glyph(":", [".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."])
_glyph("^", [".....", ".....", "..#..", ".#.#.", "#...", ".....", "....."])
_glyph("'", ["..#..", "..#..", ".....", ".....", ".....", ".....", "....."])
_glyph("`", [".#...", ".#...", ".....", ".....", ".....", ".....", "....."])
_glyph(" ", [".....", ".....", ".....", ".....", ".....", ".....", "....."])


def _glyph_size():
    return (5, 7)


def render_text(text_lines, scale=1, color=BLUE, margin=0):
    """Return a pixel RGB matrix of the given text lines on black."""
    glyph_w, glyph_h = _glyph_size()

    def glyph_for(ch):
        return GLYPHS.get(ch, GLYPHS[" "])

    max_line_len = max(len(line) for line in text_lines)
    width = margin * 2 + max_line_len * (glyph_w + 1) + 1
    height = margin * 2 + len(text_lines) * (glyph_h + 1)

    pixels = [[BLACK for _ in range(width)] for _ in range(height)]

    def source_bit(ch, x, y):
        return glyph_for(ch)[y][x] == "#"

    for row_idx, line in enumerate(text_lines):
        for col_idx, ch in enumerate(line):
            cx = margin + (col_idx * (glyph_w + 1))
            cy = margin + (row_idx * (glyph_h + 1))
            for gy in range(glyph_h):
                for gx in range(glyph_w):
                    if source_bit(ch, gx, gy):
                        px = cx + gx
                        py = cy + gy
                        if 0 <= px < width and 0 <= py < height:
                            pixels[py][px] = color
    return pixels


def write_png(path, pixels):
    height = len(pixels)
    width = len(pixels[0])
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter type 0
        for r, g, b in row:
            raw += bytes((int(r), int(g), int(b)))

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n")
        fh.write(chunk(b"IHDR", ihdr))
        fh.write(chunk(b"IDAT", idat))
        fh.write(chunk(b"IEND", b""))


THEME_TEXT = """\
# Yazan Linux GRUB theme
# Black background, Tux logo, Arch blue accent entries.

desktop-image: "background.png"
desktop-color: "#000000"
title-text: "Yazan Linux"
title-font: "Unifont Regular 16"
title-color: "#1793D1"

+ boot_menu {
    left = 50%-w/2
    top  = 25%+h/2
    width = 40%
    height = 40%
    item_font = "Unifont Regular 16"
    item_color = "#1793D1"
    selected_item_color = "#ffffff"
    item_height = 22
    item_spacing = 6
}

+ label {
    left = 50%-40%
    top = 8%
    width = 80%
    align = "center"
    text = "Yazan Linux"
    font = "Unifont Regular 16"
    color = "#1793D1"
}
"""


def generate_theme(target_dir):
    os.makedirs(target_dir, exist_ok=True)
    pixels = render_text(TUX, scale=1, color=BLUE, margin=12)
    write_png(os.path.join(target_dir, "background.png"), pixels)
    with open(os.path.join(target_dir, "theme.txt"), "w") as fh:
        fh.write(THEME_TEXT)
    return target_dir


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "/tmp/yazan-grub-theme"
    print(generate_theme(out))