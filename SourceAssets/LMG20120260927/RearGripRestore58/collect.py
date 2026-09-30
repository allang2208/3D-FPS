"""Read only the installed grips and receiver mounting geometry for authoring."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];(O/'Exports').mkdir(exist_ok=True)
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;E=u.EditorAssetLibrary
keys={'stable':'stable_antislip_reargrip','balanced':'balanced_reargrip','phantom':'phantom_reargrip'}
out={}
for key,variant in keys.items():
 path='/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_'+variant;a=u.load_asset(path)
 out[key]={'asset':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name() if s.material_interface else None} for s in a.static_materials]}
 ex=u.AssetExportTask();ex.object=a;ex.filename=str(O/'Exports'/('Before_'+key+'.fbx'));ex.automated=True;ex.prompt=False;ex.replace_identical=True;ex.options=u.FbxExportOption();ex.options.level_of_detail=False;ex.options.collision=False;ex.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(ex):raise RuntimeError('Cannot read '+key)
body='/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10';a=u.load_asset(body)
dm,status=G.copy_mesh_from_skeletal_mesh(a,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read receiver')
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm);root=next(b.world_transform for b in bones if str(b.name)=='WPN_root')
slots=[str(s.material_slot_name) for s in a.materials]
_,tl,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tl);v={};faces=[]
for ti,t in enumerate(tri):
 mid,ok=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
 if not ok:continue
 name=slots[mid]
 if 'FactoryRearGrip' not in name and name not in {'M_LMG201_H39_Receiver','M_LMG201_G43_EdgeCoat','M_LMG201_Trigger'}:continue
 ids=[t.x,t.y,t.z];pp=[]
 for vi in ids:
  p,ok=Q.get_vertex_position(dm,vi);p=root.inverse_transform_location(p);pp.append([p.x,-p.y,p.z])
 if 'FactoryRearGrip' not in name and not any(-.03<p[0]<.035 and -.045<p[1]<.075 and -.045<p[2]<.045 for p in pp):continue
 for vi,p in zip(ids,pp):v[vi]=p
 faces.append([*ids,mid])
out['Body']={'asset':body,'sha256':hashlib.sha256((P/'Content/Weapons/LMG201/Cover10/SK_LMG201_Cover10.uasset').read_bytes()).hexdigest(),'slots':slots}
with gzip.open(O/'mount.json.gz','wt') as f:json.dump({'vertices':v,'faces':faces,'slots':slots},f)
(O/'capture.json').write_text(json.dumps(out,indent=2))
print('R58_SOURCE_READ',len(faces),flush=True)
