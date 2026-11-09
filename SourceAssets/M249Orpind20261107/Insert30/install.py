from pathlib import Path
import unreal as u,json,gzip,hashlib,zipfile
r=Path(__file__).resolve().parent;project=r.parents[2];receipt=r/'install_receipt.json'
profiles={f:('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if f=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+f)for f in ['base','vertical','canted','prism','angled']}
def disk(p):return project/'Content'/(p.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
auth=json.loads((r/'publication.json').read_text())
if len(auth)!=10 or any(v['protected_world_error']>1e-9 or v['arm_length_error_cm']>1e-6 for v in auth.values()):raise RuntimeError('Arm-only limits exceeded')
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; prepared correction retained')
dirty={a.get_path_name()for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(profiles.values()):raise RuntimeError('Unsaved target retained')
original=json.loads((r/'inputs.json').read_text())['hashes'];previous=json.loads(receipt.read_text())['saved'] if receipt.exists()else {}
for path,expected in original.items():
 if sha(path)!=previous.get(path,expected):raise RuntimeError('Changed input retained: '+path)
if not(r/'Before.zip').exists():
 with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED)as z:
  for path in profiles.values():z.write(disk(path),str(disk(path).relative_to(project)))
report=dict(saved={},complete=False)
for family,path in profiles.items():
 a=u.load_asset(path);incoming=json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips'];keys={c['base'].split('.')[0]for c in incoming};rows=[];kept=[]
 for c in a.get_editor_property('clips'):
  base,retained=c.get_editor_property('base'),c.get_editor_property('retained')
  if base.get_path_name().split('.')[0]in keys:continue
  if retained:kept.append((base,retained));continue
  rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values')))for t in c.get_editor_property('tracks')]))
 if not a.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):raise RuntimeError('Profile '+family)
 for base,retained in kept:a.keep_clip(base,retained)
 if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Save '+path)
 report['saved'][path]=sha(path);receipt.write_text(json.dumps(report,indent=2));print('INSERT30_SAVED',family,flush=True)
report['complete']=True;receipt.write_text(json.dumps(report,indent=2))
