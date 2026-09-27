"""Split the approved V02 sheet deterministically for multi-view 3D input."""
from pathlib import Path
import hashlib
import json
from PIL import Image

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'References/FleshHand_ThreeViews_v02_Green.png'
OUT = ROOT/'References/MeshyInputs'
OUT.mkdir(parents=True, exist_ok=True)
sheet = Image.open(SOURCE).convert('RGB')
w, h = sheet.size
# Empty gutters of the approved 1774:887 sheet; preserve pixels and common scale.
spans = [('01_front_palm', 0, 690), ('02_side', 690, 1085), ('03_back', 1085, 1774)]
records = []
for name, left, right in spans:
    rect = (round(left*w/1774), 0, round(right*w/1774), h)
    cut = sheet.crop(rect)
    side = max(h, cut.width)
    canvas = Image.new('RGB', (side, side), 'white')
    offset = ((side-cut.width)//2, (side-h)//2)
    canvas.paste(cut, offset)
    path = OUT/(name+'.png')
    canvas.save(path)
    records.append({'path': str(path.relative_to(ROOT)), 'source_box': rect,
                    'padding_offset': offset, 'size': canvas.size,
                    'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
(OUT/'inputs.json').write_text(json.dumps({'source':str(SOURCE.relative_to(ROOT)),
    'source_size':sheet.size,'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'operation':'crop and white padding only; unchanged object pixels and common height',
    'primary_view':'front palm','views':records},ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'prepared_views':len(records),'source_size':sheet.size}))
