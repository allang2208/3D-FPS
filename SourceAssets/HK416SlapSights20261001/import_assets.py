"""Save the independent sight section and five copied M4 slap animations."""
import unreal as u,json,re,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];C=O.parent/'HK416CommonAttachments20260930'
H='/Game/Weapons/HK416/Reworked20260930';mesh_path=H+'/SK_HK416_Manny'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong project content')
clips=json.loads((O/'animations.json').read_text())['clips'];section=json.loads((O/'sight_section.json').read_text())
targets={mesh_path}|{H+'/Animations/'+c['family']+'/'+c['name'] for c in clips.values()}
mesh=u.load_asset(mesh_path);skeleton=mesh.get_editor_property('skeleton')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & (targets|{skeleton.get_outermost().get_name()}):raise RuntimeError('Preserve unsaved HK416 mesh/animation/skeleton edits')
for path in targets:
 file=P/'Content'/(path.removeprefix('/Game/')+'.uasset');dest=O/'Before'/file.relative_to(P/'Content')
 if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,dest)
canonical=lambda s:re.sub(r'[._]\d{3}$','',str(s))
bindings={};old_slots=[]
for slot in mesh.get_editor_property('materials'):
 display=canonical(slot.material_slot_name);imported=canonical(slot.get_editor_property('imported_material_slot_name'))
 bindings[display]=slot.material_interface;bindings[imported]=slot.material_interface
 old_slots.append({'slot':display,'imported':imported,'material':slot.material_interface.get_path_name()})
receipt={'before_materials':old_slots,'animations':{},'runtime_tested':False};A=u.AssetToolsHelpers.get_asset_tools()
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed '+obj.get_path_name())
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def imported(file,name,folder,opt):
 task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False;task.options=opt
 A.import_asset_tasks([task]);obj=u.load_asset(folder+'/'+name)
 if not obj:raise RuntimeError('Import failed '+name)
 return obj
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
 opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.create_physics_asset=False;opt.skeleton=skeleton
 opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
 opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
 mesh=imported(section['mesh'],'SK_HK416_Manny',H,opt);slots=list(mesh.get_editor_property('materials'));arms=[]
 for i,slot in enumerate(slots):
  name=canonical(slot.get_editor_property('imported_material_slot_name'))
  if name in ('','None'):name=canonical(slot.material_slot_name)
  source=section['original_material'] if name==section['section'] else name
  if source not in bindings:raise RuntimeError('Missing preserved material binding '+source)
  slot.material_interface=bindings[source]
  if name.startswith('M_HK416_Factory'):slot.material_slot_name=name
  if name=='M_HK416_Stock':slot.material_slot_name='M_HK416_FactoryStock'
  slots[i]=slot
  if 'Manny' in name:arms.append(i)
 mesh.set_editor_property('materials',slots)
 u.EditorAssetLibrary.set_metadata_tag(mesh,'HK416FactorySights','Complete original front/rear sights in FactorySights; optics hide by section; UVs/materials/weights preserved')
 save(mesh);receipt['mesh']={'asset':mesh.get_path_name(),'source':section['mesh'],'saved':True,'materials':[{'slot':str(s.material_slot_name),'imported':str(s.get_editor_property('imported_material_slot_name')),'material':s.material_interface.get_path_name()} for s in slots]};record()
 # Material indices can move when adding a real section; update only this
 # weapon's existing outfit profile, keeping its current native skin choices.
 file=P/'Content/ColdSteelData/modular_outfits.json';text=file.read_text(encoding='utf-8-sig');start=text.index('{',text.index(json.dumps(mesh.get_path_name())))
 profile,n=json.JSONDecoder().raw_decode(text[start:])
 if profile['hide_source_materials']!=arms:
  profile['hide_source_materials']=arms
  if file.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Outfit profile changed during import')
  file.write_text(text[:start]+json.dumps(profile,ensure_ascii=False,indent=2).replace('\n','\n  ')+text[start+n:],encoding='utf-8')
 receipt['arm_sections']=arms;record()
 for key,c in clips.items():
  path=H+'/Animations/'+c['family']+'/'+c['name'];old=u.load_asset(path);compression=old.get_editor_property('bone_compression_settings')
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  anim=imported(c['file'],c['name'],H+'/Animations/'+c['family'],opt);anim.set_editor_property('bone_compression_settings',compression)
  u.EditorAssetLibrary.set_metadata_tag(anim,'HK416DrumEmptyRelease','20261001 V2: complete M4SlapImpact left chain; rigid contact fit; strike 116; recovery 148')
  save(anim);receipt['animations'][key]={'asset':anim.get_path_name(),'source':c['file'],'saved':True,'duration':anim.get_play_length()};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
import importlib.util
spec=importlib.util.spec_from_file_location('hk416_refresh_profiles',C/'import_grip_profiles.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
receipt['runtime_profiles']=module.refresh_empty_drum_profiles(O);record()
for name in ('models.json','animations.json'):
 file=C/name;original=file.read_text();data=json.loads(original)
 if name=='models.json':data['mesh']=section['mesh'];data['sections'][section['section']]=section['original_material']
 else:
  authored=json.loads((O/name).read_text());data['clips'].update(authored['clips']);data['reference']=authored['reference'];data['empty_drum_repair']='HK416SlapSights20261001: complete M4 slap chain'
 if file.read_text()!=original:raise RuntimeError('Source catalog changed during publication: '+name)
 file.write_text(json.dumps(data,indent=2),encoding='utf-8')
receipt['status']='mesh and five animations saved; source catalogs published';record()
print('HK416_SLAP_SIGHTS_SAVED',len(receipt['animations']),flush=True)
