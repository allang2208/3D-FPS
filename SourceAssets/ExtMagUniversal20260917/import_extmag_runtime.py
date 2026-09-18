"""Import the per-rifle extended magazines in their socket-frame pose.

Each mesh is authored in its own rifle's WPN_SOCKET_Magazine frame, so the
runtime seat is identity and the installed angle comes from the factory
assembly instead of a fitted rake. Material slots are carried over from the
source (weapon-finish.md keeps slot names and order; the per-rifle finish is a
separate pass).

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'
A = u.AssetToolsHelpers.get_asset_tools()
report = {}

JOBS = [('SM_ExtMag_QBZ40', 'SM_ExtMag_QBZ40.fbx'),
        ('SM_ExtMag_M440', 'SM_ExtMag_M440.fbx'),
        ('SM_ExtMag_AKM40', 'SM_ExtMag_AKM40.fbx')]

for name, fbx in JOBS:
    opt = u.FbxImportUI()
    opt.automated_import_should_detect_type = False
    opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_as_skeletal = False
    opt.import_mesh = True
    opt.import_animations = False
    opt.import_materials = False
    opt.import_textures = False
    opt.create_physics_asset = False
    opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    opt.static_mesh_import_data.normal_generation_method = u.FBXNormalGenerationMethod.MIKK_T_SPACE
    opt.static_mesh_import_data.convert_scene_unit = False
    opt.static_mesh_import_data.import_translation = u.Vector(0, 0, 0)
    opt.static_mesh_import_data.import_rotation = u.Rotator(0, 0, 0)
    opt.static_mesh_import_data.import_uniform_scale = 1.0
    opt.static_mesh_import_data.combine_meshes = True

    task = u.AssetImportTask()
    task.filename = str(O / 'FBX' / fbx)
    task.destination_path = D
    task.destination_name = name
    task.options = opt
    task.automated = True
    task.replace_existing = True
    task.save = False
    A.import_asset_tasks([task])

    mesh = u.load_asset(f'{D}/{name}')
    if not mesh:
        report[name] = 'IMPORT FAILED'
        continue
    b = mesh.get_bounds()
    report[name] = {
        'slots': [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')],
        'bounds_extent_cm': [round(b.box_extent.x, 2), round(b.box_extent.y, 2), round(b.box_extent.z, 2)],
        'bounds_origin_cm': [round(b.origin.x, 2), round(b.origin.y, 2), round(b.origin.z, 2)],
    }
    u.EditorAssetLibrary.save_loaded_asset(mesh, False)

u.log('EXTMAG_RUNTIME_IMPORT ' + json.dumps(report))
