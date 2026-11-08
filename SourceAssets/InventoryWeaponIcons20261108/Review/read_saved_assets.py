"""Read-only, independent-process check of the two saved inventory textures."""
import hashlib
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
report = {'textures': [], 'm249_materials': [], 'errors': [], 'multiplayer_runtime_tested': False}
receipts = json.loads((ROOT.parent / 'saved-icons.json').read_text(encoding='utf-8-sig'))
for entry, expected in zip(receipts, [(512, 1536), (800, 320)]):
    texture = u.load_asset(entry['texture'])
    if not isinstance(texture, u.Texture2D):
        report['errors'].append('Missing texture: ' + entry['texture'])
        continue
    size = (texture.blueprint_get_size_x(), texture.blueprint_get_size_y())
    settings = {p: str(texture.get_editor_property(p)) for p in
                ['lod_group', 'compression_settings', 'mip_gen_settings', 'srgb', 'never_stream', 'max_texture_size']}
    actual_hash = hashlib.sha256(Path(entry['png']).read_bytes()).hexdigest()
    row = dict(asset=texture.get_path_name(), size=size, settings=settings,
               png_sha256=actual_hash, receipt_matches=actual_hash == entry['png_sha256'])
    report['textures'].append(row)
    if size != expected or not row['receipt_matches']:
        report['errors'].append('Texture size/source mismatch: ' + entry['texture'])
    if (texture.get_editor_property('lod_group') != u.TextureGroup.TEXTUREGROUP_UI or
            texture.get_editor_property('compression_settings') != u.TextureCompressionSettings.TC_EDITOR_ICON or
            texture.get_editor_property('mip_gen_settings') != u.TextureMipGenSettings.TMGS_NO_MIPMAPS or
            not texture.get_editor_property('srgb') or not texture.get_editor_property('never_stream')):
        report['errors'].append('Unexpected UI settings: ' + entry['texture'])

mesh = u.load_asset('/Game/Weapons/M249/SK_M249_V7')
if mesh:
    for entry in mesh.get_editor_property('materials'):
        material = entry.get_editor_property('material_interface')
        report['m249_materials'].append(dict(
            slot=str(entry.get_editor_property('material_slot_name')),
            material=material.get_path_name() if material else None))
else:
    report['errors'].append('Missing M249 mesh')
if not any(row['slot'] == 'M249_Factory_Handle' and row['material'] for row in report['m249_materials']):
    report['errors'].append('M249 handle material binding missing')

(ROOT / 'saved-assets-readback.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
if report['errors']:
    raise RuntimeError('; '.join(report['errors']))
print('INVENTORY_ICON_REVIEW_SAVED_ASSETS_OK', flush=True)
