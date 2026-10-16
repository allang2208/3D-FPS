"""Install nine matched bodies, then restore the shared normal; never alter M16."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=json.loads((O/'inputs.json').read_text());C=json.loads((O/'production.json').read_text())
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary;G=u.GeometryScript_AssetUtils
ROOT='/Game/Weapons/TelescopicMatchedSurface20261015';NORMAL='/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Normal_Game';M16='/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic'
RP=O/'install_receipt.json';R=json.loads(RP.read_text()) if RP.exists() else {'staged':{},'installed':{},'normal':None,'a762_materials':{},'complete':False,'gameplay_tested':False}
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
paths=[a['path'] for a in D['assets'].values()]+[NORMAL]+[s['material'].split('.')[0] for s in D['assets']['A762']['slots'][1:4]]
if any(p in dirty for p in paths):raise RuntimeError('Preserve unsaved target assets '+str([p for p in paths if p in dirty]))
if sha(M16)!=D['accepted_m16_sha256']:raise RuntimeError('Accepted M16 changed; preserve it')
for key,row in D['assets'].items():
 if key not in R['installed'] and sha(row['path'])!=row['sha256']:raise RuntimeError('Changed target '+key)
if not R['normal'] and sha(NORMAL)!=D['shared_normal_sha256']:raise RuntimeError('Shared stock normal changed')
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
for key,row in D['assets'].items():
 if key in R['staged']:continue
 target=load(row['path']);source=ROOT+'/'+key+'/SM_'+key+'_Telescopic_Matched'
 current={str(s.material_slot_name):s.material_interface.get_path_name() if s.material_interface else None for s in target.static_materials}
 expected={s['name']:s['material'] for s in row['slots']}
 if current!=expected:raise RuntimeError('Material binding changed '+key)
 previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 try:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=C['assets'][key]['fbx'];task.destination_path=ROOT+'/'+key;task.destination_name=source.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;task.factory=u.FbxFactory();A.import_asset_tasks([task]);mesh=load(source)
 finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
 slots=list(mesh.static_materials)
 for i,slot in enumerate(slots):
  name=str(slot.material_slot_name)
  if name not in expected:raise RuntimeError('Unknown imported slot '+key+' '+name)
  slot.material_interface=load(expected[name]);slots[i]=slot
 mesh.set_editor_property('static_materials',slots);mesh.set_editor_property('nanite_settings',target.get_editor_property('nanite_settings'))
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh);settings=sms.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.remove_degenerates=True;sms.set_lod_build_settings(mesh,0,settings)
 E.set_metadata_tag(mesh,'StockMatchedSource','Original low UV0/corner normals matched in host frame; current native interface preserved 20261015')
 save(mesh);R['staged'][key]={'path':source,'sha256':sha(source)};record();print('STOCK_MATCHED_STAGED',key,flush=True)
for key,row in D['assets'].items():
 if key in R['installed']:continue
 source=load(R['staged'][key]['path']);target=load(row['path']);backup(row['path']);lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
 dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),lod)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+key)
 mats,indices,names,status=G.get_section_material_list_from_static_mesh(source,lod)
 opts=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True,replace_materials=True,new_materials=list(mats),new_material_slot_names=list(names))
 _,status=G.copy_mesh_to_static_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write '+key)
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(target);sms.set_lod_build_settings(target,0,sms.get_lod_build_settings(source,0));target.get_editor_property('asset_import_data').scripted_add_filename(C['assets'][key]['fbx'],0,'')
 E.set_metadata_tag(target,'StockMatchedSurface','20261015 original low + matched original normal; full precision UV0; host interface preserved; no R1 fairing or R2 bake')
 save(target);R['installed'][key]={'path':row['path'],'sha256':sha(row['path']),'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in target.static_materials},'preserved_interface_triangles':C['assets'][key]['preserved_interface_triangles']};record();print('STOCK_MATCHED_INSTALLED',key,flush=True)
if not R['normal']:
 backup(NORMAL);oldtex=load(NORMAL);settings={n:oldtex.get_editor_property(n) for n in ('srgb','compression_settings','flip_green_channel','lod_group','lod_bias','never_stream')}
 task=u.AssetImportTask();task.filename=C['normal']['file'];task.destination_path=NORMAL.rsplit('/',1)[0];task.destination_name=NORMAL.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task]);tex=load(NORMAL)
 for k,v in settings.items():tex.set_editor_property(k,v)
 tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
 E.set_metadata_tag(tex,'StockDetailRecipe','TelescopicAllGunsRepair20261015: original matched high-to-low bake, strength 1; replaces defective R2')
 save(tex);R['normal']={'path':NORMAL,'sha256':sha(NORMAL),'source_sha256':C['normal']['sha256'],'flip_green_channel':True,'strength':1};record()
tex=load(NORMAL)
for slot in D['assets']['A762']['slots'][1:4]:
 path=slot['material']
 if path in R['a762_materials']:continue
 mat=load(path);old=L.get_material_instance_texture_parameter_value(mat,'SurfaceNormal')
 if not old or old.get_path_name()!='/Engine/EngineMaterials/DefaultNormal.DefaultNormal':raise RuntimeError('A762 normal override changed '+path)
 backup(path);L.set_material_instance_texture_parameter_value(mat,'SurfaceNormal',tex);L.update_material_instance(mat)
 if L.get_material_instance_texture_parameter_value(mat,'SurfaceNormal')!=tex:raise RuntimeError('A762 normal assignment failed')
 save(mat);R['a762_materials'][path]={'normal':tex.get_path_name(),'saved':True};record()
R['m16_unchanged']=sha(M16)==D['accepted_m16_sha256']
if not R['m16_unchanged']:raise RuntimeError('Accepted M16 changed unexpectedly')
R['complete']=True;record();print('ALL_NINE_STOCKS_MATCHED_COMPLETE',flush=True)
