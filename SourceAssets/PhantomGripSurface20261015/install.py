import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'capture.json').read_text());C=json.loads((O/'production.json').read_text());E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
ROOT='/Game/Weapons/PhantomSurface20261015';RP=O/'install_receipt.json';R=json.loads(RP.read_text()) if RP.exists() else {'staged':{},'installed':{},'complete':False,'gameplay_tested':False}
def record():RP.write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing '+path)
 return obj
def save(obj):
 if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
def backup(path):
 dst=O/'Before'/(path.split('.')[0].removeprefix('/Game/')+'.uasset');dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(disk(path),dst)
if not C.get('complete'):raise RuntimeError('Authoring incomplete')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(a['path'] in dirty for a in D['assets'].values()):raise RuntimeError('Preserve unsaved phantom assets')
for key,row in D['assets'].items():
 if key not in R['installed'] and sha(row['path'])!=row['sha256']:raise RuntimeError('Target changed '+key)
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,row in D['assets'].items():
 if key in R['staged']:continue
 target=load(row['path']);source=ROOT+'/'+key+'/SM_'+key+'_Phantom_Continuous';expected={s['name']:s['material'] for s in row['slots']}
 if {str(s.material_slot_name):s.material_interface.get_path_name() for s in target.static_materials}!=expected:raise RuntimeError('Bindings changed '+key)
 previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 try:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
  task=u.AssetImportTask();task.filename=C['assets'][key]['fbx'];task.destination_path=ROOT+'/'+key;task.destination_name=source.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(source)
 finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
 slots=list(mesh.static_materials)
 for i,slot in enumerate(slots):
  name=str(slot.material_slot_name)
  if name not in expected:raise RuntimeError('Unknown slot '+key+' '+name)
  slot.material_interface=load(expected[name]);slots[i]=slot
 mesh.set_editor_property('static_materials',slots);mesh.set_editor_property('nanite_settings',target.get_editor_property('nanite_settings'));u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 settings=sms.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.remove_degenerates=True;settings.generate_lightmap_u_vs=False;sms.set_lod_build_settings(mesh,0,settings)
 save(mesh);R['staged'][key]={'path':source,'sha256':sha(source),'slots':[str(s.material_slot_name) for s in mesh.static_materials]};record();print('PHANTOM_STAGED',key,flush=True)
for key,row in D['assets'].items():
 if key in R['installed']:continue
 source=load(R['staged'][key]['path']);target=load(row['path']);backup(row['path']);lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
 dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),lod)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Read failed '+key)
 mats,indices,names,status=G.get_section_material_list_from_static_mesh(source,lod)
 expected_names=[s['name'] for s in row['slots']];remap=next(getattr(u.GeometryScript_Materials,n) for n in dir(u.GeometryScript_Materials) if n.replace('_','').lower()=='remapmaterialids')
 for i,name in enumerate(names):remap(dm,i,1000+i)
 for i,name in enumerate(names):remap(dm,1000+i,expected_names.index(str(name)))
 opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True,replace_materials=True,new_materials=[load(s['material']) for s in row['slots']],new_material_slot_names=expected_names)
 _,status=G.copy_mesh_to_static_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Write failed '+key)
 # Preserve the complete original material-slot inventory, including unused slots.
 saved_names=[str(s.material_slot_name) for s in target.static_materials];expected_names=[s['name'] for s in row['slots']]
 if saved_names!=expected_names:raise RuntimeError('Material slot order changed '+key+' '+str(saved_names))
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(target);sms.set_lod_build_settings(target,0,sms.get_lod_build_settings(source,0));target.get_editor_property('asset_import_data').scripted_add_filename(C['assets'][key]['fbx'],0,'')
 E.set_metadata_tag(target,'PhantomSurface20261015','Accepted seed 91627; continuous source surface, authored normals and UV preserved; existing host interface retained')
 save(target);R['installed'][key]={'path':row['path'],'sha256':sha(row['path']),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in target.static_materials},'interface':C['assets'][key]['preserved_interface_triangles']};record();print('PHANTOM_INSTALLED',key,flush=True)
R['complete']=True;record();print('PHANTOM_ALL_NINE_SAVED',flush=True)
