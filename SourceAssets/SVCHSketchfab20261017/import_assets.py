"""Import the SVCh viewmodel and bind one WS1 material per semantic part.

The UE FBX importer merges the seven source objects into one skeletal mesh and
re-sorts the material slots by name, so slot order and slot names cannot be used
to tell the arms from the weapon. Identification is therefore geometric: the
weapon is rigid-bound to the WPN_* bones (one bone per vertex at weight 1.0)
while the arms are smoothly skinned to the hand/arm bones. Each slot's triangles
are classified by the bone that drives them, which is exact and re-runnable.

Headless; no editor is opened. Re-running replaces the assets in place.
"""
import json
import re
from pathlib import Path

import unreal as u

O = Path(__file__).parent
ROOT = '/Game/Weapons/SVCH/Integrated20261017'
MATROOT = ROOT + '/Materials'
PRESET_PATH = '/Game/Weapons/WeaponSurface/Presets/'
DONOR = '/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock'
FBX = O / 'Exports' / 'SK_SVCH_Manny.fbx'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary
MEL = u.MaterialEditingLibrary

auth = json.loads((O / 'Authoring' / 'authoring.json').read_text(encoding='utf-8'))
# Part -> (WS1 preset, slot name). The SVCh is a steel receiver with polymer
# furniture, so the Clean metal group is the default finish (WS1).
PRESET = {
    'Body':           ('MI_WS_CleanSatinSteel',    'SVCH_Body'),
    'Magazine':       ('MI_WS_CleanPolymer',       'SVCH_Magazine'),
    'BoltCarrier':    ('MI_WS_CleanPolishedSteel', 'SVCH_BoltCarrier'),
    'ChargingHandle': ('MI_WS_CleanPolishedSteel', 'SVCH_ChargingHandle'),
    'MagRelease':     ('MI_WS_CleanAnodized',      'SVCH_MagRelease'),
    'Selector':       ('MI_WS_CleanAnodized',      'SVCH_Selector'),
    'Cartridge':      ('MI_WS_CleanPolishedSteel', 'SVCH_Cartridge'),
}
# Which WPN_* bone each rigid part rides.
BONE_PART = {
    'WPN_root': 'Body',
    'WPN_SOCKET_Magazine': 'Magazine',
    'WPN_ChargingHandle': 'BoltCarrier',
    'WPN_Trigger': 'Body',
}
RP = O / 'Receipts' / 'import.json'
RP.parent.mkdir(exist_ok=True)
receipt = {'stage': 'importing', 'root': ROOT, 'saved': [], 'runtime_tested': False}


def record():
    RP.write_text(json.dumps(receipt, indent=1), encoding='utf-8')


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('save failed ' + asset.get_path_name())
    p = asset.get_path_name()
    if p not in receipt['saved']:
        receipt['saved'].append(p)
    record()
    return asset


def load(path):
    a = u.load_asset(path)
    if not a:
        raise RuntimeError('missing asset ' + path)
    return a


def pick(result, cls):
    for part in (result if isinstance(result, tuple) else (result,)):
        if isinstance(part, cls):
            return part
    raise RuntimeError('missing ' + cls.__name__)


if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is running; preserve the session.')

# Import into a throwaway name, then swap it in.
#
# Re-importing over SK_SVCH_Manny does not give a clean object: the importer
# merges the incoming material list into the previous asset, so an 8-material
# FBX ended up as a 14-slot mesh whose render sections were indexed against the
# old array. Deleting first is not enough either -- the old object stays alive
# until GC and still gets merged. A brand-new asset name is the only reliable
# way to get the authored slot list back.
FINAL = ROOT + '/SK_SVCH_Manny'
TEMP = ROOT + '/SK_SVCH_Manny_Import'
if E.does_asset_exist(TEMP):
    if not E.delete_asset(TEMP):
        raise RuntimeError('cannot clear the staging import asset')

# Use the default (Interchange) FBX path. The legacy path was selected by a
# console flag during the first import, and it appends six empty material slots:
# an 8-material FBX lands as 14 slots whose render sections no longer line up
# with the geometry ids, which is what broke the earlier material binding.

skeleton = load('/Game/Weapons/M4HK416Replica/SK_M4_HK416_Skeleton')
opt = u.FbxImportUI()
opt.automated_import_should_detect_type = False
opt.mesh_type_to_import = u.FBXImportType.FBXIT_SKELETAL_MESH
opt.import_as_skeletal = True
opt.import_mesh = True
opt.import_animations = False
opt.import_materials = False
opt.import_textures = False
opt.create_physics_asset = False
opt.skeleton = skeleton
opt.skeletal_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
task = u.AssetImportTask()
task.filename = str(FBX).replace('\\', '/')
task.destination_path = ROOT
task.destination_name = 'SK_SVCH_Manny_Import'
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = True
task.options = opt
task.factory = u.FbxFactory()
A.import_asset_tasks([task])


# Swap the staged import into place.
mesh = u.load_asset(TEMP)
if not mesh:
    raise RuntimeError('staged import is missing: ' + TEMP)
E.save_loaded_asset(mesh, only_if_is_dirty=False)
if not isinstance(mesh, u.SkeletalMesh):
    raise RuntimeError('staged skeletal import failed')
# delete_asset reports success but the package still answers does_asset_exist
# (a redirector survives it), so the destination never frees up for a rename.
# Move the old asset out of the way, then drop it.
RETIRED = ROOT + '/SK_SVCH_Manny_Retired'
if E.does_asset_exist(RETIRED):
    E.delete_asset(RETIRED)
if E.does_asset_exist(FINAL) and not E.rename_asset(FINAL, RETIRED):
    raise RuntimeError('cannot move the previous imported mesh aside')
if E.does_asset_exist(RETIRED):
    E.delete_asset(RETIRED)
if not E.rename_asset(TEMP, FINAL):
    raise RuntimeError('cannot move the staged import onto ' + FINAL)
mesh = u.load_asset(FINAL)
if not isinstance(mesh, u.SkeletalMesh):
    raise RuntimeError('skeletal import failed')
if mesh.skeleton != skeleton:
    raise RuntimeError('imported mesh lost the shared Manny skeleton')
receipt['imported_slot_count'] = len(mesh.get_editor_property('materials'))
receipt['mesh'] = mesh.get_path_name()
receipt['skeleton'] = mesh.skeleton.get_path_name()

editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
settings = editor.get_lod_build_settings(mesh, 0)
settings.use_full_precision_u_vs = True
settings.use_high_precision_tangent_basis = True
settings.recompute_normals = False
editor.set_lod_build_settings(mesh, 0, settings)

# ---------------------------------------------------- identify by bone
AU, Q, LU, MAT, BW = (u.GeometryScript_AssetUtils, u.GeometryScript_MeshQueries,
                      u.GeometryScript_List, u.GeometryScript_Materials,
                      u.GeometryScript_BoneWeights)
dm = u.DynamicMesh()
AU.copy_mesh_from_skeletal_mesh(mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(),
                                u.GeometryScriptMeshReadLOD())
ids = LU.convert_index_list_to_array(pick(MAT.get_all_triangle_material_i_ds(dm),
                                          u.GeometryScriptIndexList))
tris = LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm, True),
                                              u.GeometryScriptTriangleList))
tri_ids = LU.convert_index_list_to_array(pick(Q.get_all_triangle_i_ds(dm),
                                              u.GeometryScriptIndexList))
compact = not Q.get_has_triangle_id_gaps(dm)
mat_of_tri = [int(i) for i in ids][:len(tris)] if compact else [int(ids[t]) for t in tri_ids]

info = BW.get_all_bones_info(dm)
bones_info = None
for part in (info if isinstance(info, tuple) else (info,)):
    if type(part).__name__ != 'DynamicMesh':
        bones_info = part
bone_names = [str(bones_info[i].get_editor_property('name')) for i in range(len(bones_info))]
nverts = len(Q.get_all_vertex_positions(dm, True)[1]) if False else None
pos = LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm, True),
                                           u.GeometryScriptVectorList))
dom = []
for vi in range(len(pos)):
    got = BW.get_vertex_bone_weights(dm, vi)
    arr = None
    for part in (got if isinstance(got, tuple) else (got,)):
        if type(part).__name__ != 'DynamicMesh' and not isinstance(part, bool):
            arr = part
    best, bw = -1, -1.0
    if arr is not None:
        for k in range(len(arr)):
            w = float(arr[k].get_editor_property('weight'))
            if w > bw:
                bw = w
                best = int(arr[k].get_editor_property('bone_index'))
    dom.append(bone_names[best] if best >= 0 else '')

# A triangle belongs to the weapon when all three of its vertices are rigid on
# one WPN_* bone; the arms are skinned across many arm bones.
def tri_bone(t):
    names = {dom[t.x], dom[t.y], dom[t.z]}
    if len(names) == 1:
        nm = next(iter(names))
        if nm in BONE_PART:
            return nm
    return None


# Several rigid parts share WPN_root (body, selector, mag release, cartridges),
# so the bone narrows the candidate set and the authored triangle count picks
# the part. Both are exact, so the mapping is unambiguous and re-runnable.
RIGID_ON_ROOT = ('Body', 'Selector', 'MagRelease', 'Cartridge')
slot_candidates = {}
for ti, t in enumerate(tris):
    b = tri_bone(t)
    if b:
        slot_candidates.setdefault(mat_of_tri[ti], {}).setdefault(b, 0)
        slot_candidates[mat_of_tri[ti]][b] += 1
receipt['slot_bones'] = {str(k): v for k, v in sorted(slot_candidates.items())}

part_faces = {k: v['faces'] for k, v in auth['parts'].items()}
by_count = {}
for part, faces in part_faces.items():
    by_count.setdefault(faces, []).append(part)

slot_part = {}
for slot_id, per_bone in slot_candidates.items():
    total = sum(per_bone.values())
    bones = set(per_bone)
    if bones <= {'WPN_root'}:
        cands = by_count.get(total, [])
    elif bones == {'WPN_SOCKET_Magazine'}:
        cands = ['Magazine'] if total == part_faces['Magazine'] else []
    elif bones == {'WPN_ChargingHandle'}:
        cands = ['BoltCarrier'] if total == part_faces['BoltCarrier'] else []
    elif bones == {'WPN_Trigger'}:
        cands = ['Body'] if total == part_faces['Body'] else []
    else:
        cands = []
    if len(cands) != 1:
        raise RuntimeError('slot %d (bones %s, %d tris) is ambiguous: %s'
                           % (slot_id, sorted(bones), total, cands))
    slot_part[slot_id] = cands[0]
receipt['slot_part'] = {str(k): v for k, v in sorted(slot_part.items())}
weapon_faces = sum(part_faces[p] for p in slot_part.values())

slots = list(mesh.get_editor_property('materials'))
# The legacy FBX path (Interchange disabled) appends six empty slots, so the
# array is longer than the FBX's material list and the render sections are
# indexed against the array, not against the compacted ids Geometry Script
# returns. The slots still carrying an FBX material name are the real ones,
# in render-section order; everything else is importer padding.
used_abs = [i for i, s in enumerate(slots)
            if str(s.material_slot_name).startswith(('SM_SVCH_', 'MI_Manny_'))]
if len(used_abs) != len(auth['parts']) + 2:
    raise RuntimeError('found %d named material slots (%s), expected %d'
                       % (len(used_abs), used_abs, len(auth['parts']) + 2))
ordinal_of_abs = {abs_i: ord_i for ord_i, abs_i in enumerate(used_abs)}

arms_material = None
for s in load(DONOR).get_editor_property('materials'):
    if str(s.material_slot_name) == 'MI_Manny_01':
        arms_material = s.material_interface
if not arms_material:
    raise RuntimeError('cannot read the donor arm material')

made = {}
receipt['slots'] = []
arms_slots = 0
for i, slot in enumerate(slots):
    if i not in ordinal_of_abs:
        receipt['slots'].append({'i': i, 'tris': 0, 'action': 'importer padding'})
        continue
    ord_i = ordinal_of_abs[i]
    slot_total = sum(1 for m in mat_of_tri if m == ord_i)
    if slot_total == 0:
        slot.material_interface = None
        slot.material_slot_name = 'SVCH_Unused_%d' % i
        slots[i] = slot
        receipt['slots'].append({'i': i, 'tris': 0, 'action': 'unused'})
        continue
    part = slot_part.get(ord_i)
    if part is None:
        # No rigid WPN_* triangle in this slot: it is the arms' V9 skin.
        slot.material_interface = arms_material
        slot.material_slot_name = 'MI_Manny_%02d' % (arms_slots + 1)
        slots[i] = slot
        arms_slots += 1
        receipt['slots'].append({'i': i, 'tris': slot_total, 'source': 'V9 arms',
                                 'material': arms_material.get_path_name()})
        continue
    preset, label = PRESET.get(part, PRESET['Body'])
    if part in made:
        inst = made[part]
    else:
        path = MATROOT + '/MI_SVCH_' + part
        parent = load(PRESET_PATH + preset)
        inst = u.load_asset(path)
        if not inst:
            inst = A.create_asset('MI_SVCH_' + part, MATROOT, u.MaterialInstanceConstant,
                                  u.MaterialInstanceConstantFactoryNew())
        if not inst:
            raise RuntimeError('cannot create ' + path)
        MEL.set_material_instance_parent(inst, parent)
        E.set_metadata_tag(inst, 'SVCHSurfacePreset', preset)
        E.set_metadata_tag(inst, 'SVCHPart', part)
        E.set_metadata_tag(inst, 'Attribution',
                           'SVCh 308 model by TastyTony (Sketchfab '
                           '739390f40fef4b22ac9a71b72f7a95b8), CC BY 4.0; surface rebuilt on the '
                           'project weapon surface standard')
        save(inst)
        made[part] = inst
    slot.material_interface = inst
    slot.material_slot_name = label
    slots[i] = slot
    receipt['slots'].append({'i': i, 'tris': slot_total, 'part': part, 'slot': label,
                             'material': inst.get_path_name(), 'preset': preset})

if arms_slots != 2:
    raise RuntimeError('expected two arm slots, found %d' % arms_slots)
missing = set(auth['parts']) - set(made)
if missing:
    raise RuntimeError('parts without a bound slot: %s' % sorted(missing))

mesh.set_editor_property('materials', slots)
save(mesh)
# The skeleton is shared with every other viewmodel and is not modified here;\n# saving it is neither needed nor reliable from a commandlet.\n

receipt['stage'] = 'saved'
receipt['completed'] = True
record()
print('SVCH_IMPORT', json.dumps({'mesh': receipt['mesh'], 'slots': len(slots),
                                 'bound': sorted(made), 'saved': len(receipt['saved'])}),
      flush=True)
