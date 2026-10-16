"""Install the matched original low/normal pair for M16 only, with private finishes."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
ROOT='/Game/Weapons/M16A2/TelescopicMatchedSurface20261015'
TARGET='/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_tactical_telescopic'
SOURCE=ROOT+'/Meshes/SM_M16_Telescopic_MatchedSource'
WET='/Game/Weapons/M16A2/UniversalAttachments20260920/DA_M16_AttachmentWetMaterials'
C=json.loads((O/'production.json').read_text())
old=json.loads((P/'SourceAssets/M16StockDonor20261015/install_receipt.json').read_text())
expected=json.loads((P/'SourceAssets/TelescopicHardSurface20261015/install_receipt.json').read_text())['installed']['sha256']
RP=O/'install_receipt.json';R=json.loads(RP.read_text()) if RP.exists() else {'complete':False,'materials':{},'saved':[],'gameplay_tested':False}
def record():RP.write_text(json.dumps(R,indent=2),encoding='utf-8')
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
 if a.get_path_name() not in R['saved']:R['saved'].append(a.get_path_name())
 record()
def backup(path):
 dst=O/'Before'/(path.removeprefix('/Game/')+'.uasset');dst.parent.mkdir(parents=True,exist_ok=True)
 if not dst.exists():shutil.copy2(disk(path),dst)
def duplicate(src,path):
 obj=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(src,path)
 if not obj:raise RuntimeError('Duplicate failed '+path)
 return obj
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if TARGET in dirty or WET in dirty:raise RuntimeError('Preserve unsaved M16 stock/weather assets')
if not R.get('installed') and sha(TARGET)!=expected:raise RuntimeError('M16 stock changed since this task last installed it')
target=load(TARGET);backup(TARGET);backup(WET)
normal_path=ROOT+'/Textures/T_M16_Telescopic_MatchedNormal'
if not R.get('normal'):
 task=u.AssetImportTask();task.filename=C['normal_export'];task.destination_path=ROOT+'/Textures';task.destination_name=normal_path.rsplit('/',1)[1]
 task.automated=True;task.replace_existing=True;task.save=False;task.factory=u.TextureFactory();A.import_asset_tasks([task])
 tex=load(normal_path);tex.set_editor_property('srgb',False);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
 tex.set_editor_property('flip_green_channel',True);tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON);tex.set_editor_property('lod_bias',0)
 E.set_metadata_tag(tex,'MatchedStockNormal','Original 20260914 high-to-low bake, paired with original low; no R1 fairing or R2 rebake')
 save(tex);R['normal']={'path':tex.get_path_name(),'source_sha256':C['normal_sha256'],'flip_green_channel':True,'strength':1};record()
tex=load(normal_path)
old_normal='/Game/Weapons/TacticalTelescopicStock20260914/Textures/T_TacticalStock_Normal_Game'
def clone_finish(source_path,key):
 path=ROOT+'/Materials/'+key
 if path in R['materials']:return load(path)
 source=load(source_path)
 if isinstance(source,u.MaterialInstanceConstant):
  parent=source.get_base_material();graph=duplicate(parent.get_path_name(),ROOT+'/Master/M_'+key)
  material=duplicate(source_path,path);L.set_material_instance_parent(material,graph)
 else:graph=material=duplicate(source_path,path)
 changed=0
 for node in L.get_material_expressions(graph):
  if isinstance(node,u.MaterialExpressionTextureSample):
   oldtex=node.get_editor_property('texture')
   if oldtex and oldtex.get_path_name().split('.')[0]==old_normal:
    node.set_editor_property('texture',tex);node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL);changed+=1
 if not changed:raise RuntimeError('Expected stock normal sampler absent from '+source_path)
 L.recompile_material(graph);save(graph)
 if isinstance(material,u.MaterialInstanceConstant):L.update_material_instance(material)
 E.set_metadata_tag(material,'MatchedStockSource',source_path);save(material)
 R['materials'][path]={'source':source_path,'path':material.get_path_name(),'normal_nodes_replaced':changed,'base':graph.get_path_name()};record()
 return material
bindings={name:load(path) for name,path in old['materials'].items() if name in ('M16_InterfaceMetal','TacticalStock_Adapter_M4')}
weather=load(WET);mapping=dict(weather.get_editor_property('wet_materials'))
for name,key in [('TacticalStock_Metal_M4','MI_M16_Telescopic_Metal'),('TacticalStock_Polymer_M4','MI_M16_Telescopic_Polymer'),('TacticalStock_Rubber_M4','M_M16_Telescopic_Rubber')]:
 original=old['materials'][name];mat=clone_finish(original,key);bindings[name]=mat
 params={str(n) for n in L.get_scalar_parameter_names(mat.get_base_material())}
 if 'WeaponWetness' in params:mapping[mat.get_path_name()]=mat
 elif original in mapping and mapping[original]:
  wet=clone_finish(mapping[original].get_path_name(),key+'_Wet');mapping[mat.get_path_name()]=wet
weather.set_editor_property('wet_materials',mapping);save(weather);R['weather']=weather.get_path_name();record()
sms=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
if not R.get('source_mesh'):
 previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
 try:
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
  opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
  imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
  task=u.AssetImportTask();task.filename=C['mesh_export'];task.destination_path=ROOT+'/Meshes';task.destination_name=SOURCE.rsplit('/',1)[1];task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
  A.import_asset_tasks([task]);mesh=load(SOURCE)
 finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
 slots=list(mesh.static_materials)
 for i,slot in enumerate(slots):
  name=str(slot.material_slot_name)
  if name not in bindings:raise RuntimeError('Unmapped '+name)
  slot.material_interface=bindings[name];slots[i]=slot
 mesh.set_editor_property('static_materials',slots);mesh.set_editor_property('nanite_settings',target.get_editor_property('nanite_settings'))
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
 settings=sms.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;sms.set_lod_build_settings(mesh,0,settings)
 save(mesh);R['source_mesh']={'path':SOURCE,'sha256':sha(SOURCE)};record()
source=load(SOURCE)
if not R.get('installed'):
 G=u.GeometryScript_AssetUtils;lod=u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL)
 dm,status=G.copy_mesh_from_static_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,request_tangents=True),lod)
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read imported mesh')
 mats,indices,names,status=G.get_section_material_list_from_static_mesh(source,lod)
 options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,use_original_vertex_order=True,replace_materials=True,new_materials=list(mats),new_material_slot_names=list(names))
 _,status=G.copy_mesh_to_static_mesh(dm,target,options,u.GeometryScriptMeshWriteLOD())
 if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot install M16 stock')
 u.ASH12AttachmentAssetTools.disable_runtime_fast_build(target);sms.set_lod_build_settings(target,0,sms.get_lod_build_settings(source,0))
 target.get_editor_property('asset_import_data').scripted_add_filename(C['mesh_export'],0,'')
 E.set_metadata_tag(target,'M16StockSurfaceRecovery','20261015: restored original low and matching original normal; M16 interface preserved; private materials; R2 diamonds excluded')
 E.set_metadata_tag(target,'M16StockRebuild','Superseded by TelescopicMatchedSurface20261015; original shape restored')
 save(target);R['installed']={'path':TARGET,'sha256':sha(TARGET),'triangles':C['triangles'],'materials':{str(s.material_slot_name):s.material_interface.get_path_name() for s in target.static_materials}};record()
task=u.AssetExportTask();task.object=target;task.filename=str(O/'Final/SM_M16_Telescopic_SavedUE.fbx');task.automated=True;task.prompt=False;task.replace_identical=True;task.options=u.FbxExportOption();task.options.level_of_detail=False
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Saved UE export failed')
R['saved_mesh_export']=task.filename
manifest=P/'SourceAssets/WeaponSurface20260930/M16/current_surface_bindings.json';backup_manifest=O/'Before/current_surface_bindings.json'
if not backup_manifest.exists():shutil.copy2(manifest,backup_manifest)
d=json.loads(manifest.read_text(encoding='utf-8'));d['meshes'][target.get_path_name()]=R['installed']['materials'];manifest.write_text(json.dumps(d,indent=2,ensure_ascii=False),encoding='utf-8')
R.update(binding_manifest=str(manifest),complete=True);record();print('M16_MATCHED_SURFACE_INSTALLED',TARGET,flush=True)
