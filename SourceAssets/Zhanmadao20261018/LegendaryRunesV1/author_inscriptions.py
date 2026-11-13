"""Typeset the two blade inscriptions in the native Dao material's central 40% UV lane."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parent
font = ImageFont.truetype("C:/Windows/Fonts/simkai.ttf", 400)
for key, inscription in (("chixiao", "赤霄"), ("zhufeng", "逐风")):
    mask = Image.new("L", (1024, 1024))
    draw = ImageDraw.Draw(mask)
    for char, center_y in zip(inscription, (295, 729)):
        left, top, right, bottom = font.getbbox(char)
        draw.text((512 - (left + right) / 2, center_y - (top + bottom) / 2),
                  char, fill=255, font=font)
    mask.save(root / f"T_Mask_{key}_rune.png")
