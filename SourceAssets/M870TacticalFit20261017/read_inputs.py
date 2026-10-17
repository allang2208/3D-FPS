"""Read the current host surface and saved tactical donors for fitting."""
import gzip, hashlib, json
from pathlib import Path
import unreal as u

O=Path(__file__).parent; P=O.parents[1]; O.mkdir(exist_ok=True)
path='/Game/Weapons/M870/Tactical20261015/SK_M870_V7'
asset=u.load_asset(path)
G=u.GeometryScript_AssetUtils; Q=u.GeometryScript_MeshQueries
dm,status=G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read M870 surface')
_,pv,_=Q.get_all_vertex_positions(dm,False); ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
_,tv,_=Q.get_all_triangle_indices(dm,False); ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
def tr(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
data={'positions':[[v.x,v.y,v.z] for v in ps],'triangles':[[t.x,t.y,t.z] for t in ts],
      'materials':[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
      'rest':{str(b.name):tr(b.world_transform) for b in bones},
      'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in asset.materials]}
with gzip.open(O/'host.json.gz','wt',encoding='utf-8') as f:json.dump(data,f,separators=(',',':'))
report={'host':path,'host_sha256':hashlib.sha256((P/'Content/Weapons/M870/Tactical20261015/SK_M870_V7.uasset').read_bytes()).hexdigest(),'donors':{}}
for kind in ('laser','flashlight','blessed_laser'):
    donor=u.load_asset('/Game/Weapons/Super90/TacticalBottom20261012/SM_'+kind)
    report['donors'][kind]={'path':donor.get_path_name(),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in donor.static_materials}}
(O/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M870_TACTICAL_INPUTS_READ',flush=True)
