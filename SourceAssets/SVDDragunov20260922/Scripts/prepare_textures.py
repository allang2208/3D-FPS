"""Copy the SVD's ten 4096 maps into Textures/ with stable names.

Albedo / roughness / metallic / AO stay JPEG (a byte copy, no recompression); the normal
map is converted to PNG because JPEG ringing on a normal map shows up directly as shading
noise on a first-person weapon viewed up close.

Run:
    python prepare_textures.py [case_root]
"""
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def main():
    case = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    spec = json.loads((case / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
    cap = int(spec.get('texture_max_size', 4096))
    to_png = bool(spec.get('normal_to_png', True))
    out_dir = case / 'Textures'
    out_dir.mkdir(exist_ok=True)
    src_root = case / 'Source'
    manifest = []

    for part in spec['parts']:
        for role, rel in part['maps'].items():
            src = src_root / rel
            if not src.exists():
                manifest.append({'part': part['key'], 'role': role, 'source': str(src), 'missing': True})
                continue
            want_png = to_png and role == 'normal'
            ext = '.png' if want_png else src.suffix.lower()
            dest = out_dir / ('T_SVD_%s_%s%s' % (part['texture_set'], role, ext))
            original = None
            if want_png or max(Image.open(src).size) > cap:
                img = Image.open(src)
                original = list(img.size)
                if max(img.size) > cap:
                    scale = cap / max(img.size)
                    img = img.resize((round(img.size[0] * scale), round(img.size[1] * scale)), Image.LANCZOS)
                if want_png:
                    img.save(dest, 'PNG')
                else:
                    img.convert('RGB').save(dest, 'JPEG', quality=95, subsampling=0)
            else:
                shutil.copyfile(src, dest)
            manifest.append({
                'part': part['key'], 'role': role, 'texture_set': part['texture_set'],
                'source': str(src), 'output': str(dest), 'asset_name': dest.stem,
                'original_size': original, 'bytes': dest.stat().st_size,
            })
            print('TEXTURE %-6s %-10s -> %-32s %7.1f MB' % (part['key'], role, dest.name, dest.stat().st_size / 1048576))

    (case / 'Receipts').mkdir(exist_ok=True)
    (case / 'Receipts' / 'textures.json').write_text(json.dumps(manifest, indent=2, default=str), encoding='utf-8')
    missing = [m for m in manifest if m.get('missing')]
    print('SVD_TEXTURE_PREP_DONE', len(manifest), 'maps,', len(missing), 'missing')


main()
