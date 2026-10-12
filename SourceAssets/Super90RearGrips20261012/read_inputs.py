import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];I=O/'Inputs';I.mkdir(exist_ok=True)
paths={'super90':'/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7'}
sources=json.loads((P/'SourceAssets/M16UniversalAttachments20260920/sources.json').read_text())
for k in ['phantom_reargrip','stable_antislip_reargrip','balanced_reargrip']:paths[k]=sources[k]['source']
r={'assets':{},'materials':{},'dirty':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if 'Super90' in p.get_name()]}
L=u.MaterialEditingLibrary
for key,path in paths.items():
 obj=u.load_asset(path)
 if not obj:raise RuntimeError(path)
 slots=obj.materials if key=='super90' else obj.static_materials
 r['assets'][key]={'path':path,'sha256':hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest(),'slots':[{'name':str(s.material_slot_name),'imported':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name()} for s in slots]}
 t=u.AssetExportTask();t.object=obj;t.filename=str(I/(key+'.fbx'));t.automated=True;t.prompt=False;t.replace_identical=True;t.options=u.FbxExportOption();t.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(t):raise RuntimeError(str(t.errors))
 for s in slots:
  mat=s.material_interface;path=mat.get_path_name()
  if path in r['materials'] or ('Skin' in str(s.material_slot_name)):continue
  x={'class':mat.get_class().get_name()};r['materials'][path]=x
  if isinstance(mat,u.MaterialInstanceConstant):
   x['parent']=mat.parent.get_path_name();x['scalars']={str(n):L.get_material_instance_scalar_parameter_value(mat,n) for n in L.get_scalar_parameter_names(mat)}
   x['vectors']={str(n):[getattr(L.get_material_instance_vector_parameter_value(mat,n),k) for k in ('r','g','b','a')] for n in L.get_vector_parameter_names(mat)}
   x['textures']={str(n):(L.get_material_instance_texture_parameter_value(mat,n).get_path_name() if L.get_material_instance_texture_parameter_value(mat,n) else None) for n in L.get_texture_parameter_names(mat)}
  else:
   x['inputs']={}
   for label in ['NORMAL','BASE_COLOR','ROUGHNESS','METALLIC','AMBIENT_OCCLUSION']:
    p=getattr(u.MaterialProperty,'MP_'+label);n=L.get_material_property_input_node(mat,p);x['inputs'][label]=n.get_class().get_name() if n else None
   x['textures']={}
   for j,n in enumerate(L.get_material_expressions(mat)):
    try:
     tex=n.get_editor_property('texture')
     if tex:x['textures'][str(j)]=tex.get_path_name()
    except Exception:pass
mesh=u.load_asset(paths['super90']);G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries
mats,indices,names,status=G.get_lod_material_list_from_skeletal_mesh(mesh,u.GeometryScriptMeshReadLOD())
dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read native Super90 geometry')
_,pos,_=Q.get_all_vertex_positions(dm,False);pos=u.GeometryScript_List.convert_vector_list_to_array(pos)
_,tri,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tri)
ids=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tri))]
with gzip.open(I/'native_geometry.json.gz','wt',encoding='utf-8') as f:json.dump({'positions':[[v.x,v.y,v.z] for v in pos],'triangles':[[v.x,v.y,v.z] for v in tri],'materials':ids,'slot_names':[str(n) for n in names],'slot_indices':list(indices)},f)
(O/'inputs.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print('SUPER90_REARGRIP_INPUTS_EXPORTED',list(paths),r['dirty'])
