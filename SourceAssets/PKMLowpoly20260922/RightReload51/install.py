"""Install only right-arm and charge tracks into the five existing empty reloads."""
import unreal as u,json,hashlib,shutil
from pathlib import Path
P=Path(r'D:/FPS3D/FPSGAME/SourceAssets/PKMLowpoly20260922/RightReload51');root=Path('D:/FPS3D/FPSGAME');E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('Active PIE: preserve play session; animation install pending')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};entries=[json.loads((P/'Authored'/f'{f}.json').read_text()) for f in ['base','vertical','canted','prism','angled']]
for d in entries:
 disk=root/'Content'/(d['asset'].removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(disk.read_bytes()).hexdigest()!=d['source_sha256']:raise RuntimeError('Target changed since authoring: '+d['asset'])
 if d['asset'] in dirty:raise RuntimeError('Unsaved target: '+d['asset'])
receipt=[]
for d in entries:
 path=d['asset'];asset=u.load_asset(path);disk=root/'Content'/(path.removeprefix('/Game/')+'.uasset');backup=P/'Before'/disk.relative_to(root/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():shutil.copy2(disk,backup)
 controller=asset.get_editor_property('controller')
 if controller is None:controller=u.AnimDataController();controller.set_model(asset.get_editor_property('data_model_interface'))
 controller.open_bracket('PKM right cover elbow and held pull-push refinement',False)
 try:
  for bone,keys in d['tracks'].items():
   if not controller.set_bone_track_keys(bone,[u.Vector(*k['p']) for k in keys],[u.Quat(*k['q']) for k in keys],[u.Vector(*k['s']) for k in keys],False):raise RuntimeError('Cannot set '+bone)
 finally:controller.close_bracket(False)
 E.set_metadata_tag(asset,'PKMRightArmRevision','RightReload51')
 E.set_metadata_tag(asset,'PKMRightArmSource',str(P/'Authored'/(next(e['family'] for e in json.loads((P/'inputs.json').read_text()) if e['asset']==path)+'.json')))
 if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Save failed '+path)
 receipt.append(dict(asset=path,saved=True,tracks=list(d['tracks']),keys=d['keys'],duration=d['duration'],before_sha256=d['source_sha256'],after_sha256=hashlib.sha256(disk.read_bytes()).hexdigest()))
 (P/'install_receipt.json').write_text(json.dumps(dict(complete=len(receipt)==5,animations=receipt,runtime_tested=False),indent=2))
 print('PKM51_SAVED',path,flush=True)
print('PKM51_INSTALL_COMPLETE')
