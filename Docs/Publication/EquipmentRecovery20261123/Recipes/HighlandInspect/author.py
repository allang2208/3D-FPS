from pathlib import Path
import hashlib,json
import unreal as u
W=Path('F:/FPSGAME-Recovery-Work-20261120/HighlandInspectR6b20261121')
project=Path('D:/FPS3D/FPSGAME');S=project/'SourceAssets/RuneSword20260913/InspectReverseV85'
job=json.loads((W/'job.json').read_bytes())
receipt=json.loads((S/'import_receipt_v85.json').read_bytes())
original_script=S/'import_inspect_v85.py'
text=original_script.read_text(encoding='utf8')
start=text.index('        compression = current.')
end=text.index('        authored = restore_idle',start)
from textwrap import dedent
import_part=compile(dedent(text[start:end]),str(original_script),'exec')
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
if mesh is None:raise RuntimeError('Sword skeleton donor missing')
NAME='A_RuneSword_Inspect'
flag='Interchange.FeatureFlags.Import.FBX'
previous_flag=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
saved={}
def pkg(asset):return asset.get_path_name().split('.')[0] if asset else None
def save(obj):
 if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_package()],False):raise RuntimeError('Save failed '+obj.get_path_name())
try:
 for row in receipt['assets']:
  variant=row['variant'];path=row['asset'];dest=path.rsplit('/',1)[0]
  source=Path(row['author_fbx']);full=Path(row['full_fbx']);handoff=Path(row['handoff_keys'])
  data=json.loads(handoff.read_bytes())
  current=u.load_asset(path)
  exec(import_part,globals())
  model=sequence.get_editor_property('data_model_interface')
  frames=model.get_number_of_frames()
  duration=sequence.get_play_length()
  if frames!=139 or abs(duration-row['seconds'])>0.00001 or len(data['samples'])!=frames+1:raise RuntimeError('Unexpected R6b frame data')
  ctrl=sequence.get_editor_property('controller')
  ctrl.open_bracket('Restore published R6b inspect idle handoff',False)
  try:
   for name in data['edited_bones']:
    keys=[r['bones'][name] for r in data['samples']]
    if not ctrl.set_bone_track_keys(name,[u.Vector(*a['p']) for a in keys],[u.Quat(*a['q']) for a in keys],[u.Vector(*a['s']) for a in keys],False):raise RuntimeError(name)
  finally:ctrl.close_bracket(False)
  importer=sequence.get_editor_property('asset_import_data')
  importer.scripted_add_filename(str(full),0,'V85 with current idle handoff')
  save(sequence)
  saved[path]=dict(variant=variant,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),final_fbx=str(full),handoff=str(handoff),handoff_sha256=hashlib.sha256(handoff.read_bytes()).hexdigest(),frames=frames,seconds=duration,baseline_sha256=row['after_sha256'])
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous_flag))
profile=u.load_asset(job['profile'])
if not profile or str(profile.get_editor_property('family'))!='Sword_LongGrip':raise RuntimeError('Wrong profile')
def clips():return list(profile.get_editor_property('clips'))
def role(c):return pkg(c.get_editor_property('base'))
def others():return {role(c):c.export_text() for c in clips() if role(c)!=job['standard']}
other_clips=others()
if None in other_clips or sum(role(c)==job['standard'] for c in clips())!=1:raise RuntimeError('Incomplete existing long grip profile')
if not profile.bake_clip(u.load_asset(job['standard']),u.load_asset(job['long_grip'])):raise RuntimeError('Failed to bake R6b left arm')
if others()!=other_clips:raise RuntimeError('Another grip entry changed')
layer=next(c for c in clips() if role(c)==job['standard'])
tracks=[str(t.get_editor_property('bone')) for t in layer.get_editor_property('tracks')]
if layer.get_editor_property('retained') or abs(layer.get_editor_property('duration')-139/120)>0.00001 or not tracks:raise RuntimeError('Incomplete inspect layer')
save(profile)
saved[job['profile']]=dict(role='Inspect',bones=tracks,seconds=layer.get_editor_property('duration'),remaining_clips_preserved=len(other_clips))
(W/'saved.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
u.log('INSPECT_R6B_RECOVERED '+str(tracks))
