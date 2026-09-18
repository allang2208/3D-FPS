"""Install the arc-tube extended magazines (round 7) into UE.

Replaces the official assets with the `_arc` builds from
`Scripts/build_extmag_arc_tube.py`, binds each one to its own rifle's magazine
slot material and writes `install_extmag_arc_receipt.json`.

Run with the editor closed:
  UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>

The running editor's MCP asset tools refuse delete/duplicate/replace on these
assets (their existence check reports false while the assets load fine), so this
script is the install route: UE's own import task replaces the asset in place,
which keeps the C++ soft paths and the icons working unchanged.
"""
import json
import sys
from pathlib import Path

import unreal as u

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'

JOBS = {
    'SM_ExtMag_M440': dict(
        fbx='SM_ExtMag_M440_arc.fbx',
        host='/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
        slot='Magazine_Light_001',
        rifle='M4'),
    'SM_ExtMag_QBZ40': dict(
        fbx='SM_ExtMag_QBZ40_arc.fbx',
        host='/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny',
        slot='M_QBZ191_Wear_Magazine',
        rifle='QBZ191'),
}

report = {}
for name, cfg in JOBS.items():
    task = u.AssetImportTask()
    task.filename = str(O / 'FBX' / cfg['fbx'])
    task.destination_path = D
    task.destination_name = name
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_materials = False
    options.import_textures = False
    options.import_animations = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.convert_scene_unit = False
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

    mesh = u.load_asset(D + '/' + name)
    if not mesh:
        report[name] = 'MESH MISSING after import'
        continue
    host = u.load_asset(cfg['host'])
    material = None
    if host:
        for entry in host.get_editor_property('materials'):
            if str(entry.material_slot_name) == cfg['slot']:
                material = entry.material_interface
    if not material:
        report[name] = 'FAILED host slot %s not found' % cfg['slot']
        continue
    slots = mesh.get_editor_property('static_materials')
    for index, slot in enumerate(slots):
        slot.material_interface = material
        slots[index] = slot
    mesh.set_editor_property('static_materials', slots)
    bounds = mesh.get_bounds()
    saved = u.EditorAssetLibrary.save_loaded_asset(mesh, False)
    report[name] = {
        'fbx': cfg['fbx'],
        'rifle': cfg['rifle'],
        'material': material.get_path_name(),
        'material_slot': cfg['slot'],
        'size_cm': [round((bounds.box_extent * 2).x, 3),
                    round((bounds.box_extent * 2).y, 3),
                    round((bounds.box_extent * 2).z, 3)],
        'saved': bool(saved),
    }

(O / 'install_extmag_arc_receipt.json').write_text(
    json.dumps(report, indent=2, default=str), encoding='utf-8')
u.log('EXTMAG_ARC_INSTALL ' + json.dumps(report))
