"""Save ten scoped native reload assets; do not launch PIE or evaluate tests."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
info=json.loads((O/'authoring.json').read_text());receipt={}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Active game: preserve session, cannot save reload assets')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def sha(path):return hashlib.sha256((P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
for key,spec in info['clips'].items():
 path=spec['destination']
 if path in dirty or spec['source'] in dirty:raise RuntimeError('Unsaved target/source '+key)
 if sha(spec['source'])!=spec['source_sha256']:raise RuntimeError('Source changed during production '+key)
 clip=u.load_asset(path)
 if not clip:
  folder,name=path.rsplit('/',1);E.make_directory(folder);clip=A.duplicate_asset(name,folder,u.load_asset(spec['source']))
 if not clip:raise RuntimeError('Cannot create '+path)
 model=clip.get_editor_property('data_model_interface');controller=clip.get_editor_property('controller');tracks=json.loads(Path(spec['keys']).read_text())
 controller.open_bracket('201 factory magazine contact and release',False)
 try:
  for n,rows in tracks.items():
   if not model.is_valid_bone_track_name(n):controller.add_bone_curve(n,False)
   if not controller.set_bone_track_keys(n,[u.Vector(*v['p']) for v in rows],[u.Quat(*v['q']) for v in rows],[u.Vector(*v['s']) for v in rows],False):raise RuntimeError('Cannot write '+n)
 finally:controller.close_bracket(False)
 E.set_metadata_tag(clip,'LMG201ReloadRevision','Magazine24: factory magazine only; SVD partial wrap; complete native FK chain; delayed grip return')
 E.set_metadata_tag(clip,'SourceAnimation',spec['source']);E.set_metadata_tag(clip,'SourceSHA256',spec['source_sha256'])
 u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
 if not E.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
 receipt[key]={'asset':clip.get_path_name(),'saved':True,'sha256':sha(path),'source':spec['source'],'runtime_tested':False}
 (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2));print('MAGAZINE24_SAVED',key,flush=True)
print('MAGAZINE24_IMPORT_COMPLETE',len(receipt),flush=True)
