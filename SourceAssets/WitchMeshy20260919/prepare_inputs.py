"""Split the approved reference plates into individual Meshy inputs; no repainting."""
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
REF = ROOT / 'Reference'
OUT = ROOT / 'Inputs'


def foreground(image):
    rgb = image.convert('RGB')
    filled = rgb.copy()
    marker = (255, 0, 255)
    ImageDraw.floodfill(filled, (0, 0), marker, thresh=36)
    mask = Image.new('L', rgb.size)
    mask.putdata([0 if value == marker else 255 for value in filled.getdata()])
    rgba = rgb.convert('RGBA')
    rgba.putalpha(mask)
    return rgba


def save_group(source, boxes, labels, name):
    image = Image.open(REF / source)
    crops = [foreground(image.crop(box)) for box in boxes]
    # One common scale per object, preserving cross-view height relationships.
    scale = min(960 / max(c.height for c in crops), 960 / max(c.width for c in crops))
    folder = OUT / name
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for crop, box, label in zip(crops, boxes, labels):
        resized = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.LANCZOS)
        canvas = Image.new('RGBA', (1024, 1024), (255, 255, 255, 0))
        canvas.alpha_composite(resized, ((1024 - resized.width) // 2, 1024 - 32 - resized.height))
        path = folder / f'{label}.png'
        canvas.save(path)
        records.append({'path': path.relative_to(ROOT).as_posix(), 'view': label, 'crop_xyxy': box})
    return {'source': source, 'source_size': image.size, 'same_scale_per_object': scale, 'views': records}


def main():
    body = Image.open(REF / 'body_three_views_v01.png')
    w, h = body.size
    # Gutters of this actual 1774x887 plate, normalized to its dimensions.
    cuts = [0, round(w * 650 / 1774), round(w * 1135 / 1774), w]
    body_boxes = [(cuts[i], 0, cuts[i + 1], h) for i in range(3)]
    props = Image.open(REF / 'props_three_views_v02.png')
    pw, ph = props.size
    cols = [round(pw * i / 3) for i in range(4)]
    split = round(ph * 636 / 1024)
    staff_boxes = [(cols[i], 0, cols[i + 1], split) for i in range(3)]
    bottle_boxes = [(cols[i], split, cols[i + 1], ph) for i in range(3)]
    manifest = {
        'operation': 'Crop only; edge-connected near-white background converted to alpha; equal scale per object.',
        'body': save_group('body_three_views_v01.png', body_boxes, ['front', 'left', 'back'], 'body'),
        'staff': save_group('props_three_views_v02.png', staff_boxes, ['front', 'side', 'back'], 'staff'),
        'bottle': save_group('props_three_views_v02.png', bottle_boxes, ['front', 'side', 'back'], 'bottle'),
        'stage': 'production_inputs_not_visual_acceptance',
    }
    (OUT / 'input_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'prepared': 9, 'folder': str(OUT)}))


if __name__ == '__main__':
    main()
