from pathlib import Path
import unreal as u,json,gzip,hashlib
r=Path(__file__).resolve().parent;p=r.parents[2];receipt=r/'install_receipt.json';report=json.loads(receipt.read_text());E=u.EditorAssetLibrary
for family in ['base','vertical','canted','prism','angled']:
 path='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family
 disk=p/'Content'/(path.removeprefix('/Game/')+'.uasset')
 if hashlib.sha256(disk.read_bytes()).hexdigest()!=report['saved'][path]:raise RuntimeError('Changed profile retained '+path)
 a=u.load_asset(path);incoming=json.load(gzip.open(r/('idle_'+family+'.json.gz'),'rt'))['clips'];keys={c['base'] for c in incoming};rows=[];kept=[]
 for c in a.get_editor_property('clips'):
  v=c.get_editor_property;base=v('base');retained=v('retained')
  if base.get_path_name().split('.')[0] in keys:continue
  if retained:kept.append((base,retained));continue
  rows.append(dict(base=base.get_path_name(),duration=v('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in v('tracks')]))
 if not a.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):raise RuntimeError('Profile '+family)
 for base,retained in kept:a.keep_clip(base,retained)
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+path)
 report['saved'][path]=hashlib.sha256(disk.read_bytes()).hexdigest();receipt.write_text(json.dumps(report,indent=2))
report['idle_loop_repaired']=True;receipt.write_text(json.dumps(report,indent=2));print('M249_IDLE_LOOP_SAVED',flush=True)
