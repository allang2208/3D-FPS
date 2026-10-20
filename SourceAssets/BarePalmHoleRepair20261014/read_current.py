"""Read current bare-hand surfaces and native binds without modifying assets."""
import json, hashlib
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BarePalmHoleRepair20261014'
SNAPSHOTS=R/globals().get('SNAPSHOT_SUBDIR','Snapshots');SNAPSHOTS.mkdir(exist_ok=True)
Q=u.GeometryScript_MeshQueries;G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
def xyz(v):return [v.x,v.y,v.z]
paths=globals().get('MESH_PATHS',[
 '/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1',
 '/Game/Characters/ModularOutfit20260924/BarePalmV7/Pickaxe/SK_Pickaxe_BareArmsV7',
 '/Game/Characters/ModularOutfit20260924/BarePalmV7/M4/SK_M4_BareArmsV7'])
for path in paths:
 asset=u.load_asset(path)
 if not isinstance(asset,u.SkeletalMesh):raise RuntimeError('Missing mesh '+path)
 key=hashlib.sha256(path.split('.')[0].encode()).hexdigest()[:12]
 target=SNAPSHOTS/(key+'.json')
 if target.exists() and not globals().get('REFRESH_EMPTY',False):continue
 if target.exists() and json.loads(target.read_text())['triangles']:continue
 dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read failed '+path)
 _,positions,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(positions)
 _,triangles,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(triangles)
 _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
 materials=[dict(slot=str(s.material_slot_name),path=s.material_interface.get_path_name() if s.material_interface else '') for s in asset.materials]
 skin={i for i,s in enumerate(materials) if 'Bare' in s['path'] or 'Thumb' in s['path'] or 'Skin_' in s['slot']}
 triangle_ids=[];mats=[]
 for ti in range(len(ts)):
  m,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
  if valid and m in skin:triangle_ids.append(ti);mats.append(m)
 vertex_ids=sorted({int(v) for ti in triangle_ids for v in xyz(ts[ti])});remap={v:i for i,v in enumerate(vertex_ids)}
 weights=[]
 for vi in vertex_ids:
  _,ws,valid=B.get_vertex_bone_weights(dm,vi)
  weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0} if valid else {})
 ns=[];uv=[]
 for ti in triangle_ids:
  _,a,b,c,valid=Q.get_triangle_normals(dm,ti);ns.append([xyz(v) for v in (a,b,c)])
  a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti);uv.append([[v.x,v.y] for v in (a,b,c)])
 file=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
 d=dict(path=path,source_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),positions=[xyz(ps[i]) for i in vertex_ids],
  triangles=[[remap[int(v)] for v in xyz(ts[i])] for i in triangle_ids],normals=ns,uv=uv,triangle_materials=mats,weights=weights,
  vertex_ids=vertex_ids,triangle_ids=triangle_ids,materials=materials,
  bones={str(b.name):dict(index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
   axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones})
 target.write_text(json.dumps(d,separators=(',',':')))
 print('PALM_SNAPSHOT',path,len(vertex_ids),len(triangle_ids),flush=True)
api={}
for cls in (u.GeometryScript_MeshEdits,u.GeometryScript_MeshQueries,u.GeometryScript_Normals,u.GeometryScript_UVs,u.GeometryScript_VertexColors):
 for n in dir(cls):
  if any(s in n for s in ('triangle','vertex','append','num_uv','uv_set','index','normal')):
   api[cls.__name__+'.'+n]=str(getattr(cls,n).__doc__)
(R/'api.json').write_text(json.dumps(api,indent=2))
print('PALM_SNAPSHOT_COMPLETE',flush=True)
