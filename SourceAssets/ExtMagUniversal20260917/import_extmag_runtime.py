"""Import the per-rifle extended magazines in their socket-frame pose.

Each mesh is authored in its own rifle's WPN_SOCKET_Magazine frame, so the
runtime seat is identity and the installed angle comes from the factory
assembly instead of a fitted rake. Material slots are carried over from the
source (weapon-finish.md keeps slot names and order; the per-rifle finish is a
separate pass).

The seat's *scale* is not identity: the M4 viewmodel is a centimetre frame
(relative scale 1) while the AKM/QBZ viewmodels inherit the FBX x100 scale on
WPN_root and are metre frames (relative scale 0.01). M4DrumVisual.cpp derives
that factor from the runtime socket, so what matters here is only that each
mesh imports at real centimetres - the receipt below records the measured
bounds so a bad unit conversion cannot pass unnoticed again.

Every run writes import_extmag_receipt.json next to this script. A UE log line is
not evidence: the 2026-09-18 round lost the QBZ re-import to a silent save
failure while the editor held the project.

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
from pathlib import Path

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'
A = u.AssetToolsHelpers.get_asset_tools()
report = {}

JOBS = [('SM_ExtMag_QBZ40', 'SM_ExtMag_QBZ40_inframe.fbx'),
        ('SM_ExtMag_M440', 'SM_ExtMag_M440_inframe.fbx'),
        ('SM_ExtMag_AKM40', 'SM_ExtMag_AKM40_inframe.fbx')]

for name, fbx in JOBS:
    source = O / 'FBX' / fbx
    if not source.exists():
        report[name] = 'FBX MISSING ' + str(source)
        continue
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
    task.filename = str(source)
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
    # BoxExtent is a half extent; the AOI wants the real size. A magazine here is
    # 19-27 cm long. Anything outside 15-40 cm means the FBX unit conversion went
    # wrong, which is exactly the failure that produced a 2 mm magazine in the
    # 2026-09-17 round.
    size = [b.box_extent.x * 2, b.box_extent.y * 2, b.box_extent.z * 2]
    longest = max(size)
    verdict = 'OK' if 15.0 <= longest <= 40.0 else 'SUSPECT_UNIT longest=%.2fcm' % longest
    saved = u.EditorAssetLibrary.save_loaded_asset(mesh, False)
    report[name] = {
        'fbx': fbx,
        'saved': bool(saved),
        'slot_count': len(mesh.get_editor_property('static_materials')),
        'slots': [str(s.material_slot_name) for s in mesh.get_editor_property('static_materials')],
        'size_cm': [round(v, 2) for v in size],
        'bounds_center_cm': [round(b.origin.x, 2), round(b.origin.y, 2), round(b.origin.z, 2)],
        'unit_verdict': verdict,
    }

(O / 'import_extmag_receipt.json').write_text(json.dumps(report, indent=2, default=str))
u.log('EXTMAG_RUNTIME_IMPORT ' + json.dumps(report))
