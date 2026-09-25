"""Rebuild Bow field gloves from the current M4 fitted-glove mesh."""
import json
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
CONFIG = PROJECT/'Content/ColdSteelData/modular_outfits.json'
RECEIPT = PROJECT/'SourceAssets/DarkBow20260925/ArmsV4/outfit_receipt.json'
DEST = '/Game/Weapons/DarkBow20260925/ArmsV4'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils
Q = u.GeometryScript_MeshQueries
B = u.GeometryScript_BoneWeights


def play_world():
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
    if not world:
        return None
    name = world.get_name()
    if 'UEDPIE' in name or name.startswith('UEDPIE') or 'PIE_' in name:
        return world
    return None


world = play_world()
if world:
    u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
    import time
    for _ in range(80):
        time.sleep(0.25)
        if not play_world():
            break
    else:
        raise RuntimeError('Finish play before saving Bow field gloves')

config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
source_profile = next(v for v in config['profiles'].values() if v['rig_profile'] == 'M4')
source = u.load_asset(source_profile['gloves'])
if not source:
    raise RuntimeError('Missing current M4 field gloves '+source_profile['gloves'])
bow = u.load_asset(DEST+'/SK_Bow_BareArmsV7')
if not bow:
    raise RuntimeError('Missing Bow bare arms')
native, status = G.copy_mesh_from_skeletal_mesh(
    bow, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read Bow skeleton')
_, bones = B.get_all_bones_info(native)
ids = {str(b.name): b.index for b in bones}

def rotate(p):
    return u.Vector(-p.y, p.x, p.z)

dm, status = G.copy_mesh_from_skeletal_mesh(
    source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot read M4 field gloves')
_, bones = B.get_all_bones_info(dm)
names = {b.index: str(b.name) for b in bones}
_, pos, _ = Q.get_all_vertex_positions(dm, False)
positions = u.GeometryScript_List.convert_vector_list_to_array(pos)
_, tris, _ = Q.get_all_triangle_indices(dm, False)
faces = u.GeometryScript_List.convert_triangle_list_to_array(tris)
used = {v for f in faces for v in (f.x, f.y, f.z)}
vertex_weights = {}
for i in used:
    _, weights, valid = B.get_vertex_bone_weights(dm, i)
    vertex_weights[i] = [u.GeometryScriptBoneWeight(bone_index=ids[names[w.bone_index]], weight=w.weight)
                         for w in weights if w.weight > 0]
vertices = []
normals = []
uvs = [[], [], [], []]
weights = []
triangles = []
mats = []
channels = min(4, Q.get_num_uv_sets(dm))
for i, f in enumerate(faces):
    base = len(vertices)
    _, a, b, c, valid = Q.get_triangle_normals(dm, i)
    normals.extend(rotate(v) for v in (a, b, c))
    for vi in (f.x, f.y, f.z):
        vertices.append(rotate(positions[vi]))
        weights.append(vertex_weights[vi])
    for ch in range(4):
        if ch < channels:
            a, b, c, valid = Q.get_triangle_u_vs(dm, ch, i)
            uvs[ch].extend((a, b, c))
        else:
            uvs[ch].extend([u.Vector2D(0, 0)] * 3)
    mats.append(u.GeometryScript_Materials.get_triangle_material_id(dm, i)[0])
    triangles.append(u.IntVector(base, base + 1, base + 2))
out = u.DynamicMesh()
u.GeometryScript_MeshEdits.append_buffers_to_mesh(
    out, u.GeometryScriptSimpleMeshBuffers(
        vertices=vertices, normals=normals, uv0=uvs[0], uv1=uvs[1], uv2=uvs[2], uv3=uvs[3],
        triangles=triangles), 0, True)
B.copy_bones_from_mesh(native, out)
B.mesh_create_bone_weights(out)
for i, w in enumerate(weights):
    B.set_vertex_bone_weights(out, i, w)
for i, m in enumerate(mats):
    u.GeometryScript_Materials.set_triangle_material_id(out, i, m, True)
name = 'SK_Bow_FieldGloves'
target = DEST+'/Outfits/'+name
asset = u.load_asset(target)
if not asset:
    asset = A.duplicate_asset(name, DEST+'/Outfits', bow)
brown = u.load_asset('/Game/Characters/ModularOutfit20260924/Materials/M_FieldGloves_Brown')
options = u.GeometryScriptCopyMeshToAssetOptions(
    replace_materials=True,
    new_materials=[brown or s.material_interface for s in source.materials],
    new_material_slot_names=[s.material_slot_name for s in source.materials],
    enable_recompute_normals=False, enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_, status = G.copy_mesh_to_skeletal_mesh(out, asset, options, u.GeometryScriptMeshWriteLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError('Cannot bind Bow field gloves')
if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()], False) or E.save_loaded_asset(asset, False)):
    raise RuntimeError('Cannot save Bow field gloves')
saved = {}
if RECEIPT.exists():
    saved = json.loads(RECEIPT.read_text(encoding='utf-8')).get('saved', {})
saved['FieldGloves'] = asset.get_path_name()
RECEIPT.write_text(json.dumps({'saved': saved, 'runtime_tested': False}, indent=2) + '\n', encoding='utf-8')
print('BOW_FIELD_GLOVES_REBOUND', asset.get_path_name(), flush=True)
