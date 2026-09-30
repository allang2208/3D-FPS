"""Save the F57 receiver-only triangle patch to the active 201 mesh."""
import unreal as u
import json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
CANDIDATE='/Game/Weapons/LMG201/FeedMouth57/SK_LMG201_FeedMouth57_Candidate'
S=json.loads((O/'source.json').read_text());removals=json.loads((O/'removals.json').read_text());author=json.loads((O/'authoring.json').read_text())
parts=json.load(gzip.open(O/'mesh_buffers.json.gz','rt'))
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;Q=u.GeometryScript_MeshQueries


def file(path):return P/'Content'/(path.removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(file(path).read_bytes()).hexdigest()
def preflight():
    if sha(BODY)!=S['sha256']:raise RuntimeError('Current body changed since F57 capture; retained')
    if BODY in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Unsaved body edits retained')
    sub=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if sub and sub.get_game_world():raise RuntimeError('PIE is active; no asset modified')


def copy_to(dm,asset,slots):
    opt=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,opt,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native mesh write failed '+asset.get_path_name())
    asset.materials=[s.copy() for s in slots]


def save(asset):
    E.set_metadata_tag(asset,'201FeedMouthRevision','FeedMouth57: local clearance for B53; capped thickness and rounded cut edges')
    E.set_metadata_tag(asset,'201FeedMouthSource',str(O/'LMG201_FeedMouth57.blend'))
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+asset.get_path_name())


preflight()
if E.does_asset_exist(CANDIDATE):raise RuntimeError('Existing F57 candidate retained; inspect prior receipt before retry')
body=u.load_asset(BODY);slots=[s.copy() for s in body.materials];names={str(s.material_slot_name):i for i,s in enumerate(slots)}
dm,status=G.copy_mesh_from_skeletal_mesh(body,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read current mesh')
_,bones=B.get_all_bones_info(dm);root=next(b.index for b in bones if str(b.name)=='WPN_root')
color_cache={}
for ti in {ti for row in parts for ti in row['color_source'] if ti>=0}:
    _,a,b,c,valid=Q.get_triangle_vertex_colors(dm,ti)
    color_cache[ti]=[[v.r,v.g,v.b,v.a] for v in (a,b,c)] if valid else [[1.,1.,1.,1.]]*3
u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,
    u.GeometryScript_List.convert_array_to_index_list(removals['remove_triangle_ids'],u.GeometryScriptIndexType.TRIANGLE),True)
for row in parts:
    colors=[]
    for ti,weights in zip(row['color_source'],row['color_bary']):
        if ti<0:colors.append(u.LinearColor(1,1,1,1));continue
        corners=color_cache[ti]
        colors.append(u.LinearColor(*[sum(corners[k][j]*weights[k] for k in range(3)) for j in range(4)]))
    added=u.DynamicMesh()
    buffers=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*v) for v in row['p']],
        normals=[u.Vector(*v) for v in row['n']],uv0=[u.Vector2D(*v) for v in row['uv']],
        triangles=[u.IntVector(*v) for v in row['t']],vertex_colors=colors)
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(added,buffers,names[row['slot']],True)
    B.copy_bones_from_mesh(dm,added,u.GeometryScriptCopyBonesFromMeshOptions(reindex_weights=False))
    B.mesh_create_bone_weights(added);B.set_all_vertex_bone_weights(added,[u.GeometryScriptBoneWeight(bone_index=root,weight=1.)])
    u.GeometryScript_MeshEdits.append_mesh(dm,added,u.Transform(),True)

candidate=E.duplicate_asset(BODY,CANDIDATE)
if not candidate:raise RuntimeError('Could not create F57 candidate')
copy_to(dm,candidate,slots);save(candidate)
receipt={'status':'candidate_saved','source_body_sha256':S['sha256'],'candidate':CANDIDATE,
    'candidate_sha256':sha(CANDIDATE),'removed_faces':author['removed_faces'],'added_faces':author['new_faces'],
    'model_source':str(O/'LMG201_FeedMouth57.blend'),'animations_modified':False,'belt_modified':False,
    'cpp_modified':False,'materials_changed':False,'runtime_tested':False}
(O/'delivery.json').write_text(json.dumps(receipt,indent=2));print('F57_CANDIDATE_SAVED',flush=True)
preflight()
backup=O/'Before'/file(BODY).relative_to(P/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
if backup.exists():raise RuntimeError('Original F57 backup retained; current body not overwritten')
shutil.copy2(file(BODY),backup)
copy_to(dm,body,slots);save(body)
receipt.update(status='current_body_saved',saved={BODY:{'sha256':sha(BODY)}},backup=str(backup))
(O/'delivery.json').write_text(json.dumps(receipt,indent=2))
bindings={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in body.materials}
(O/'bindings.json').write_text(json.dumps({body.get_path_name():bindings},indent=2))
manifest=O.parent/'Material21/bindings.json';data=json.loads(manifest.read_text())
data['meshes'][body.get_path_name()]=bindings;data['current_geometry_revision']='FeedMouth57';data['current_feed_mouth_revision']='FeedMouth57'
manifest.write_text(json.dumps(data,indent=2))
print('F57_CURRENT_SAVED',receipt['saved'],flush=True)
