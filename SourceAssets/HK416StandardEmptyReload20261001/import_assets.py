"""Save HK416 standard/extended empty reload and its four runtime grip layers."""
import unreal as u,json,shutil,importlib.util
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];C=O.parent/'HK416CommonAttachments20260930'
H='/Game/Weapons/HK416/Reworked20260930'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()!=(P/'Content').resolve():raise RuntimeError('Wrong project content')
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE is active; preserve the running session')
clips=json.loads((O/'animations.json').read_text())['clips']
if set(clips)!={f+'/reload_empty' for f in ('base','vertical','canted','prism','angled')}:raise RuntimeError('Unexpected standard-empty import scope')
targets={H+'/Animations/'+c['family']+'/'+c['name'] for c in clips.values()}
profiles={'/Game/Weapons/AnimationProfiles20261001/ue_hk416/DA_'+f for f in ('vertical','canted','prism','angled','drum')}
mesh=u.load_asset(H+'/SK_HK416_Manny');skeleton=mesh.get_editor_property('skeleton')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & (targets|profiles|{skeleton.get_outermost().get_name()}):raise RuntimeError('Preserve unsaved HK416 animation/profile edits')
for path in targets:
 source=P/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=O/'Before'/source.relative_to(P/'Content')
 if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
receipt={'animations':{},'runtime_tested':False,'magazines':['factory','ext_mag'],'source_strike_frame':130,'source_end_frame':162}
def record():(O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
A=u.AssetToolsHelpers.get_asset_tools();flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 for key,c in clips.items():
  path=H+'/Animations/'+c['family']+'/'+c['name'];old=u.load_asset(path)
  if not old:raise RuntimeError('Missing active HK416 clip '+path)
  compression=old.get_editor_property('bone_compression_settings')
  opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
  opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
  opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
  task=u.AssetImportTask();task.filename=c['file'];task.destination_path=H+'/Animations/'+c['family'];task.destination_name=c['name']
  task.automated=True;task.replace_existing=True;task.save=False;task.options=opt;A.import_asset_tasks([task])
  anim=u.load_asset(path);anim.set_editor_property('bone_compression_settings',compression)
  u.EditorAssetLibrary.set_metadata_tag(anim,'HK416StandardEmptyRelease','20261001: factory/ext_mag; M4 complete arm; native contact fit; strike 130; grip recovery 142..162')
  if not u.EditorLoadingAndSavingUtils.save_packages([anim.get_outermost()],False):raise RuntimeError('Save failed '+path)
  receipt['animations'][key]={'asset':anim.get_path_name(),'source':c['file'],'saved':True,'duration':anim.get_play_length()};record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
spec=importlib.util.spec_from_file_location('hk416_standard_profiles',C/'import_grip_profiles.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
receipt['runtime_profiles']=module.refresh_empty_profiles(O,'reload_empty');record()
file=C/'animations.json';text=file.read_text();catalog=json.loads(text);catalog['clips'].update(clips)
catalog['standard_empty_repair']='HK416StandardEmptyReload20261001: factory and extended magazines; complete M4 slap and runtime grip layers'
catalog['reference']=json.loads((O/'animations.json').read_text())['reference']
if file.read_text()!=text:raise RuntimeError('Animation catalog changed during publication')
file.write_text(json.dumps(catalog,indent=2),encoding='utf-8')
receipt['status']='five standard/extended empty animations and runtime grip layers saved';record()
print('HK416_STANDARD_EXTENDED_EMPTY_SAVED',len(receipt['animations']),flush=True)
