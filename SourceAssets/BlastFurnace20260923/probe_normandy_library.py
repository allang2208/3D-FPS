"""Read-only probe of the UnrealNormandy material library, plus a PNG export.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

Answers what the project already owns before any material swap:

1. which master material each candidate instance uses;
2. which textures each one samples, and at what source size / compression;
3. what scalar and vector knobs it exposes.

It also exports the underlying texture sets to PNG under
``Saved/BlastFurnace20260923/NormandyPNG`` so the Blender preview can show the
real library maps instead of my procedural ones. Nothing in the project is
modified; every introspection is guarded so one odd struct cannot lose the
export.
"""
import json
from pathlib import Path

import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923')
PNG = OUT / 'NormandyPNG'
PNG.mkdir(parents=True, exist_ok=True)

CANDIDATES = [
    '/Game/UnrealNormandy/MaterialInstances/MI_Bricks_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_BrickWall_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_BrickWall_Chunks_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00B_Gray',
    '/Game/UnrealNormandy/MaterialInstances/MI_StoneWall_Pieces_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_StoneWall_Pieces_00C_NoDirt',
    '/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_Slate_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_Rock_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_RustyMetal_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_Enbankment_00A',
    '/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A',
]

TEXTURE_SETS = [
    'T_HB_Wall4x4_00A', 'T_HB_Wall4x4_01A', 'T_Mortar_00A',
    'T_StoneSurface_00A', 'T_StoneSurface_01A', 'T_StoneSurface_02A', 'T_StoneSurface_03A',
    'T_StoneSurface_DetailNormal_00A',
    'T_MetalRust_00A', 'T_SoilSurface_02A', 'T_SoilSurface_04A',
    'T_CliffSurface_02A', 'T_CliffSurface_03A',
    'T_LC_RockBasaltLichen_00A', 'T_LC_BasaltCliff_00A', 'T_LC_BasaltCliffCracked_00A',
    'T_LC_GroundSoilExcavated_00A', 'T_LC_MossyGravel_00A', 'T_LC_GroundDry_00A',
    'T_RottenWoodSurface_00A', 'T_WoodSurface_00A', 'T_ST_Rubbish_00A',
]
SUFFIXES = ('BaseColor', 'Albedo', 'Normal', 'RHAOM', 'Height', 'Masks', 'ORM')

report = {'material_instances': {}, 'texture_sets': {}, 'exported_png': [],
          'export_error': None, 'struct_probe': {}}


def texture_info(tex):
    if tex is None:
        return None
    return {'path': tex.get_path_name(),
            'size': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()],
            'srgb': bool(tex.get_editor_property('srgb')),
            'compression': str(tex.get_editor_property('compression_settings'))}


def struct_fields(item):
    """Introspect a parameter struct without assuming its property names."""
    fields = {}
    for name in dir(item):
        if name.startswith('_') or name in ('get_class', 'get_editor_property', 'set_editor_property',
                                            'cast', 'get_full_name', 'get_name', 'get_path_name'):
            continue
        try:
            value = item.get_editor_property(name)
        except Exception:  # noqa: BLE001 - keep walking the struct
            continue
        if callable(value) or isinstance(value, type):
            continue
        fields[name] = value
    return fields


def probe_instance(path):
    asset = u.load_asset(path)
    if asset is None:
        return {'missing': True}
    parent = asset.get_editor_property('parent')
    entry = {'parent': parent.get_path_name() if parent else None,
             'class': asset.get_class().get_name(),
             'textures': {}, 'scalars': {}, 'vectors': {}}
    for kind, bucket in (('texture_parameter_values', 'textures'),
                         ('scalar_parameter_values', 'scalars'),
                         ('vector_parameter_values', 'vectors')):
        try:
            items = asset.get_editor_property(kind)
        except Exception as error:  # noqa: BLE001
            entry.setdefault('errors', []).append('%s: %s' % (kind, error))
            continue
        for item in items or []:
            fields = struct_fields(item)
            if not report['struct_probe']:
                report['struct_probe'][kind] = {
                    name: type(value).__name__ for name, value in fields.items()}
            label = next((value for name, value in fields.items()
                          if 'name' in name.lower() and isinstance(value, str)),
                         next((str(value) for name, value in fields.items()
                               if 'name' in name.lower()), None))
            value = next((value for name, value in fields.items() if 'value' in name.lower()), None)
            if label is None or value is None:
                continue
            if bucket == 'textures':
                entry['textures'][label] = texture_info(value)
            elif bucket == 'scalars':
                entry['scalars'][label] = value
            else:
                try:
                    entry['vectors'][label] = [round(c, 4) for c in
                                               (value.r, value.g, value.b, value.a)]
                except Exception:  # noqa: BLE001
                    entry['vectors'][label] = str(value)
    return entry


for path in CANDIDATES:
    report['material_instances'][path] = probe_instance(path)

for family in TEXTURE_SETS:
    entry = {}
    for suffix in SUFFIXES:
        asset = u.load_asset('/Game/UnrealNormandy/Textures/%s_%s' % (family, suffix))
        if asset:
            entry[suffix] = texture_info(asset)
    report['texture_sets'][family] = entry or {'missing': True}

# --- export the maps so Blender can preview the real library ------------
wanted = set()
for entry in report['texture_sets'].values():
    for info in entry.values():
        if isinstance(info, dict) and info.get('path'):
            wanted.add(info['path'].split('.')[0])

for asset_path in sorted(wanted):
    texture = u.load_asset(asset_path)
    if texture is None:
        continue
    target = PNG / (texture.get_name() + '.png')
    if target.exists():
        report['exported_png'].append(str(target))
        continue
    try:
        task = u.AssetExportTask()
        task.set_editor_property('object', texture)
        task.set_editor_property('filename', str(target))
        task.set_editor_property('automated', True)
        task.set_editor_property('prompt', False)
        task.set_editor_property('replace_identical', True)
        task.set_editor_property('exporter', u.TextureExporter())
        if u.Exporter.run_asset_export_task(task) and target.exists():
            report['exported_png'].append(str(target))
    except Exception as error:  # noqa: BLE001 - the probe must not fail hard
        report['export_error'] = '%s: %s' % (asset_path, error)

(OUT / 'normandy_probe.json').write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                                    default=str), encoding='utf-8')
print('NORMANDY_PROBE ' + json.dumps({
    'instances': len(report['material_instances']),
    'texture_sets': len(report['texture_sets']),
    'exported_png': len(report['exported_png']),
    'export_error': report['export_error'],
    'struct_probe': report['struct_probe']}, ensure_ascii=False, default=str), flush=True)
