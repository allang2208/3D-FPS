"""Why does the furnace render untextured in game?

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

Checks the three links in order and stops at the first one that is broken,
printing numbers instead of a diagnosis:

1. the static mesh's material slots and what they point at;
2. each material's texture parameters, and whether the referenced texture
   assets exist on disk;
3. the texture assets themselves: source size, compression, whether the
   imported pixel data is a placeholder (a 4x4 or 1x1 source means the import
   failed rather than the material).
"""
import json
from pathlib import Path

import unreal as u

ROOT = '/Game/Props/BlastFurnace20260923'
MESH = ROOT + '/SM_BlastFurnace'
SLOTS = ('Masonry', 'Firebrick', 'WroughtIron', 'ClayLuting',
         'SlagLining', 'EmberBed', 'OreLump')
CHANNELS = ('BaseColor', 'Roughness', 'Metallic', 'Normal', 'AO')

report = {'mesh': {}, 'materials': {}, 'textures': {}}


def texture_row(path):
    texture = u.load_asset(path)
    if texture is None:
        return {'loaded': False, 'exists_on_disk': u.EditorAssetLibrary.does_asset_exist(path)}
    size_x, size_y = texture.blueprint_get_size_x(), texture.blueprint_get_size_y()
    return {
        'loaded': True,
        'size': [size_x, size_y],
        'placeholder': size_x <= 4 or size_y <= 4,
        'srgb': bool(texture.get_editor_property('srgb')),
        'compression': str(texture.get_editor_property('compression_settings')),
    }


mesh = u.load_asset(MESH)
if mesh is None:
    raise SystemExit('MESH_MISSING')
report['mesh'] = {
    'asset': mesh.get_path_name(),
    'slots': [{'slot': str(s.get_editor_property('material_slot_name')),
               'material': s.get_editor_property('material_interface').get_path_name()
               if s.get_editor_property('material_interface') else None}
              for s in mesh.get_editor_property('static_materials')],
    'nanite': bool(mesh.get_editor_property('nanite_settings').enabled),
}

for name in SLOTS:
    path = '%s/Materials/M_BlastFurnace_%s' % (ROOT, name)
    material = u.load_asset(path)
    if material is None:
        report['materials'][name] = {'loaded': False,
                                     'exists_on_disk': u.EditorAssetLibrary.does_asset_exist(path)}
        continue
    entry = {'class': material.get_class().get_name(), 'textures': {}}
    # These are base Materials, not MaterialInstances: the texture references
    # live on the TextureSampleParameter2D expressions, not on the asset.
    for item in u.MaterialEditingLibrary.get_material_expressions(material) or []:
        if item.get_class().get_name() != 'MaterialExpressionTextureSampleParameter2D':
            continue
        label = str(item.get_editor_property('parameter_name'))
        value = item.get_editor_property('texture')
        entry['textures'][label] = value.get_path_name() if value else None
    for label in entry['textures']:
        report['textures'].setdefault(label, texture_row(entry['textures'][label]))
    report['materials'][name] = entry

# Also the raw texture assets, independent of the materials.
for name in SLOTS:
    for channel in CHANNELS:
        path = '%s/Textures/T_BlastFurnace_%s_%s' % (ROOT, name, channel)
        if path not in report['textures']:
            report['textures'][path] = texture_row(path)

(HERE := Path(__file__).resolve().parent, (HERE / 'untextured-diagnose.json').write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8'))

broken = []
for label, row in report['textures'].items():
    if not row.get('loaded'):
        broken.append('missing %s' % label)
    elif row.get('placeholder'):
        broken.append('placeholder %s (%s)' % (label, row['size']))
print('UNTEXTURED_DIAGNOSE ' + json.dumps({
    'mesh_slots': report['mesh']['slots'],
    'materials_loaded': {k: (v.get('loaded', False)) for k, v in report['materials'].items()},
    'texture_count': len(report['textures']),
    'broken': broken[:8]}, ensure_ascii=False), flush=True)
