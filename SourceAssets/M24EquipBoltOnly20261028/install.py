"""Replace only M24 equip animation and its two profile entries."""
import unreal as u,json,copy,ast,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
node=next(n for n in ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='packed');exec(compile(ast.unparse(node),'pack','exec'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; assets not modified')
before=json.loads((O/'before.json').read_text());equip_package=before['equip']['path'];equip_path=equip_package+'.A_M24_equip'
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in [*paths.values(),equip_package]):raise RuntimeError('Unsaved M24 target retained')
live={f:u.load_asset(p) for f,p in paths.items()};current={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(current)
def disk(path):return Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
if hashlib.sha256(disk(equip_path).read_bytes()).hexdigest()!=before['equip']['sha256']:raise RuntimeError('Concurrent equip asset change retained')
for family,p in live.items():
 if any(c.get_editor_property('retained') is not None for c in p.get_editor_property('clips')):raise RuntimeError('Retained profile clip requires separate merge')
 previous=next(c for c in before['profiles'][family]['clips'] if c['base']==equip_path);target=next(c for c in spec[family]['clips'] if c['base']==equip_path)
 if target!=previous:raise RuntimeError('Concurrent equip profile change retained')
 target.update(duration=58/30,tracks=[])
backup=O/'Backups';backup.mkdir(exist_ok=True)
for path in [*paths.values(),equip_path]:
 src=disk(path);dest=backup/src.name
 if not dest.exists():shutil.copy2(src,dest)
for family in current:(backup/(family+'.json')).write_text(json.dumps(current[family]))
receipt={'complete':False,'saved':[],'scope':'equip only; reload clips and profile entries preserved','runtime_tested':False}
def record():(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 receipt['saved'].append({'path':asset.get_path_name(),'sha256':hashlib.sha256(disk(asset.get_path_name()).read_bytes()).hexdigest()});record()
mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9');skeleton=mesh.skeleton
if skeleton.get_path_name().split('.')[0] in dirty:raise RuntimeError('Shared skeleton has unsaved edits')
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
 opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;opt.import_mesh=False;opt.import_animations=True;opt.import_materials=False;opt.import_textures=False;opt.skeleton=skeleton
 opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
 t=u.AssetImportTask();t.filename=str(O/'Export/A_M24_equip.fbx');t.destination_path=equip_package.rsplit('/',1)[0];t.destination_name='A_M24_equip';t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory();t.options=opt;A.import_asset_tasks([t])
 clip=u.load_asset(equip_path)
 if not clip:raise RuntimeError('Equip import failed')
 clip.set_editor_property('bone_compression_settings',u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(clip)
 for family,p in live.items():
  if not p.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Profile merge failed '+family)
  save(p)
 receipt['equip_seconds']=clip.get_play_length();receipt['complete']=True;record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
print('M24_EQUIP_BOLT_ONLY_SAVED',json.dumps(receipt),flush=True)
