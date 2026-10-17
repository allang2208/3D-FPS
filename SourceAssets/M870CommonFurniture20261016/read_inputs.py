"""Freeze the current M870 mesh and actual common accessory donors for fitting."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];I=O/'Inputs';I.mkdir(exist_ok=True)
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
paths={'m870':'/Game/Weapons/M870/Tactical20261015/SK_M870_V7'}
for folder,keys in [('Super90CommonStocks20261013',('skeleton','core_stock','qr_performance','tactical_telescopic','legendary_adjustable_tactical_stock')),('Super90RearGrips20261012',('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip'))]:
    data=json.loads((O.parent/folder/'inputs.json').read_text())
    paths.update({k:data['assets'][k]['path'] for k in keys})
for k in ('vertical','tactical_vertical','canted','prism','angled'):
    paths[k]='/Game/Weapons/Super90/Foregrips20261007/Meshes/SM_Super90_'+k
R={'assets':{}}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,path in paths.items():
    if path in dirty:raise RuntimeError('Unsaved authoring input '+path)
    obj=u.load_asset(path)
    if not obj:raise RuntimeError(path)
    slots=obj.materials if key=='m870' else obj.static_materials
    if key=='m870' and any(str(s.material_slot_name).startswith('M870_Factory') for s in slots):raise RuntimeError('Keep frozen pre-split input')
    task=u.AssetExportTask();task.object=obj;task.filename=str(I/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True
    task.options=u.FbxExportOption();task.options.level_of_detail=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
    R['assets'][key]={'path':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'name':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in slots]}
mesh=u.load_asset(paths['m870'])
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native extraction failed')
_,pv,_=Q.get_all_vertex_positions(dm,False);ps=u.GeometryScript_List.convert_vector_list_to_array(pv)
_,tv,_=Q.get_all_triangle_indices(dm,False);ts=u.GeometryScript_List.convert_triangle_list_to_array(tv)
_,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
def tr(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
d={'positions':[[v.x,v.y,v.z] for v in ps],'triangles':[[t.x,t.y,t.z] for t in ts],
   'materials':[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(ts))],
   'rest':{str(b.name):tr(b.world_transform) for b in bones},'parents':{str(b.name):names.get(b.parent_index) for b in bones}}
with gzip.open(I/'native_geometry.json.gz','wt',encoding='utf-8') as f:json.dump(d,f,separators=(',',':'))
(O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M870_FURNITURE_INPUTS_EXPORTED',len(paths),flush=True)
