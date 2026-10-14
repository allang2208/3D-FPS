"""Save only the three authored LMG201 junction repairs through the UE batch gate."""
import array,hashlib,json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve();C=json.loads((O/'Input/current.json').read_text())
E=u.EditorAssetLibrary;AU=u.GeometryScript_AssetUtils;ED=u.GeometryScript_MeshEdits;N=u.GeometryScript_Normals
VERSION='LMG201GripJunction-20261007';RP=O/'install_receipt.json'
R=json.loads(RP.read_text()) if RP.exists() else {'version':VERSION,'meshes':{},'complete':False,'runtime_tested':False,'material_changed':False}
def record():RP.write_text(json.dumps(R,indent=2))
def disk(p):return P/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
def outcome(r):
 if isinstance(r,tuple) and any(isinstance(x,u.GeometryScriptOutcomePins) and x!=u.GeometryScriptOutcomePins.SUCCESS for x in r):raise RuntimeError('Geometry operation failed')
dirty=set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if ed and ed.get_game_world():raise RuntimeError('PIE active; preserve current session')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key,row in C.items():
 if row['path'] in dirty:raise RuntimeError('Unsaved target '+row['path'])
 if key not in R['meshes'] and sha(row['path'])!=row['sha256']:raise RuntimeError('Concurrent target edit '+key)
for key,row in C.items():
 if key in R['meshes']:continue
 mesh=u.load_asset(row['path'])
 if not mesh:raise RuntimeError('Missing current mesh '+key)
 before=O/'Before'/(row['path'].removeprefix('/Game/')+'.uasset');before.parent.mkdir(parents=True,exist_ok=True)
 if not before.exists():shutil.copy2(disk(row['path']),before)
 dm=u.DynamicMesh();outcome(AU.copy_mesh_from_static_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)))
 with (O/'Plans'/(key+'.bin')).open('rb') as f:
  h=json.loads(f.readline())
  if h['source_sha256']!=sha(row['path']):raise RuntimeError('Target changed before write '+key)
  def read(code,count):a=array.array(code);a.fromfile(f,count);return a
  vids=read('i',h['moved']);positions=read('f',len(vids)*3);tids=read('i',h['normal_triangles']);normals=read('f',len(tids)*9)
 for i,vid in enumerate(vids):ED.set_vertex_position(dm,vid,u.Vector(*positions[3*i:3*i+3]),True)
 for i,tid in enumerate(tids):
  j=i*9;n=u.GeometryScriptTriangle();n.vector0=u.Vector(*normals[j:j+3]);n.vector1=u.Vector(*normals[j+3:j+6]);n.vector2=u.Vector(*normals[j+6:j+9]);N.set_mesh_triangle_normals(dm,tid,n,True)
 if h.get('orientation_flip_ids'):
  result=u.GeometryScript_MeshSelection.convert_index_array_to_mesh_selection(dm,h['orientation_flip_ids'],u.GeometryScriptMeshSelectionType.TRIANGLES)
  selection=next(x for x in result if isinstance(x,u.GeometryScriptMeshSelection)) if isinstance(result,tuple) else result
  N.flip_triangle_selection_normals(dm,selection,True,False)
 slots=list(mesh.get_editor_property('static_materials'))
 opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[s.material_interface for s in slots],new_material_slot_names=[s.material_slot_name for s in slots],enable_recompute_normals=False,enable_recompute_tangents=True,enable_remove_degenerates=False,use_original_vertex_order=True)
 outcome(AU.copy_mesh_to_static_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD(lod_index=0)));mesh.set_editor_property('static_materials',slots)
 E.set_metadata_tag(mesh,'GripJunctionVersion',VERSION);E.set_metadata_tag(mesh,'GripJunctionAuthor','SourceAssets/LMG201GripJunction20261007/README.md')
 exports=O/'Exports';exports.mkdir(exist_ok=True);fbx=exports/(mesh.get_name()+'.fbx')
 task=u.AssetExportTask();task.object=mesh;task.filename=str(fbx);task.automated=True;task.prompt=False;task.replace_identical=True
 task.options=u.FbxExportOption();task.options.level_of_detail=False;task.options.collision=False;task.options.bake_material_inputs=u.FbxMaterialBakeMode.DISABLED
 if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Author export failed '+key)
 mesh.get_editor_property('asset_import_data').scripted_add_filename(str(fbx),0,'201 junction refined current source')
 if not E.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+key)
 R['meshes'][key]={'path':row['path'],'sha256':sha(row['path']),'fbx':str(fbx),'source_sha256':h['source_sha256'],'moved_vertices':len(vids),'normal_triangles':len(tids),'orientation_flipped_triangles':len(h.get('orientation_flip_ids',[])),
  'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in slots],'triangles':row['triangles'],'uv_sets':row['uv_sets'],'saved':True};record();print('JUNCTION_SAVED',key,flush=True)
R['complete']=len(R['meshes'])==len(C);record();print('JUNCTION_COMPLETE',R['complete'],flush=True)
