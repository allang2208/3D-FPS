"""Rasterize the existing glove mesh UV islands; no source texture is repainted."""
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

O = Path(__file__).parent
size = 4096
mask = Image.new('L', (size, size), 0)
draw = ImageDraw.Draw(mask)
faces = json.loads((O/'glove_uv_faces.json').read_text())
for face in faces:
    draw.polygon([(u*(size-1), (1-v)*(size-1)) for u,v in face], fill=255)
mask = mask.filter(ImageFilter.MaxFilter(9))
mask.save(O/'T_Manny_GloveMask.png')
print('GLOVE_MASK', len(faces), mask.getbbox())
