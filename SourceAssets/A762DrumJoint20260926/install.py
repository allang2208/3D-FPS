"""Import the new A762 tower, preserving the existing attachment identity.

A762_DRUM_STAGE_ONLY=1 writes only the independent candidate package. The final
install is run only when the project's game/editor is not holding the live asset,
or inside its existing editor through the project's mutex-protected bridge.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
P = O.parents[1]
LIVE = '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_drum'
CANDIDATE = '/Game/Weapons/A762/DrumJoint20260926/SM_A762_drum'
STAGE = os.environ.get('A762_DRUM_STAGE_ONLY') == '1'
TARGET = CANDIDATE if STAGE else LIVE
SOURCE = O / 'Exports/SM_A762_drum.fbx'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
receipt_path = O / ('candidate_receipt.json' if STAGE else 'install_receipt.json')

old = u.load_asset(LIVE)
rifle = u.load_asset('/Game/Weapons/A762/Integrated20260920/SK_A762_Manny')
if not old or not rifle:
    raise RuntimeError('The current A762 drum or rifle could not be loaded')
materials = {str(s.material_slot_name): s.material_interface for s in old.static_materials}
rifle_materials = {str(s.material_slot_name): s.material_interface for s in rifle.materials}
for new, source in [('A762_drum_Neck', 'M_A762_Magazine_Rebuilt'),
                    ('A762_drum_Inside', 'M_A762_MagazineInside_Rebuilt')]:
    materials[new] = rifle_materials[source]
    if not materials[new]:
        raise RuntimeError('Missing existing A762 finish ' + source)

disk = P / 'Content/Weapons/A762/Accessories05/Meshes/SM_A762_drum.uasset'
baseline_file = O / 'source_asset.json'
sha = hashlib.sha256(disk.read_bytes()).hexdigest()
if baseline_file.exists():
    baseline = json.loads(baseline_file.read_text(encoding='utf-8'))
    if sha != baseline['sha256'] and not receipt_path.exists():
        raise RuntimeError('Live drum package changed since source preparation; preserve it before continuing')
else:
    baseline = {'asset': LIVE, 'sha256': sha, 'bytes': disk.stat().st_size}
    baseline_file.write_text(json.dumps(baseline, indent=2), encoding='utf-8')

if not STAGE:
    backup = O / 'Before/SM_A762_drum.uasset'
    backup.parent.mkdir(exist_ok=True)
    if not backup.exists():
        shutil.copy2(disk, backup)

if STAGE and not E.does_asset_exist(CANDIDATE):
    target = E.duplicate_asset(LIVE, CANDIDATE)
    if not target:
        raise RuntimeError('Cannot create isolated drum candidate')
else:
    target = u.load_asset(TARGET)

# Reimport into the duplicate/current mesh so its existing LOD and Nanite policy
# survive. Only the geometry, new per-face bindings and source filename change.
nanite = target.get_editor_property('nanite_settings')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_as_skeletal = False
options.import_materials = False
options.import_textures = False
options.import_animations = False
options.set_editor_property('reset_to_fbx_on_material_conflict', True)
d = options.static_mesh_import_data
d.combine_meshes = True
d.auto_generate_collision = False
d.generate_lightmap_u_vs = False
d.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
d.vertex_color_import_option = u.VertexColorImportOption.REPLACE
task = u.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path, task.destination_name = TARGET.rsplit('/', 1)
task.options = options
task.factory = u.FbxFactory()
task.automated = True
task.replace_existing = True
task.replace_existing_settings = False
task.save = False
A.import_asset_tasks([task])
mesh = u.load_asset(TARGET)
if not mesh or not task.imported_object_paths:
    raise RuntimeError('FBX import did not produce the requested asset')
slots = list(mesh.static_materials)
for i, slot in enumerate(slots):
    name = str(slot.material_slot_name)
    if name not in materials:
        name = str(slot.get_editor_property('imported_material_slot_name'))
    if name not in materials:
        raise RuntimeError('Unmapped material slot ' + str(slot.material_slot_name))
    slot.material_interface = materials[name]
    slots[i] = slot
mesh.set_editor_property('static_materials', slots)
mesh.set_editor_property('nanite_settings', nanite)
E.set_metadata_tag(mesh, 'A762DrumRevision', '20260926: closed ordered tower loft; real seated magwell contour')
saved = bool(E.save_loaded_asset(mesh, False))
if not saved:
    raise RuntimeError('Failed to save ' + TARGET)
receipt = {'asset': mesh.get_path_name(), 'source': str(SOURCE), 'saved': saved,
           'stage_only': STAGE, 'runtime_asset_replaced': not STAGE,
           'source_asset_before': baseline,
           'slots': [{'slot': str(s.material_slot_name), 'material': s.material_interface.get_path_name()}
                     for s in mesh.static_materials],
           'existing_lod_and_nanite_policy': 'retained by duplicate/reimport; no policy override',
           'game_tested': False, 'acceptance_rendered': False}
receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('A762_DRUM_JOINT_SAVED', json.dumps(receipt), flush=True)

