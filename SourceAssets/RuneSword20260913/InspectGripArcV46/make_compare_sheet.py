"""Stack the video reference frames over the matching shipped-animation renders."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

P = Path(__file__).parent
REF = P.parent / 'VideoReferenceStudy20260915/Original'
SHOTS = P / 'TwirlCompare'
PHASES = [(7, 76.0000), (8, 76.0333), (9, 76.0667), (10, 76.1000), (11, 76.1333),
          (12, 76.1667), (13, 76.2000), (14, 76.2333), (15, 76.2667), (16, 76.3000),
          (17, 76.3333), (19, 76.4000), (20, 76.4333), (21, 76.4667)]
CROP = (536, 96, 852, 480)
COLUMNS = 7
SCALE = 1.0


def load(path):
    image = Image.open(path).convert('RGB')
    return image.crop(CROP)


cell_w = CROP[2] - CROP[0]
cell_h = CROP[3] - CROP[1]
rows = (len(PHASES) + COLUMNS - 1) // COLUMNS
sheet = Image.new('RGB', (COLUMNS * cell_w, rows * 2 * (cell_h + 18)), (12, 14, 20))
draw = ImageDraw.Draw(sheet)

for i, (index, seconds) in enumerate(PHASES):
    column = i % COLUMNS
    row = i // COLUMNS
    x = column * cell_w
    ref = load(REF / ('source_%03d.png' % index))
    shot = load(SHOTS / ('v42_%02d_%07.4f.png' % (index, seconds)))
    top = row * 2 * (cell_h + 18)
    sheet.paste(ref, (x, top))
    draw.text((x + 4, top + cell_h + 3), 'REF %.4f s  f%02d' % (seconds, index),
              fill=(230, 210, 120))
    sheet.paste(shot, (x, top + cell_h + 18))
    draw.text((x + 4, top + 2 * cell_h + 21),
              'V42 clip %.3f s' % (0.350 + seconds - 76.0), fill=(150, 210, 255))

out = P / 'reference_vs_v42_twirl.png'
if SCALE != 1.0:
    sheet = sheet.resize((int(sheet.width * SCALE), int(sheet.height * SCALE)),
                         Image.LANCZOS)
sheet.save(out, quality=92)
print('SHEET', out, sheet.size)
print('COMPARE_SHEET_DONE')
