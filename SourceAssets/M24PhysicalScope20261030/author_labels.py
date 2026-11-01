"""Angular reticle labels only; lines/ticks are analytic in the lens shader."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

out = Path(__file__).resolve().parent
size = 2048
ink = Image.new('L', (size, size))
draw = ImageDraw.Draw(ink)
font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 54)

def label(x_mil, y_mil, text):
    draw.text(((x_mil / 48 + .5) * size, (y_mil / 48 + .5) * size), text, font=font, fill=255, anchor='mm')

for value in (5, 10, 15, 20):
    for sign in (-1, 1):
        label(sign * value, 1.3, str(value))
    label(1.7, value, str(value))
halo = ink.filter(ImageFilter.MaxFilter(5))
Image.merge('RGBA', (ink, halo, Image.new('L', ink.size), Image.new('L', ink.size, 255))).save(out / 'T_M24_MilLabels.png')
print('M24 angular label source authored')
