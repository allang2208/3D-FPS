"""Copy and downscale every texture the import spec needs into Textures/.

Props are small objects, so 2048 px is plenty (several sources ship 4K+ at 17-24 MB
per map). Each output is written as PNG with a stable name so the UE side never has
to guess: T_Prop_<Name>_<Slot>_<Role>.png.

Run:
    python prepare_textures.py [case_root]
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    case = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    spec = json.loads((case / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
    cap = int(spec.get('texture_max_size', 2048))
    out_root = case / 'Textures'
    out_root.mkdir(exist_ok=True)
    manifest = {}

    for prop in spec['props']:
        key = prop['key']
        src_root = case / 'Source' / key
        out_dir = out_root / key
        out_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for mat in prop.get('materials', []):
            slot = mat.get('slot', '*')
            slot_tag = 'All' if slot == '*' else re.sub(r'[^0-9A-Za-z]+', '', slot.title())
            for role, rel in (mat.get('maps') or {}).items():
                src = src_root / rel
                if not src.exists():
                    entries.append({'role': role, 'source': str(src), 'missing': True})
                    continue
                img = Image.open(src)
                original = img.size
                if max(img.size) > cap:
                    scale = cap / max(img.size)
                    img = img.resize((max(1, round(img.size[0] * scale)), max(1, round(img.size[1] * scale))),
                                     Image.LANCZOS)
                if img.mode not in ('RGB', 'RGBA', 'L'):
                    img = img.convert('RGBA' if 'A' in img.getbands() else 'RGB')
                dest = out_dir / ('T_Prop_%s_%s_%s.png' % (prop['name'], slot_tag, role))
                img.save(dest, 'PNG', optimize=False)
                entries.append({
                    'role': role, 'source': str(src), 'output': str(dest),
                    'original_size': list(original), 'output_size': list(img.size),
                    'mode': img.mode,
                })
        manifest[key] = entries
        print('TEXTURES', key, json.dumps(entries, default=str))

    (case / 'Receipts').mkdir(exist_ok=True)
    (case / 'Receipts' / 'textures.json').write_text(json.dumps(manifest, indent=2, default=str), encoding='utf-8')
    missing = [e for entries in manifest.values() for e in entries if e.get('missing')]
    print('TEXTURE_PREP_DONE', len(manifest), 'props,', sum(len(v) for v in manifest.values()), 'maps,', len(missing), 'missing')


main()
