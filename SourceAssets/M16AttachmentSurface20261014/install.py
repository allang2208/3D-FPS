"""Repair existing M16 assets through the active editor, preserving all other work."""
import unreal as u,json,gzip,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];C=json.loads((O/'inputs.json').read_text())
E=u.EditorAssetLibrary;G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;N=u.GeometryScript_Normals
RP=O/'install_receipt.json';R=json.loads(RP.read_text()) if RP.exists() else {'meshes':{},'complete':False,'gameplay_tested':False}
def record():RP.write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 ed=u.get_editor_subsystem(u.LevelEditorSubsystem)
 if ed.is_in_play_in_editor():raise RuntimeError('PIE is still stopping; do not modify loaded meshes yet.')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in ('M16_stock','M16_balanced'):
 if key in R['meshes']:continue
 row=C['meshes'][key];path=row['path']
 if path in dirty or sha(path)!=row['sha256']:raise RuntimeError('Preserve changed or unsaved target '+path)
 mesh=u.load_asset(path)
 dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read failed '+key)
 with gzip.open(O/'Plans'/(key+'.json.gz'),'rt',encoding='utf-8') as f:d=json.load(f)
 def setuv(tid,channel,coords):
  x=u.GeometryScriptUVTriangle(uv0=u.Vector2D(*coords[0]),uv1=u.Vector2D(*coords[1]),uv2=u.Vector2D(*coords[2]))
  u.GeometryScript_UVs.set_mesh_triangle_u_vs(dm,channel,tid,x,True)
 if key=='M16_stock':
  for j,tid in enumerate(d['triangles']):
   setuv(tid,0,d['uv0'][j]);setuv(tid,1,d['uv1'][j])
   n=d['normals'][j]
   N.set_mesh_triangle_normals(dm,tid,u.GeometryScriptTriangle(vector0=u.Vector(*n[0]),vector1=u.Vector(*n[1]),vector2=u.Vector(*n[2])),True)
 else:
  u.GeometryScript_MeshEdits.set_all_mesh_vertex_positions(dm,u.GeometryScript_List.convert_array_to_vector_list([u.Vector(*p) for p in d['positions']]))
  for i,mid in enumerate(d['materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,i,mid,True)
  for i,tid in enumerate(d['uv_triangles']):setuv(tid,0,d['uv0'][i])
  _,selection=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,d['normal_faces'],u.GeometryScriptMeshSelectionType.TRIANGLES)
  N.recompute_normals_for_mesh_selection(dm,selection,u.GeometryScriptCalculateNormalsOptions())
  _,body_selection=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,d['uv_triangles'],u.GeometryScriptMeshSelectionType.TRIANGLES)
  # The selected balanced grip is solid polymer. Restore its original zero-RGB
  # MetalRegion mask only on the grasping body; native cap and metal neck retain theirs.
  u.GeometryScript_VertexColors.set_mesh_selection_vertex_color(dm,body_selection,u.LinearColor(0,0,0,1),u.GeometryScriptColorFlags(),True)
 N.compute_tangents(dm,u.GeometryScriptTangentsOptions(uv_layer=0))
 options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True)
 _,status=G.copy_mesh_to_static_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write failed '+key)
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);settings=sms.get_lod_build_settings(mesh,0)
 settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
 sms.set_lod_build_settings(mesh,0,settings)
 E.set_metadata_tag(mesh,'M16AttachmentSurfaceRepair','20261014 R2: precise donor UV0/tangent alignment; semantic body/neck/native-cap material IDs; scoped surface fairing')
 save(mesh)
 R['meshes'][key]={'path':path,'saved':True,'sha256':sha(path),'source_sha256':row['sha256'],'tangent_algorithm':'FastMikkT'};record()
 final=O/'Final';final.mkdir(exist_ok=True)
 task=u.AssetExportTask();task.object=mesh;task.filename=str(final/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
 mesh.get_editor_property('asset_import_data').scripted_add_filename(task.filename,0,'');save(mesh)
 R['meshes'][key].update(sha256=sha(path),export=task.filename);record()
 print('M16_REPAIRED_SAVED',key,flush=True)
if not R.get('detail_normal'):
 path='/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Normal_Game'
 if path in dirty:raise RuntimeError('Unsaved stock normal texture')
 old=u.load_asset(path);backup=O/'Before'/(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(disk(path),backup)
 settings={n:old.get_editor_property(n) for n in ('srgb','compression_settings','flip_green_channel','lod_group','lod_bias','never_stream')}
 task=u.AssetImportTask();task.filename=str(O/'Detail/T_TelescopicStructuralDetail_R2.png');task.destination_path=path.rsplit('/',1)[0];task.destination_name=path.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory()
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(path)
 for n,v in settings.items():tex.set_editor_property(n,v)
 E.set_metadata_tag(tex,'StockDetailRecipe','M16AttachmentSurface20261014: high mesh follows repaired low, micro-burr cleanup, 4K structural normal bake at full strength')
 save(tex);R['detail_normal']={'path':path,'saved':True,'sha256':sha(path),'strength':1,'shared_stock_families':10};record()
# Finalize an already-saved stock from the interrupted import-metadata operation.
for key,row in R['meshes'].items():
 if row.get('export') and row.get('tangent_algorithm')=='FastMikkT':continue
 if sha(row['path'])!=row['sha256']:raise RuntimeError('Changed partial target '+key)
 mesh=u.load_asset(row['path'])
 if '20261014 R2:' not in E.get_metadata_tag(mesh,'M16AttachmentSurfaceRepair'):raise RuntimeError('Partial target identity differs')
 if row.get('tangent_algorithm')!='FastMikkT':
  dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL))
  N.compute_tangents(dm,u.GeometryScriptTangentsOptions(uv_layer=0))
  _,status=G.copy_mesh_to_static_mesh(dm,mesh,u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True),u.GeometryScriptMeshWriteLOD())
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Tangent write failed '+key)
  u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 save(mesh)
 task=u.AssetExportTask();task.object=mesh;task.filename=str(O/'Final'/(key+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+key)
 mesh.get_editor_property('asset_import_data').scripted_add_filename(task.filename,0,'');save(mesh)
 row.update(sha256=sha(row['path']),export=task.filename,tangent_algorithm='FastMikkT');record()
R['complete']=True;record();print('M16_ATTACHMENT_SURFACE_R2_COMPLETE',flush=True)
from runpy import run_path
run_path(str(O/'diagnose_saved.py'),run_name='__main__')
