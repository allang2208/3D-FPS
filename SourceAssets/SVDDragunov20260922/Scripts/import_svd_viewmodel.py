"""Import the SVD viewmodel as a skeletal mesh bound to the existing M4 skeleton.

Follows the project's own skeletal-import pattern (opt.skeleton = <existing mesh>.skeleton):
the new mesh has to ride the shared Manny arms and WPN_* bones, so it must NOT bring its
own skeleton. Arms material slots are copied from the running M4 viewmodel so the hands
keep the accepted appearance; the eight SVD slots get their material instances.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / 'Config' / 'import_spec.json').read_text(encoding='utf-8-sig'))
BASE = SPEC['content_root']
M4_MESH = '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'
FBX = ROOT / 'Authored' / 'SK_SVD_Manny.fbx'
MESH_NAME = 'SK_SVD_Manny'

E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Different project: %s' % u.Paths.project_dir())
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Preserve running play session')
if not FBX.exists():
    raise RuntimeError('missing rigged FBX: %s' % FBX)

receipt_path = ROOT / 'Receipts' / 'viewmodel_import.json'
receipt = {'stage': 'importing', 'fbx': str(FBX), 'target_skeleton_from': M4_MESH}

m4 = u.load_asset(M4_MESH)
if not isinstance(m4, u.SkeletalMesh):
    raise RuntimeError('M4 viewmodel not found: %s' % M4_MESH)
m4_skeleton = m4.skeleton
if m4_skeleton is None:
    raise RuntimeError('M4 viewmodel has no skeleton')
receipt['skeleton'] = m4_skeleton.get_path_name().split('.')[0]

task = u.AssetImportTask()
task.filename = str(FBX).replace('\\', '/')
task.destination_path = BASE + '/Viewmodel'
task.destination_name = MESH_NAME
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal = True
options.import_mesh = True
options.import_animations = False
options.import_materials = False
options.import_textures = False
options.create_physics_asset = False
options.skeleton = m4_skeleton
# FbxSkeletalMeshImportData has no combine_meshes / import_uniform_scale here; the project's
# own skeletal imports only set the FbxImportUI-level options above.
task.options = options
task.factory = u.FbxFactory()
TOOLS.import_asset_tasks([task])

mesh = u.load_asset(BASE + '/Viewmodel/' + MESH_NAME)
if not isinstance(mesh, u.SkeletalMesh):
    raise RuntimeError('skeletal import failed: %s' % MESH_NAME)
receipt['imported'] = True
receipt['skeleton_used'] = mesh.skeleton.get_path_name().split('.')[0] if mesh.skeleton else None
receipt['skeleton_matches_m4'] = bool(mesh.skeleton and mesh.skeleton == m4_skeleton)

# material mapping: arms slots keep the M4's accepted materials, SVD slots get their own.
# USkeletalMesh exposes material slots as the `materials` struct array; each SkeletalMaterial
# carries `material_interface`, which is written back through set_editor_property. The
# subsystem has no set_material (probed: only overlay/lod helpers).
m4_slots = list(m4.get_editor_property('materials'))
m4_materials = {}
for slot in m4_slots:
    material = slot.get_editor_property('material_interface')
    m4_materials[str(slot.get_editor_property('material_slot_name'))] = material

slots = list(mesh.get_editor_property('materials'))
assigned = []
for index, slot in enumerate(slots):
    name = str(slot.get_editor_property('material_slot_name'))
    target = None
    source = None
    for part in sorted(SPEC['parts'], key=lambda p: -len(p['part_name'])):
        # longest name first: 'Body' is a substring of 'ScopeBody' and stole its slot
        if part['part_name'].lower() in name.lower().replace('_', ''):
            target = u.load_asset(BASE + '/Materials/MI_SVD_' + part['part_name'])
            source = 'svd'
            break
    if target is None:
        for m4_name, m4_mat in m4_materials.items():
            if m4_name.lower() in name.lower() or name.lower() in m4_name.lower():
                target = m4_mat
                source = 'm4_arms'
                break
    if target is None and index < len(m4_slots):
        target = m4_slots[index].get_editor_property('material_interface')
        source = 'm4_by_index'
    if target is None:
        assigned.append({'slot': name, 'material': None, 'source': 'unmapped'})
        continue
    slot.set_editor_property('material_interface', target)
    assigned.append({'slot': name, 'material': target.get_path_name().split('.')[0], 'source': source})
mesh.set_editor_property('materials', slots)

receipt['material_slots'] = assigned
if not E.save_loaded_asset(mesh, False):
    raise RuntimeError('skeletal mesh save failed')
receipt['stage'] = 'saved'
receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')
print('VIEWMODEL_IMPORT ' + json.dumps(receipt, default=str))
