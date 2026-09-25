"""Save native-bound fitted sleeves, then publish the two field-sweater recipes."""
import hashlib
import json
from pathlib import Path

import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/ModularOutfit20260925/FittedSleevesV1'
BARE = PROJECT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
DEST = '/Game/Characters/ModularOutfit20260924/FittedSleevesV1'
CONFIG = PROJECT/'Content/ColdSteelData/modular_outfits.json'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
G = u.GeometryScript_AssetUtils
B = u.GeometryScript_BoneWeights
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
RECEIPTS = ROOT/'Saved'
RECEIPTS.mkdir(parents=True, exist_ok=True)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play before saving fitted sleeve equipment')


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing sleeve dependency: '+path)
    return asset


def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save fitted sleeves: '+asset.get_path_name())


material = load('/Game/Characters/ModularOutfit20260924/Materials/M_FieldSweater_Olive')
initial = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
previous = {}
published = {}
manifest = json.loads((ROOT/'manifest.json').read_text())
for entry in manifest:
    name = entry['profile']
    raw = Path(entry['authored']).read_bytes()
    data = json.loads(raw)
    sha = hashlib.sha256(raw).hexdigest()
    profile = initial['profiles'][data['source']]
    if profile.get('native_bare_skin') != data['base_mesh'] or profile.get('shirt_covers') != [0,1]:
        raise RuntimeError('Bare hand base or coverage changed during fitting: '+name)
    if hashlib.sha256((BARE/'Authored'/f'{name}.json').read_bytes()).hexdigest() != data['bare_authored_sha256']:
        raise RuntimeError('Bare hand authoring changed during fitting: '+name)
    previous[name] = {'source': data['source'], 'profile_shirt': profile.get('shirt'),
                      'item_meshes': {key: initial['items'][key]['rig_meshes'].get(name)
                                      for key in ('ue_field_sweater', 'ue_field_sweater_charcoal')}}
    receipt_file = RECEIPTS/f'{name}.json'
    if receipt_file.exists():
        receipt = json.loads(receipt_file.read_text())
        if receipt['authored_sha256'] == sha and E.does_asset_exist(receipt['mesh']):
            published[name] = receipt['mesh']
            continue
    print('FITTED_SLEEVES_IMPORT_BEGIN', name, flush=True)
    source = load(data['binding_source'])
    native, status = G.copy_mesh_from_skeletal_mesh(source, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read native sleeve binding: '+name)
    _, bones = B.get_all_bones_info(native)
    bone_ids = {str(b.name): b.index for b in bones}
    vertices, normals, uv0, weights, triangles = [], [], [], [], []
    lookup = {}
    for fi, face in enumerate(data['triangles']):
        row = []
        for corner, vi in enumerate(face):
            uv = data['uv'][fi][corner]
            normal = data['normals'][fi][corner]
            key = (vi, *[round(v, 7) for v in (*uv, *normal)])
            if key not in lookup:
                lookup[key] = len(vertices)
                vertices.append(u.Vector(*data['positions'][vi]))
                normals.append(u.Vector(*normal))
                uv0.append(u.Vector2D(*uv))
                weights.append(data['weights'][vi])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm = u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm, u.GeometryScriptSimpleMeshBuffers(
        vertices=vertices, normals=normals, uv0=uv0, triangles=triangles), 0, True)
    _, built_triangles, _ = u.GeometryScript_MeshQueries.get_all_triangle_indices(dm, False)
    if len(u.GeometryScript_List.convert_triangle_list_to_array(built_triangles)) != len(triangles):
        raise RuntimeError('Sleeve assembly rejected triangles; no mesh or recipe saved: '+name)
    B.copy_bones_from_mesh(native, dm)
    B.mesh_create_bone_weights(dm)
    for vi, bindings in enumerate(weights):
        B.set_vertex_bone_weights(dm, vi, [u.GeometryScriptBoneWeight(bone_index=bone_ids[n], weight=w) for n, w in bindings.items()])
    folder = DEST+'/'+name
    mesh_name = 'SK_'+name+'_FittedSleevesV1'
    mesh = u.load_asset(folder+'/'+mesh_name)
    if not mesh:
        mesh = A.duplicate_asset(mesh_name, folder, source)
    options = u.GeometryScriptCopyMeshToAssetOptions(
        replace_materials=True, new_materials=[material], new_material_slot_names=['FittedSweaterFabric'],
        enable_recompute_normals=False, enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _, status = G.copy_mesh_to_skeletal_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD())
    if status != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot build fitted sleeve mesh: '+name)
    mesh.set_editor_property('physics_asset', None)
    build = S.get_lod_build_settings(mesh, 0)
    build.set_editor_property('use_full_precision_u_vs', True)
    S.set_lod_build_settings(mesh, 0, build)
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):
        raise RuntimeError('Cannot configure fitted sleeve LODs: '+name)
    if not S.regenerate_lod(mesh, 3, True, False):
        raise RuntimeError('Cannot build fitted sleeve LODs: '+name)
    E.set_metadata_tag(mesh, 'SourceContract', data['contract'])
    save(mesh)
    receipt = {'profile': name, 'mesh': mesh.get_path_name(), 'authored_sha256': sha,
               'base_mesh': data['base_mesh'], 'native_skeleton': data['skeleton'],
               'new_animations': 0, 'runtime_tested': False}
    receipt_file.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    published[name] = mesh.get_path_name()
    print('FITTED_SLEEVES_SAVED', name, mesh.get_path_name(), flush=True)

# Merge only this batch's mesh paths into the latest config; retain Body,
# original-glove recovery, glove meshes, item IDs, and unrelated concurrent work.
config = json.loads(CONFIG.read_text(encoding='utf-8-sig'))
for name, prior in previous.items():
    profile = config['profiles'][prior['source']]
    if profile.get('shirt') not in (prior['profile_shirt'], published[name]):
        raise RuntimeError('Sleeve profile changed during import: '+name)
    if profile.get('native_bare_skin') != initial['profiles'][prior['source']]['native_bare_skin']:
        raise RuntimeError('Bare hand base changed during import: '+name)
    profile['shirt'] = published[name]
    for key, old in prior['item_meshes'].items():
        meshes = config['items'][key]['rig_meshes']
        if meshes.get(name) not in (old, published[name]):
            raise RuntimeError('Equipment recipe changed during import: '+key+'/'+name)
        meshes[name] = published[name]
backup = ROOT/'previous-shirt-paths.json'
if not backup.exists():
    backup.write_text(json.dumps(previous, indent=2)+'\n', encoding='utf-8')
CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(ROOT/'published.json').write_text(json.dumps({'profiles': published, 'items': ['ue_field_sweater', 'ue_field_sweater_charcoal'],
    'runtime_tested': False, 'new_animations': 0}, indent=2)+'\n', encoding='utf-8')
print('FITTED_SLEEVES_PUBLISHED', len(published), flush=True)
