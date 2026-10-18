"""Save only the 25 hardknuckle bindings and its existing pickup mesh."""
import hashlib, json, shutil
from pathlib import Path
import unreal as u

O=Path(__file__).parent;R=O.parents[1]
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;E=u.EditorAssetLibrary
rows=json.loads((O/'author_receipt.json').read_text())
review=json.loads((O/'geometry_review.json').read_text())
if len(review['profiles'])!=len(rows):raise RuntimeError('Incomplete scoped glove repair review')
review_hashes={row['profile']:row['sha256'] for row in review['profiles']}
for row in rows:
    if review_hashes[row['profile']]!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():
        raise RuntimeError('Authored mesh changed since cuff diagnosis '+row['profile'])
receipt_path=O/'import_receipt.json'
receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {'saved':{},'game_run':False}
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('Do not replace loaded outfit during PIE')

def load(p):
    asset=u.load_asset(p)
    if not asset:raise RuntimeError('Missing dependency '+p)
    return asset

def backup(asset):
    relative=asset.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset'
    source=R/'Content'/relative;dest=O/'Before/Assets'/relative
    if source.exists() and not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)

def build_dynamic(d,native=None):
    vertices=[];normals=[];uv=[];triangles=[];weights=[];seen={}
    for fi,face in enumerate(d['triangles']):
        out=[]
        for corner,vi in enumerate(face):
            n=d['normals'][fi][corner];tex=d['uv'][fi][corner]
            key=(vi,*[round(x,7) for x in n+tex])
            if key not in seen:
                seen[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]))
                normals.append(u.Vector(*n));uv.append(u.Vector2D(*tex));weights.append(d['weights'][vi])
            out.append(seen[key])
        triangles.append(u.IntVector(*out))
    dm=u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True)
    if native:
        _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
        B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
        for vi,ws in enumerate(weights):
            missing=set(ws)-set(ids)
            if missing:raise RuntimeError('Missing native cuff bones '+str(missing))
            B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[n],weight=w) for n,w in ws.items()])
    for fi,material in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,material,True)
    return dm

def options(d):
    return u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[load(p) for p in d['materials']],
        new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)

def save(asset,key,sha,triangles):
    E.set_metadata_tag(asset,'HardKnuckleRepair20261017',sha)
    E.set_metadata_tag(asset,'Super90GarmentSHA256',sha)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    receipt['saved'][key]={'asset':asset.get_path_name(),'sha256':sha,'triangles_lod0':triangles,'saved':True}
    receipt_path.write_text(json.dumps(receipt,indent=2))
    print('HARDKNUCKLE_SAVED',key,asset.get_path_name(),flush=True)

sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
for row in rows:
    raw=Path(row['file']).read_bytes();sha=hashlib.sha256(raw).hexdigest();d=json.loads(raw);key=row['profile'];asset=load(row['asset'])
    if receipt['saved'].get(key,{}).get('sha256')==sha and E.get_metadata_tag(asset,'HardKnuckleRepair20261017')==sha:continue
    backup(asset)
    native,status=G.copy_mesh_from_skeletal_mesh(load(d['binding_source']),u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native binding '+key)
    dm=build_dynamic(d,native)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,asset,options(d),u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot rebuild '+key)
    asset.set_editor_property('physics_asset',None)
    u.FPSModularOutfitComponent.configure_outfit_lods(asset)
    if not sub.regenerate_lod(asset,3,True,False):raise RuntimeError('Could not regenerate glove LODs '+key)
    save(asset,key,sha,len(d['triangles']))

row=next(x for x in rows if x['profile']=='M4');raw=Path(row['file']).read_bytes();d=json.loads(raw);sha=hashlib.sha256(raw).hexdigest()
asset=load('/Game/Characters/ModularOutfit20260924/Super90Source20261006/Pickups/SM_ue_hardknuckle_gloves')
backup(asset);dm=build_dynamic(d)
_,status=G.copy_mesh_to_static_mesh(dm,asset,options(d),u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Could not rebuild glove pickup')
save(asset,'pickup',sha,len(d['triangles']))
receipt['completed']=len(receipt['saved'])==len(rows)+1
receipt_path.write_text(json.dumps(receipt,indent=2))
print('HARDKNUCKLE_IMPORT_COMPLETE',receipt['completed'],flush=True)
