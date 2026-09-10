"""Crop the recorded game UI frames into a real-time GIF (no synthetic visuals)."""
from pathlib import Path
from PIL import Image
import argparse
import json

parser=argparse.ArgumentParser()
parser.add_argument('--width',type=int,default=1280)
args=parser.parse_args()
directory=Path(__file__).resolve().parents[2]/'Saved'/'InventoryVisual'
paths=sorted(directory.glob(f'glint-{args.width}-[0-9][0-9].png'))
assert len(paths)==32, f'Expected 32 recorded frames, got {len(paths)}'
images=[Image.open(path).convert('RGB') for path in paths]
width,height=images[0].size
box=(round(width*.55),110,width,height)
frames=[image.crop(box) for image in images]
output=directory/f'corner-glints-{width}.gif'
frames[0].save(output,save_all=True,append_images=frames[1:],duration=120,loop=0,optimize=False)
report={'frames':len(paths),'frame_interval_ms':120,'crop':box,'unique_ui_frames':len({frame.tobytes() for frame in frames}),'gif':str(output)}
assert report['unique_ui_frames']>10, 'Recorded UI appears static'
(directory/f'corner-glints-{width}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
