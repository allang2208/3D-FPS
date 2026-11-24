"""Prepare the ImageGen masters for the workbench's grayscale RGBA texture format."""
from pathlib import Path
import json
import sys
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

here = Path(__file__).resolve().parent
factory_slots = ('blade_1', 'guard', 'grip', 'pommel', 'blade_material')


def prepare_factory_icons():
    # Work at the approved artwork's native resolution. Only the photograph inside
    # the recessed well is interchangeable; the silver rim and all exterior pixels
    # (including the steel tint and the transparent corners) belong to the master.
    frame_path = here.parents[1] / 'FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'
    with Image.open(frame_path) as original:
        frame = original.convert('RGBA')
    if frame.size != (1254, 1254):
        raise ValueError(f'Factory frame aperture is authored for the 1254px master: {frame_path}')
    aperture = Image.new('L', frame.size, 0)
    ImageDraw.Draw(aperture).ellipse((144, 139, 1099, 1068), fill=255)
    aperture = ImageChops.darker(aperture, aperture.filter(ImageFilter.GaussianBlur(1.5)))
    for slot in factory_slots:
        name = slot + '_factory.png'
        with Image.open(here / 'IconMasters' / name) as part:
            if part.size != frame.size:
                raise ValueError(f'Unregistered factory artwork size for {name}: {part.size}')
            plate = ImageOps.grayscale(part).convert('RGBA')
        result = Image.composite(plate, frame, aperture)
        result.save(here / 'Icons' / name)


if '--raven-quill-guard' in sys.argv:
    keys = ['guard_raven_quill_guard']
elif '--exclusive' in sys.argv:
    keys = json.loads((here / 'exclusive_cards.json').read_text(encoding='utf-8'))['parts']
else:
    prepare_factory_icons()
    keys = []
for key in keys:
    name = key + '.png'
    with Image.open(here / 'IconMasters' / name) as source:
        rgba = source.convert('RGBA')
        gray = ImageOps.grayscale(rgba)
        # The generated backplate is near-opaque. Keep transparency only at the outer bevel.
        alpha = rgba.getchannel('A').point(lambda a: min(255, round(a * 255 / 244)))
        icon = Image.merge('RGBA', (gray, gray, gray, alpha))
        icon.resize((1024, 1024), Image.Resampling.LANCZOS).save(here / 'Icons' / name)
