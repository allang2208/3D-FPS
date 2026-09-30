"""Save isolated native sleeves. Existing appearances supply only materials."""
import sys,importlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/FieldSweaterNativeFamily20260930'
sys.path.insert(0,str(P/'Tools/ModularOutfit'))
import garment_ue as g
importlib.reload(g)
from garment_pipeline import read,write,digest,asset_file
DEST='/Game/Characters/ModularOutfit20260924/FieldSweaterNativeFamily20260930'
B=u.GeometryScript_BoneWeights;E=u.EditorAssetLibrary
profiles=[p for p in read(R/'before.json')['recipe']['rig_meshes'] if p!='Body']
profiles=profiles[globals().get('START',0):globals().get('STOP',len(profiles))]
for profile in profiles:
 receipt=R/'Saved'/profile/'saved.json';author_path=R/'Authored'/(profile+'.json')
 if receipt.exists() and read(receipt).get('author_sha256')==digest(author_path):
  print('NATIVE_SLEEVE_ALREADY_SAVED',profile,flush=True);continue
 d=read(author_path);paths=read(R/'Before'/profile/'paths.json')
 if digest(asset_file(paths['skin']))!=paths['skin_sha256'] or digest(asset_file(paths['shirt']))!=paths['shirt_sha256']:raise RuntimeError('Author source changed: '+profile)
 source=u.load_asset(paths['shirt']);binding=u.load_asset(d['binding_source']);native,_=g.source_snapshot(binding)
 _,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
 vertices=[];normals=[];uv=[];weights=[];triangles=[];lookup={}
 for fi,face in enumerate(d['triangles']):
  row=[]
  for ci,vi in enumerate(face):
   n=d['normals'][fi][ci];t=d['uv'][fi][ci];key=(vi,d['triangle_materials'][fi],*[round(v,7) for v in n+t])
   if key not in lookup:
    lookup[key]=len(vertices);vertices.append(u.Vector(*d['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*t));weights.append(d['weights'][vi])
   row.append(lookup[key])
  triangles.append(u.IntVector(*row))
 dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=triangles),0,True)
 if dm.get_triangle_count()!=len(triangles):raise RuntimeError('UE rejected authored triangles: '+profile)
 B.copy_bones_from_mesh(native,dm);B.mesh_create_bone_weights(dm)
 for vi,w in enumerate(weights):
  _,ok=B.set_vertex_bone_weights(dm,vi,[u.GeometryScriptBoneWeight(bone_index=ids[k],weight=v) for k,v in w.items()])
  if not ok:raise RuntimeError('Native weight write failed: '+profile)
 for fi,mat in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,mat,True)
 path=DEST+'/'+profile+'/SK_'+profile+'_FieldSweater'
 # These are close-camera sleeves, about 26k triangles for BOTH arms. Keep the
 # paired deformation surface at all three LOD indices; do not independently
 # collapse the interior, exterior or lip after binding them to the native arm.
 result=g.save_candidate(dm,source,path,R/'Saved'/profile,binding=binding,lod_triangle_ratios=(1.,1.,1.))
 asset=u.load_asset(path);asset.set_editor_property('physics_asset',None)
 E.set_metadata_tag(asset,'SourceContract',d['contract'])
 E.set_metadata_tag(asset,'AuthorSource',str(author_path))
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Final asset save failed: '+profile)
 result.update(asset_sha256=digest(asset_file(asset.get_path_name())),author_sha256=digest(author_path),native_source=paths['skin'],lod_triangle_ratios=[1.,1.,1.])
 write(receipt,result)
 print('NATIVE_SLEEVE_SAVED',profile,asset.get_path_name(),flush=True)
print('NATIVE_SLEEVE_BATCH_COMPLETE',len(profiles),flush=True)
