"""Prepare the ImageGen masters for the workbench's grayscale RGBA texture format."""
from pathlib import Path
from PIL import Image, ImageOps

here = Path(__file__).resolve().parent
for slot in ('blade_1', 'guard', 'grip', 'pommel', 'blade_material'):
    name = slot + '_factory.png'
    with Image.open(here / 'IconMasters' / name) as source:
        rgba = source.convert('RGBA')
        gray = ImageOps.grayscale(rgba)
        # The generated backplate is near-opaque. Keep transparency only at the outer bevel.
        alpha = rgba.getchannel('A').point(lambda a: min(255, round(a * 255 / 244)))
        icon = Image.merge('RGBA', (gray, gray, gray, alpha))
        icon.resize((1024, 1024), Image.Resampling.LANCZOS).save(here / 'Icons' / name)
