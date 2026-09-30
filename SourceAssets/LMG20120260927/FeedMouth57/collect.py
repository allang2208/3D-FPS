"""Read the current fixed receiver surfaces needed for local feed clearance."""
import unreal as u
import json, gzip, hashlib
from pathlib import Path
O=Path(__file__).parent; P=O.parents[2]
BODY='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10'
asset=u.load_asset(BODY)
G=u.GeometryScript_AssetUtils; Q=u.GeometryScript_MeshQueries; B=u.GeometryScript_BoneWeights
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read body')
_,bones=B.get_all_bones_info(dm)
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
slots=[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in asset.materials]
out={'body':BODY,'sha256':hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest(),'slots':slots,'bones':[{'name':str(b.name),'index':b.index,'rest':tr(b.world_transform)} for b in bones],'pie':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'dirty':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
targets={'M_LMG201_A40_Cover','M_LMG201_A40_Interior','M_LMG201_S42_Cover','M_LMG201_F37_Interior','M_LMG201_H39_Receiver','M_LMG201_G43_EdgeCoat'}
_,tl,_=Q.get_all_triangle_indices(dm,False); triangles=u.GeometryScript_List.convert_triangle_list_to_array(tl)
verts={};rows=[];normals={};uvs={}
get_uvs=getattr(Q,next(n for n in dir(Q) if n.replace('_','').lower()=='gettriangleuvs'))
for ti,t in enumerate(triangles):
 mid,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
 if not valid or slots[mid]['name'] not in targets:continue
 rows.append([ti,t.x,t.y,t.z,mid])
 _,n0,n1,n2,valid=Q.get_triangle_normals(dm,ti)
 normals[ti]=[list(n.to_tuple()) for n in (n0,n1,n2)]
 uv0,uv1,uv2,valid=get_uvs(dm,0,ti)
 uvs[ti]=[list(v.to_tuple()) for v in (uv0,uv1,uv2)]
 for vi in (t.x,t.y,t.z):
  if vi in verts:continue
  p,valid=Q.get_vertex_position(dm,vi);_,w,valid=B.get_vertex_bone_weights(dm,vi)
  verts[vi]={'p':list(p.to_tuple()),'w':[[v.bone_index,v.weight] for v in w if v.weight>0]}
with gzip.open(O/'native.json.gz','wt') as f:json.dump({'vertices':verts,'triangles':rows,'normals':normals,'uvs':uvs},f)
(O/'source.json').write_text(json.dumps(out,indent=2))
print('F57_SOURCE',out['sha256'],len(rows),'faces', 'PIE',out['pie'],flush=True)
