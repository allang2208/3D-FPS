"""Rebake runtime profile entries when authored HK416 actions change."""
import unreal as u,shutil
from pathlib import Path

def refresh_empty_drum_profiles(output):
 return refresh_empty_profiles(output,'drum_reload_empty')

def refresh_empty_profiles(output,kind='reload_empty'):
 return refresh_profiles(output,kind)

def refresh_inspect_profiles(output):
 return refresh_profiles(output,'inspect')

def refresh_profiles(output,kind):
 output=Path(output);P=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()
 H='/Game/Weapons/HK416/Reworked20260930/Animations';D='/Game/Weapons/AnimationProfiles20261001/ue_hk416'
 base=u.load_asset(H+'/base/A_HK416_base_'+kind)
 dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()};report={}
 for family in ('vertical','canted','prism','angled','drum'):
  path=D+'/DA_'+family;profile=u.load_asset(path)
  if not profile:continue # Older projects still play their authored family clips.
  if path in dirty:raise RuntimeError('Preserve unsaved grip profile '+path)
  layers=list(profile.get_editor_property('clips'));old=next((x for x in layers if x.get_editor_property('base')==base),None)
  had_clip=old is not None;previous_duration=float(old.get_editor_property('duration')) if had_clip else None
  # BakeClip replaces entries in Clips; release reflected struct views before mutation.
  del old,layers
  if family=='drum' and kind!='inspect' and not had_clip:
   report[family]={'asset':profile.get_path_name(),'changed':False,'reason':'No empty-reload correction; uses the base animation'};continue
  authored=base if family=='drum' and kind!='inspect' else u.load_asset(H+'/'+family+'/A_HK416_'+family+'_'+kind)
  if not authored:raise RuntimeError('Missing authored empty-reload clip '+family+'/'+kind)
  backup=output/'Before'/(path.removeprefix('/Game/')+'.uasset')
  if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(P/(path.removeprefix('/Game/')+'.uasset'),backup)
  if not profile.bake_clip(base,authored):raise RuntimeError('Could not bake HK416 correction '+family+'/'+kind)
  tag='HK416InspectSource' if kind=='inspect' else 'HK416DrumEmptySource' if kind=='drum_reload_empty' else 'HK416StandardEmptySource'
  note='AKM/SVD rifle inspection trajectory / HK416 native held chain' if kind=='inspect' else 'M4SlapImpact whole chain / HK416 native contact'
  u.EditorAssetLibrary.set_metadata_tag(profile,tag,note+'; updated layer: '+kind)
  if not u.EditorLoadingAndSavingUtils.save_packages([profile.get_outermost()],False):raise RuntimeError('Save failed '+path)
  report[family]={'asset':profile.get_path_name(),'changed':True,'saved':True,'base':base.get_path_name(),'authored':authored.get_path_name(),'duration':base.get_play_length(),'previous_duration':previous_duration}
 return report
