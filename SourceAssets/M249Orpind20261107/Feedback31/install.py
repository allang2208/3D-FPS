"""Save root-only reload feedback, preserving all current hand/weapon tracks."""
from pathlib import Path
import unreal as u,json,gzip,pickle,hashlib,zipfile
r=Path(__file__).resolve().parent;project=r.parents[2];receipt=r/'install_receipt.json';baseline=pickle.load(open(r/'current.pkl','rb'))
profiles={f:p['asset'].split('.')[0]for f,p in baseline['profiles'].items()}
def disk(p):return project/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
auth=json.loads((r/'authoring.json').read_text())
if len(auth)!=10 or any(v['grip_relative_error']>1e-5 or v['entry_exit_error']>1e-3 or v['changed_tracks']!=['root']or v['root_motion']for v in auth.values()):raise RuntimeError('Root-only feedback contract failed')
for family,p in baseline['profiles'].items():
 for new in json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips']:
  old=next(c for c in p['clips']if c['base']==new['base'])
  if [t for t in new['tracks']if t['bone']!='root']!=[t for t in old['tracks']if t['bone']!='root']or new['duration']!=old['duration']:raise RuntimeError('Existing action changed: '+family)
if '-run='not in u.SystemLibrary.get_command_line().lower()and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; prepared feedback retained')
dirty={p.get_path_name()for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(profiles.values()):raise RuntimeError('Unsaved target profile retained')
original=json.loads((r/'inputs.json').read_text())['hashes'];previous=json.loads(receipt.read_text())['saved']if receipt.exists()else {}
for path,expected in original.items():
 if sha(path)!=previous.get(path,expected):raise RuntimeError('Changed input retained: '+path)
if not(r/'Before.zip').exists():
 with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED)as z:
  for path in profiles.values():z.write(disk(path),str(disk(path).relative_to(project)))
report=dict(saved={},complete=False,changed_tracks=['root'],base_sequences_changed=False)
for family,path in profiles.items():
 a=u.load_asset(path);incoming=json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips'];keys={c['base'].split('.')[0]for c in incoming};rows=[];retained=[]
 for c in a.get_editor_property('clips'):
  base,keep=c.get_editor_property('base'),c.get_editor_property('retained')
  if base.get_path_name().split('.')[0]in keys:continue
  if keep:retained.append((base,keep));continue
  rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values')))for t in c.get_editor_property('tracks')]))
 if not a.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):raise RuntimeError('Profile '+family)
 for base,keep in retained:a.keep_clip(base,keep)
 if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Save '+path)
 report['saved'][path]=sha(path);receipt.write_text(json.dumps(report,indent=2));print('FEEDBACK31_SAVED',family,flush=True)
report['complete']=True;receipt.write_text(json.dumps(report,indent=2))
