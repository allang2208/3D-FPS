"""Save isolated fixed assets. Publish only this item's two rig references later."""
import sys,json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterSurfaceRepair20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
from garment_ue import source_snapshot,save_candidate
from garment_pipeline import read,write,digest,asset_file
DEST='/Game/Characters/ModularOutfit20260924/FieldSweaterSurfaceRepair20260930'
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights;E=u.EditorAssetLibrary
results={}
for profile in ['Body','Traversal']:
    revision=profile
    receipt=R/'Saved'/revision/'saved.json'
    if receipt.exists():results[profile]=read(receipt);continue
    author_path=R/'Authored'/('BodyEquipped.json' if profile=='Body' else profile+'.json')
    d=read(author_path);paths=read(R/'Before'/profile/'paths.json')
    source=u.load_asset(paths['shirt']);binding=u.load_asset(d['binding_source']);native,_=source_snapshot(binding)
    _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
    vertices=[];normals=[];uv=[];weights=[];triangles=[];lookup={}
    for fi,f in enumerate(d['triangles']):
        row=[]
        for ci,vi in enumerate(f):
            n=d['normals'][fi][ci];t=d['uv'][fi][ci];key=(vi,d['triangle_materials'][fi],*[round(v,7) for v in n+t])
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*t));weights.append(d['weights'][vi])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True)
    if dm.get_triangle_count()!=len(triangles):raise RuntimeError('Rejected cloth triangles '+profile)
    B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
    for vi,w in enumerate(weights):
        _,ok=B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[k],weight=v) for k,v in w.items()])
        if not ok:raise RuntimeError('Cannot assign native cloth weights')
    for fi,mat in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,mat,True)
    path=DEST+'/'+revision+'/SK_'+profile+'_FieldSweater'
    material_source=source
    if d.get('extra_materials'):
        material_source=u.new_object(u.SkeletalMesh)
        slots=list(source.get_editor_property('materials'))
        for name,mat in zip(['ExposedArmSkin','ExposedTorsoSkin'],d['extra_materials']):
            slots.append(u.SkeletalMaterial(material_interface=u.load_asset(mat),material_slot_name=name))
        material_source.set_editor_property('materials',slots)
    results[profile]=save_candidate(dm,material_source,path,R/'Saved'/revision,binding=binding)
    asset=u.load_asset(path);asset.set_editor_property('physics_asset',None);E.set_metadata_tag(asset,'SourceContract',d['contract'])
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Final asset metadata save '+profile)
    results[profile]['asset_sha256']=digest(asset_file(asset.get_path_name()))
    results[profile]['author_sha256']=digest(author_path)
    write(receipt,results[profile])
    print('FIELD_SURFACE_SAVED',profile,asset.get_path_name(),flush=True)

write(R/'saved-assets.json',results)
print('FIELD_SURFACE_ASSETS_SAVED',len(results),flush=True)
