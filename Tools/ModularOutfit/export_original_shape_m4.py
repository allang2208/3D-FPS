"""Export the original M4 native surface for a shape-preserving bare derivative."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4')
ROOT.mkdir(parents=True,exist_ok=True)
SOURCE='/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416'
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights;G=u.GeometryScript_AssetUtils
asset=u.load_asset(SOURCE)
dm,outcome=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if outcome!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot export original M4')
def xyz(v):return [v.x,v.y,v.z]
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
_,plist,_=Q.get_all_vertex_positions(dm,False)
positions=u.GeometryScript_List.convert_vector_list_to_array(plist)
_,tlist,_=Q.get_all_triangle_indices(dm,False)
triangles=u.GeometryScript_List.convert_triangle_list_to_array(tlist)
materials=[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else ''} for s in asset.materials]
armids=[i for i,s in enumerate(materials) if 'Manny' in s['slot']]
faces=[];uv=[];mats=[];normals=[];triangle_ids=[]
for i,t in enumerate(triangles):
    mat,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,i)
    if not valid or mat not in armids:continue
    a,b,c,valid=Q.get_triangle_u_vs(dm,0,i)
    if not valid:raise RuntimeError('Original UV missing')
    _,n1,n2,n3,valid=Q.get_triangle_normals(dm,i)
    if not valid:raise RuntimeError('Original normal missing')
    faces.append(xyz(t));uv.append([[v.x,v.y] for v in (a,b,c)])
    normals.append([xyz(v) for v in (n1,n2,n3)]);mats.append(mat);triangle_ids.append(i)
ids=sorted({v for f in faces for v in f});remap={v:i for i,v in enumerate(ids)}
weights=[]
for i in ids:
    _,ws,valid=B.get_vertex_bone_weights(dm,i)
    if not valid:raise RuntimeError('Original weights missing')
    weights.append({names[w.bone_index]:w.weight for w in ws if w.weight>0})
data={'source':asset.get_path_name(),'materials':materials,'arm_materials':armids,
 'bones':{str(b.name):{'index':b.index,'parent':b.parent_index,'position':xyz(b.world_transform.translation),
  'axes':[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]} for b in bones},
 'positions':[xyz(positions[i]) for i in ids],'weights':weights,'source_vertex_ids':ids,
 'triangles':[[remap[v] for v in f] for f in faces],'source_triangle_ids':triangle_ids,
 'uv':uv,'normals':normals,'triangle_materials':mats}
(ROOT/'M4_original.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
print('ORIGINAL_M4_EXPORTED',len(ids),len(faces))
