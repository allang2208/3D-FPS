from pathlib import Path
import unreal as u,json,runpy,hashlib,gc
R=Path(__file__).resolve().parent
H=runpy.run_path(str(R/'materials.py'));BASE=H['BASE'];save=H['save'];load=H['load'];record=H['record']
A=u.AssetToolsHelpers.get_asset_tools();SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

def main(selected=None):
 report=json.loads((R/'assets_saved.json').read_text(encoding='utf8'))
 for row in json.loads((R/'assembly.json').read_text(encoding='utf8'))['meshes']:
  if selected and row['kind'] not in selected:continue
  t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name=row['name'];t.automated=True;t.replace_existing=True;t.save=False;t.factory=u.FbxFactory()
  o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;o.import_mesh=True;o.import_materials=False;o.import_textures=False;o.import_animations=False
  d=o.static_mesh_import_data
  for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=False).items():d.set_editor_property(k,v)
  d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;t.options=o;A.import_asset_tasks([t])
  if not t.imported_object_paths:raise RuntimeError('No imported mesh '+row['name'])
  mesh=load(BASE+'/Meshes/'+row['name'])
  for i,s in enumerate(mesh.get_editor_property('static_materials')):mesh.set_material(i,load(report['materials'][str(s.material_slot_name)]))
  bs=SM.get_lod_build_settings(mesh,0);bs.use_full_precision_u_vs=True;bs.recompute_normals=False;bs.recompute_tangents=False;bs.generate_lightmap_u_vs=False;SM.set_lod_build_settings(mesh,0,bs)
  ns=mesh.get_editor_property('nanite_settings').copy();ns.enabled=False;mesh.set_editor_property('nanite_settings',ns)
  mesh.set_editor_property('positive_bounds_extension',u.Vector(15000,15000,1500));mesh.set_editor_property('negative_bounds_extension',u.Vector(15000,15000,1500))
  save(mesh);report['meshes'][row['kind']]=dict(path=mesh.get_path_name(),triangles=row['triangles'],sha256=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest());record(report)
  gc.collect();u.SystemLibrary.collect_garbage();print('TRAFFIC_MESH_SAVED',row['kind'])
 if len(report['meshes'])==4:report['stage']='assets_saved';record(report)
if __name__=='__main__':main()
