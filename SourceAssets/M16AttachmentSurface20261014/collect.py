import unreal as u,json,array,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];(O/'Input').mkdir(exist_ok=True)
paths={
 'M16_stock':'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic',
 'M16_balanced':'/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_balanced_reargrip',
 'M4_stock':'/Game/Weapons/TacticalTelescopicStock20260914/M4/SM_TacticalTelescopicStock',
 'M4_balanced':'/Game/Weapons/RearGripFinish20260913/M4/balanced/Seam20260914/SM_BalancedRearGrip'}
G,Q,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.MaterialEditingLibrary
def disk(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def readgraph(m):
 p=m.get_path_name()
 if p in R['materials']:return
 if not isinstance(m,u.Material):
  parent=m.parent
  R['materials'][p]={'class':m.get_class().get_name(),'parent':parent.get_path_name(),
   'scalars':{str(n):L.get_material_instance_scalar_parameter_value(m,n) for n in L.get_scalar_parameter_names(m.get_base_material())},
   'textures':{str(n):(L.get_material_instance_texture_parameter_value(m,n).get_path_name() if L.get_material_instance_texture_parameter_value(m,n) else None) for n in L.get_texture_parameter_names(m.get_base_material())}}
  readgraph(parent);return
 nodes=L.get_material_expressions(m);graph=[]
 for n in nodes:
  v={'name':n.get_name(),'class':n.get_class().get_name(),'properties':{}}
  for k in ('coordinate_index','texture','parameter_name','default_value','r','constant','code','description'):
   try:
    x=n.get_editor_property(k)
    v['properties'][k]=x.get_path_name() if isinstance(x,u.Object) else x if isinstance(x,(str,int,float,bool,type(None))) else str(x)
   except Exception:pass
  v['inputs']={}
  for name in L.get_material_expression_input_names(n):
   try:
    connected,output=L.get_material_expression_input_node(n,name)
    v['inputs'][str(name)]=[connected.get_name() if connected else None,str(output)]
   except Exception:pass
  graph.append(v)
 R['materials'][p]={'class':'Material','nodes':graph}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
R={'meshes':{},'materials':{},'runtime_components':[],'runtime_tested':False}
for key,path in paths.items():
 if path in dirty:raise RuntimeError('Unsaved target '+path)
 mesh=u.load_asset(path)
 if not mesh:raise RuntimeError(path)
 dest=O/'Before'/(path.removeprefix('/Game/')+'.uasset');dest.parent.mkdir(parents=True,exist_ok=True)
 if not dest.exists():shutil.copy2(disk(path),dest)
 dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read '+key)
 _,pos,_=Q.get_all_vertex_positions(dm,False);pos=u.GeometryScript_List.convert_vector_list_to_array(pos)
 _,tri,_=Q.get_all_triangle_indices(dm,False);tri=u.GeometryScript_List.convert_triangle_list_to_array(tri)
 mids=[u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0] for i in range(len(tri))]
 row={'path':path,'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest(),'vertices':len(pos),'triangles':len(tri),'uv_sets':Q.get_num_uv_sets(dm),'slots':[str(s.material_slot_name) for s in mesh.static_materials],'materials':[s.material_interface.get_path_name() for s in mesh.static_materials]}
 normals=array.array('f');uvs=[array.array('f') for j in range(row['uv_sets'])]
 for i in range(len(tri)):
  _,n0,n1,n2,_=Q.get_triangle_normals(dm,i)
  for n in (n0,n1,n2):normals.extend((n.x,n.y,n.z))
  for j,uv in enumerate(uvs):
   a,b,c,_=Q.get_triangle_u_vs(dm,j,i)
   for p in (a,b,c):uv.extend((p.x,p.y))
 with (O/'Input'/(key+'.bin')).open('wb') as f:
  f.write((json.dumps(row)+'\n').encode())
  for ar in [array.array('f',(x for p in pos for x in (p.x,p.y,p.z))),array.array('i',(x for t in tri for x in (t.x,t.y,t.z))),array.array('i',mids),normals]+uvs:ar.tofile(f)
 for s in mesh.static_materials:readgraph(s.material_interface)
 task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'Input'/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+key)
 R['meshes'][key]=row
 (O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
# Read only components using the named meshes, without opening a preview or running a game.
for comp in u.ObjectIterator(u.StaticMeshComponent):
 mesh=comp.get_editor_property('static_mesh')
 if not mesh or mesh.get_path_name().split('.')[0] not in paths.values():continue
 mats=[]
 for i in range(comp.get_num_materials()):
  m=comp.get_material(i);mats.append(m.get_path_name() if m else None)
 R['runtime_components'].append({'component':comp.get_path_name(),'mesh':mesh.get_path_name(),'materials':mats})
(O/'inputs.json').write_text(json.dumps(R,indent=2),encoding='utf-8')
print('M16_ATTACHMENT_INPUTS_SAVED',list(R['meshes']),len(R['materials']))
