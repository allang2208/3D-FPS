"""Prepare the three Meshy input views from the V2 reference. No creative image edits."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'References/V2/hundred_eyed_slag_turnaround_v2.png'
# Native V2 image is 1902 x 827; split points fall in empty gutters.
CELLS = [('front', (0, 0, 616, 827)),
         ('right', (616, 0, 1295, 827)),
         ('back', (1295, 0, 1902, 827))]
image = Image.open(SOURCE).convert('RGB')
outputs = []
for view, box in CELLS:
    patch = image.crop(box)
    # Keep identical pixel scale and vertical alignment; add white padding only.
    square = Image.new('RGB', (827, 827), 'white')
    square.paste(patch, ((827 - patch.width) // 2, 0))
    output = ROOT / 'Inputs/body' / (view + '.png')
    output.parent.mkdir(parents=True, exist_ok=True)
    square.save(output)
    outputs.append({'view': view, 'crop_xyxy': box,
                    'file': output.relative_to(ROOT).as_posix(), 'size': square.size})
(ROOT / 'Inputs/view_mapping.json').write_text(
    json.dumps({'source': SOURCE.relative_to(ROOT).as_posix(),
                'order': ['front', 'right', 'back'], 'views': outputs},
               ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'prepared_views': len(outputs)}, ensure_ascii=False))
