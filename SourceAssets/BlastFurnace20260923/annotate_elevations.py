"""Annotate the contract elevations by measuring the rendered silhouette.

    python SourceAssets/BlastFurnace20260923/annotate_elevations.py

The elevation renders use a transparent film, so the silhouette comes from the
alpha channel rather than a brightness threshold — the drawn numbers are
measured pixels times the known orthographic scale, not the numbers the
authoring script claimed.
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Authored' / 'Verify'
MM_PER_PIXEL = 2.60 / 1240.0 * 1000.0
FONT = Path('C:/Windows/Fonts/msyhbd.ttc')
if not FONT.exists():
    FONT = Path('C:/Windows/Fonts/arialbd.ttf')

# Key contract heights, in centimetres above the base.
KEY_HEIGHTS = [
    (47.0, '炉基压顶 47'),
    (168.0, '炉身收顶 168'),
    (220.0, '炉口 220'),
]

JOBS = [
    ('elevation_front_clay.png', 'annotated_side_Y100.png',
     '相机 +X 方向看：横向 = Y 向 100 cm', 100.0),
    ('elevation_side_clay.png', 'annotated_front_X120.png',
     '相机 -Y 方向看：横向 = X 向 120 cm（右为出铁口侧 +X）', 120.0),
]


def measure(image):
    alpha = image.getchannel('A')
    box = alpha.point(lambda v: 255 if v > 128 else 0).getbbox()
    return box


def arrow(draw, start, end, colour, width=3):
    draw.line([start, end], fill=colour, width=width)
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / length, dy / length
    for point, sign in ((start, 1), (end, -1)):
        draw.polygon([
            point,
            (point[0] + sign * ux * 18 - uy * 7, point[1] + sign * uy * 18 + ux * 7),
            (point[0] + sign * ux * 18 + uy * 7, point[1] + sign * uy * 18 - ux * 7),
        ], fill=colour)


report = {'mm_per_pixel': round(MM_PER_PIXEL, 4), 'measurements': []}
font_big = ImageFont.truetype(str(FONT), 34)
font_small = ImageFont.truetype(str(FONT), 26)

for source, target, caption, contract_width in JOBS:
    image = Image.open(OUT / source).convert('RGBA')
    box = measure(image)
    if box is None:
        raise SystemExit('No silhouette found in ' + source)
    left, top, right, bottom = box
    measured_width = (right - left) * MM_PER_PIXEL / 10.0
    measured_height = (bottom - top) * MM_PER_PIXEL / 10.0

    canvas = Image.new('RGB', (image.width + 300, image.height), (34, 36, 40))
    canvas.paste(image, (190, 0), image)
    draw = ImageDraw.Draw(canvas)
    origin_x, origin_y = 190, 0
    red = (232, 96, 72)
    blue = (96, 176, 232)

    # Overall width, measured under the model.
    y = min(canvas.height - 70, bottom + 46)
    arrow(draw, (origin_x + left, y), (origin_x + right, y), red)
    draw.text((origin_x + left, y + 12), '实测 %.1f cm ／ 契约 %.1f cm'
              % (measured_width, contract_width), font=font_small, fill=red)

    # Overall height, measured to the left of the model.
    x = max(40, origin_x + left - 58)
    arrow(draw, (x, origin_y + top), (x, origin_y + bottom), red)
    draw.text((14, origin_y + top - 46), '实测 %.1f' % measured_height, font=font_small, fill=red)
    draw.text((14, origin_y + top - 16), '契约 220.0 cm', font=font_small, fill=red)

    # Key contract heights as ticks on the right edge.
    for height_cm, label in KEY_HEIGHTS:
        ty = origin_y + bottom - height_cm * 10.0 / MM_PER_PIXEL
        draw.line([(origin_x + right + 6, ty), (origin_x + right + 40, ty)], fill=blue, width=2)
        draw.text((origin_x + right + 46, ty - 14), label, font=font_small, fill=blue)

    draw.text((14, 16), caption, font=font_big, fill=(238, 238, 232))
    draw.text((14, 58), '白膜（Clay）正交立面 · %.3f mm/px' % MM_PER_PIXEL,
              font=font_small, fill=(178, 182, 188))

    canvas.save(OUT / target)
    report['measurements'].append({
        'source': source, 'annotated': target,
        'measured_width_cm': round(measured_width, 2),
        'measured_height_cm': round(measured_height, 2),
        'contract_width_cm': contract_width, 'contract_height_cm': 220.0,
        'width_error_cm': round(measured_width - contract_width, 2),
        'height_error_cm': round(measured_height - 220.0, 2)})
    print('ANNOTATED %s width %.2f (contract %.1f) height %.2f (contract 220.0)'
          % (target, measured_width, contract_width, measured_height), flush=True)

# A caption on the scale reference so the figure's height is explicit.
scale = Image.open(OUT / 'scale_reference_clay.png').convert('RGB')
draw = ImageDraw.Draw(scale)
draw.text((18, 16), '白膜 + 180 cm 人形参照', font=font_big, fill=(238, 238, 232))
draw.text((18, 58), '高炉 220 cm ／ 参照人形 180 cm', font=font_small, fill=(178, 182, 188))
scale.save(OUT / 'annotated_scale_reference.png')

(OUT / 'elevation-measurements.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('ELEVATION_ANNOTATION_DONE')
