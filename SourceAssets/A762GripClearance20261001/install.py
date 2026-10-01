"""Save the two local R09 clearance edits, retaining topology, UVs and slots."""
import array,hashlib,json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=Path(u.Paths.project_dir()).resolve()
if P!=Path('D:/FPS3D/FPSGAME').resolve():raise RuntimeError('Wrong project')
C=json.loads((O/'Input/current.json').read_text());RP=O/'install_receipt.json'
receipt=json.loads(RP.read_text()) if RP.exists() else {'revision':'GripClearance09-20261001','saved':{},'complete':False,'tested':False}
ROOT='/Game/Weapons/A762/GripClearance20261001'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();AU=u.GeometryScript_AssetUtils
def disk(path):return P/'Content'/(path.removeprefix('/Game/')+'.uasset')
def sha(file):return hashlib.sha256(file.read_bytes()).hexdigest()
def record():RP.write_text(json.dumps(receipt,indent=2))
def outcome(result):
 pins=[x for x in result if isinstance(x,u.GeometryScriptOutcomePins)] if isinstance(result,tuple) else []
 if pins and pins[0]!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Native mesh copy failed')
dirty=set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if ed and ed.get_game_world():raise RuntimeError('PIE_ACTIVE: authored R09 ready; no asset writes')
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(ROOT) for p in dirty):raise RuntimeError('Unsaved revision asset')
for key,row in C.items():
 path=row['path']
 if path in dirty:raise RuntimeError('Unsaved current mesh '+path)
 if sha(disk(path))!=receipt['saved'].get(path,{}).get('sha256',row['sha256']):raise RuntimeError('Concurrent mesh edit '+key)
 mesh=u.load_asset(path);slots=mesh.materials if key=='Body' else mesh.static_materials
 if [str(s.material_slot_name) for s in slots]!=row['slots'] or [s.material_interface.get_path_name() if s.material_interface else None for s in slots]!=row['materials']:
  raise RuntimeError('Material bindings changed '+key)

for key,row in C.items():
 path=row['path']
 if path in receipt['saved']:continue
 body=key=='Body';mesh=u.load_asset(path)
 backup=O/'Before'/(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(disk(path),backup)
 with (O/'Exports'/(key+'_edit.bin')).open('rb') as f:
  h=json.loads(f.readline())
  def read(code,count):
   a=array.array(code);a.fromfile(f,count);return a
  vi=read('i',h['moved_vertices']);pos=read('f',len(vi)*3);ti=read('i',h['normal_triangles']);ns=read('f',len(ti)*9)
 dm=u.DynamicMesh();fn=AU.copy_mesh_from_skeletal_mesh if body else AU.copy_mesh_from_static_mesh
 outcome(fn(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0)))
 if dm.get_triangle_count()!=h['triangles']:raise RuntimeError('Source topology changed '+key)
 for i,vid in enumerate(vi):u.GeometryScript_MeshEdits.set_vertex_position(dm,vid,u.Vector(*pos[3*i:3*i+3]),True)
 for i,tid in enumerate(ti):
  normal=u.GeometryScriptTriangle();j=i*9
  normal.vector0=u.Vector(*ns[j:j+3]);normal.vector1=u.Vector(*ns[j+3:j+6]);normal.vector2=u.Vector(*ns[j+6:j+9])
  u.GeometryScript_Normals.set_mesh_triangle_normals(dm,tid,normal,True)
 candidate=ROOT+'/'+path.rsplit('/',1)[1]+'_R09'
 if E.does_asset_exist(candidate):
  if candidate not in receipt['saved']:raise RuntimeError('Unowned candidate '+candidate)
  copy=u.load_asset(candidate)
 else:copy=A.duplicate_asset(candidate.rsplit('/',1)[1],ROOT,mesh)
 options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=False,enable_recompute_normals=False,enable_recompute_tangents=True,enable_remove_degenerates=False,use_original_vertex_order=True)
 write=AU.copy_mesh_to_skeletal_mesh if body else AU.copy_mesh_to_static_mesh
 for target,asset in [(candidate,copy),(path,mesh)]:
  outcome(write(dm,asset,options,u.GeometryScriptMeshWriteLOD(lod_index=0)))
  E.set_metadata_tag(asset,'A762DetailRevision','GripClearance09-20261001')
  E.set_metadata_tag(asset,'A762DetailSource','SourceAssets/A762GripClearance20261001/README.md')
  if not body:asset.get_editor_property('asset_import_data').scripted_add_filename(str(O/'Exports/SM_A762_phantom_reargrip_R09.fbx'),0,'R09 trigger clearance')
  if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+target)
  receipt['saved'][target]={'sha256':sha(disk(target)),'triangles':h['triangles'],'moved_vertices':len(vi),'normal_triangles':len(ti),'backup':str(backup),'slots':row['slots'],'materials':row['materials']};record()
  print('A762_SURFACE_CLEARANCE_SAVED',key,target,flush=True)
receipt['complete']=all(row['path'] in receipt['saved'] for row in C.values());record()
print('A762_SURFACE_CLEARANCE_COMPLETE',receipt['complete'],flush=True)
