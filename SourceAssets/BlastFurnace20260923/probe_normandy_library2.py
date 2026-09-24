"""What export machinery does this build expose, and what do the MIs sample?

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash
"""
import json
from pathlib import Path

import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/Saved/BlastFurnace20260923')
report = {}

report['export_related'] = sorted(n for n in dir(u)
                                  if 'export' in n.lower() or 'image' in n.lower())
report['texture_methods'] = sorted(n for n in dir(u.Texture2D) if not n.startswith('_'))[:80]

CANDIDATES = {
    'bricks': '/Game/UnrealNormandy/MaterialInstances/MI_Bricks_00A',
    'brick_wall': '/Game/UnrealNormandy/MaterialInstances/MI_BrickWall_00A',
    'brick_chunks': '/Game/UnrealNormandy/MaterialInstances/MI_BrickWall_Chunks_00A',
    'stone_wall': '/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00A',
    'stone_wall_gray': '/Game/UnrealNormandy/MaterialInstances/MI_Main_StoneWall_00B_Gray',
    'stone_pieces': '/Game/UnrealNormandy/MaterialInstances/MI_StoneWall_Pieces_00A',
    'mortar': '/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A',
    'slate': '/Game/UnrealNormandy/MaterialInstances/MI_Slate_00A',
    'rock': '/Game/UnrealNormandy/MaterialInstances/MI_Rock_00A',
    'rusty_metal': '/Game/UnrealNormandy/MaterialInstances/MI_RustyMetal_00A',
    'enbankment': '/Game/UnrealNormandy/MaterialInstances/MI_Enbankment_00A',
    'wood': '/Game/UnrealNormandy/MaterialInstances/MI_Wood_00A',
}
instances = {}
for key, path in CANDIDATES.items():
    asset = u.load_asset(path)
    if asset is None:
        instances[key] = {'missing': True}
        continue
    parent = asset.get_editor_property('parent')
    entry = {'path': path, 'parent': parent.get_path_name() if parent else None,
             'textures': {}, 'scalars': {}, 'vectors': {}}
    for kind, bucket in (('texture_parameter_values', 'textures'),
                         ('scalar_parameter_values', 'scalars'),
                         ('vector_parameter_values', 'vectors')):
        try:
            items = asset.get_editor_property(kind)
        except Exception as error:  # noqa: BLE001
            continue
        for item in items or []:
            info = item.get_editor_property('parameter_info')
            name = str(info.get_editor_property('name')) if info else '?'
            value = item.get_editor_property('parameter_value')
            if bucket == 'textures':
                entry['textures'][name] = value.get_path_name() if value else None
            elif bucket == 'scalars':
                entry['scalars'][name] = value
            else:
                try:
                    entry['vectors'][name] = [round(c, 4) for c in
                                              (value.r, value.g, value.b, value.a)]
                except Exception:  # noqa: BLE001
                    entry['vectors'][name] = str(value)
    instances[key] = entry
report['instances'] = instances

# Texture source sizes for the sets that matter here.
families = ['T_HB_Wall4x4_00A', 'T_HB_Wall4x4_01A', 'T_Mortar_00A',
            'T_StoneSurface_00A', 'T_StoneSurface_01A', 'T_StoneSurface_02A', 'T_StoneSurface_03A',
            'T_MetalRust_00A', 'T_SoilSurface_02A', 'T_SoilSurface_04A',
            'T_LC_GroundSoilExcavated_00A', 'T_LC_MossyGravel_00A', 'T_LC_GroundDry_00A']
sizes = {}
for family in families:
    row = {}
    for suffix in ('BaseColor', 'Albedo', 'Normal', 'RHAOM', 'Height'):
        tex = u.load_asset('/Game/UnrealNormandy/Textures/%s_%s' % (family, suffix))
        if tex:
            row[suffix] = {'size': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()],
                           'srgb': bool(tex.get_editor_property('srgb')),
                           'compression': str(tex.get_editor_property('compression_settings'))}
    sizes[family] = row or {'missing': True}
report['texture_sizes'] = sizes

(OUT / 'normandy_probe2.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str),
                                          encoding='utf-8')
print('NORMANDY_PROBE2 ' + json.dumps({
    'export_related': report['export_related'],
    'instances_ok': sum(1 for v in instances.values() if not v.get('missing'))}, ensure_ascii=False),
      flush=True)
