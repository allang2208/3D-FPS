"""Read production glove geometry for the explicitly requested contact check."""
import unreal as u
import json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonStaffGripFacing20261009'
cfg=json.loads((root/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
path=cfg['items']['ue_steel_gauntlets']['rig_meshes']['Jason']
asset=u.load_asset(path)
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List;B=u.GeometryScript_BoneWeights
_,points,_=Q.get_all_vertex_positions(dm,False)
_,tris,_=Q.get_all_triangle_indices(dm,False)
_,bones=B.get_all_bones_info(dm)
points=L.convert_vector_list_to_array(points);tris=L.convert_triangle_list_to_array(tris)
weights=[]
for i in range(len(points)):
    _,ws,valid=B.get_vertex_bone_weights(dm,i)
    if not valid:raise RuntimeError('Missing skin '+str(i))
    weights.append([[w.bone_index,w.weight] for w in ws if w.weight>0])
def xyz(p):return [p.x,p.y,p.z]
data=dict(source=path,positions=[xyz(p) for p in points],triangles=[xyz(t) for t in tris],weights=weights,
    bones=[dict(name=str(b.name),index=b.index,parent=b.parent_index,position=xyz(b.world_transform.translation),
    axes=[xyz(b.world_transform.transform_location(v)-b.world_transform.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))]) for b in bones])
(out/'production-steel.json').write_text(json.dumps(data,separators=(',',':')))
print('STAFF_PRODUCTION_MESH '+path+' '+str(len(points))+' vertices')
