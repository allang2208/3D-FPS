"""Read back exact saved root tracks; all prior local animation stays intact."""
from pathlib import Path
import unreal as u,json,pickle,gzip,struct,hashlib
r=Path(__file__).resolve().parent;project=r.parents[2];old=pickle.load(open(r/'current.pkl','rb'));after={};report={}
def f32(x):return struct.unpack('f',struct.pack('f',x))[0]
def record(asset):
 result=[]
 for c in asset.get_editor_property('clips'):
  get=c.get_editor_property;retained=get('retained')
  result.append(dict(base=get('base').get_path_name(),retained=retained.get_path_name()if retained else None,duration=get('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values')))for t in get('tracks')]))
 return result
for family,p in old['profiles'].items():
 a=u.load_asset(p['asset']);rows=record(a);expected={c['base']:c for c in json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips']}
 for before in p['clips']:
  current=next(c for c in rows if c['base']==before['base'])
  if before['base']not in expected:
   if current!=before:raise RuntimeError('Unrelated clip changed '+family+'/'+before['base'])
   continue
  target=expected[before['base']];kept=lambda c:[t for t in c['tracks']if t['bone']!='root']
  if kept(current)!=kept(before)or current['duration']!=before['duration']or current['retained']!=before['retained']:raise RuntimeError('Original motion changed '+family)
  saved_root=next(t for t in current['tracks']if t['bone']=='root');target_root=next(t for t in target['tracks']if t['bone']=='root')
  if saved_root['times']!=[f32(x)for x in target_root['times']]or saved_root['values']!=[f32(x)for x in target_root['values']]:raise RuntimeError('Saved root differs '+family)
 after[family]=dict(asset=p['asset'],clips=rows);report[family]=dict(reloads=len(expected),original_tracks_unchanged=True,other_actions_unchanged=True,saved_root_matches=True)
for path,sha in json.loads((r/'inputs.json').read_text())['hashes'].items():
 if '/Animations/'in path or path.endswith('SK_M249_V7'):
  disk=project/'Content'/(path.removeprefix('/Game/')+'.uasset')
  if hashlib.sha256(disk.read_bytes()).hexdigest()!=sha:raise RuntimeError('Base asset changed '+path)
pickle.dump(after,open(r/'saved_profiles.pkl','wb'));(r/'saved_verification.json').write_text(json.dumps(report,indent=2));print('FEEDBACK31_VERIFIED',len(report),'profiles; original joints, timing and other actions unchanged',flush=True)
