"""Save restored original sleeves only. Body appearance is material-driven."""
import hashlib,json,shutil,sys
from pathlib import Path
import unreal as u
O=Path(__file__).parent;R=O.parents[1];sys.path.insert(0,str(O))
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():raise RuntimeError('Preserve the running game; do not replace clothes during PIE')
exec(compile((O/'build_materials.py').read_text(),str(O/'build_materials.py'),'exec'),{'__file__':str(O/'build_materials.py')})
rows=json.loads((O/'sleeve_manifest.json').read_text())
receipt_path=O/'import_receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'saved':{},'game_run':False}

def save_receipt():receipt_path.write_text(json.dumps(receipt,indent=2))
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing asset '+path)
    return asset
for row in rows:
    raw=Path(row['file']).read_bytes();sha=hashlib.sha256(raw).hexdigest();d=json.loads(raw);asset=load(row['asset'])
    if receipt['saved'].get(row['profile'],{}).get('sha256')==sha and E.get_metadata_tag(asset,'ST6OriginalSleeves20261017')==sha:continue
    relative=asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
    backup=O/'Before/Assets'/relative
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(R/'Content'/relative,backup)
    native,status=G.copy_mesh_from_skeletal_mesh(load(d['binding_source']),u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot load sleeve binding')
    _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
    vertices=[];normals=[];uv=[];weights=[];faces=[];seen={}
    for fi,face in enumerate(d['triangles']):
        tri=[]
        for j,vi in enumerate(face):
            n=d['normals'][fi][j];t=d['uv'][fi][j];key=(vi,*[round(v,7) for v in n+t])
            if key not in seen:
                seen[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*t));weights.append(d['weights'][vi])
            tri.append(seen[key])
        faces.append(u.IntVector(*tri))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=faces),0,True)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for i,ws in enumerate(weights):B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in ws.items()])
    for fi,m in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,m,True)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(p) for p in d['materials']],new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot restore sleeve '+row['profile'])
    asset.set_editor_property('physics_asset',None)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(asset,3,True,False)
    E.set_metadata_tag(asset,'ST6OriginalSleeves20261017',sha);E.set_metadata_tag(asset,'Super90GarmentSHA256',sha)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+row['profile'])
    receipt['saved'][row['profile']]={'asset':asset.get_path_name(),'sha256':sha,'triangles':len(faces)};save_receipt()
    print('ST6_ORIGINAL_SLEEVE_SAVED',row['profile'],flush=True)
receipt['sleeves_completed']=len(receipt['saved'])==25;save_receipt()
print('ST6_ORIGINAL_SLEEVES_COMPLETE',flush=True)
