"""Save the six joint-only profile patches after checking the captured inputs."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,zipfile,struct,datetime
r=Path(__file__).resolve().parent;project=r.parents[2];prior=r.parent/'Wrist33';follow=prior/'Followup'
expected=json.loads((follow/'state.json').read_text())['saved_hashes']|json.loads((follow/'entry_saved.json').read_text())['saved']
paths={f:'/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+f for f in ('vertical','angled','canted','prism')}
paths.update(base='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip',bipod='/Game/Weapons/M249/Bipod/DA_M249_Bipod')
def disk(p):return project/'Content'/(p.removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(disk(p).read_bytes()).hexdigest()
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def matches(asset,payload):
    def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
    clips=asset.get_editor_property('clips')
    if len(clips)!=len(payload['clips']):return False
    for a,b in zip(clips,payload['clips']):
        if a.get_editor_property('base').get_path_name()!=b['base'] or a.get_editor_property('duration')!=f32(b['duration']):return False
        retained=a.get_editor_property('retained');source=b.get('retained')
        if (retained.get_path_name() if retained else None)!=(source if source else None):return False
        tracks=a.get_editor_property('tracks')
        if len(tracks)!=len(b['tracks']):return False
        for x,y in zip(tracks,b['tracks']):
            if str(x.get_editor_property('bone'))!=y['bone'] or list(x.get_editor_property('times'))!=list(map(f32,y['times'])) or list(x.get_editor_property('values'))!=list(map(f32,y['values'])):return False
    return True
saved=json.loads((r/'install_receipt.json').read_text())['saved'] if (r/'install_receipt.json').exists() else {}
for family,p in paths.items():
    if p in dirty:raise RuntimeError('Dirty input retained '+p)
    if sha(p)!=saved.get(p,expected[p]):
        # The first install reached vertical in a user-opened PIE. It was left
        # dirty when saving was denied; the user may subsequently save it.
        if family!='vertical' or not matches(u.load_asset(p),json.load(gzip.open(r/(family+'.json.gz'),'rt'))):raise RuntimeError('Input changed; preserved '+p)
        saved[p]=sha(p)
if (r/'before.zip').exists():
    with zipfile.ZipFile(r/'before.zip') as backup:
        for p in paths.values():
            name=str(disk(p).relative_to(project)).replace('\\','/')
            if hashlib.sha256(backup.read(name)).hexdigest()!=expected[p]:raise RuntimeError('Backup identity mismatch '+p)
else:
    with zipfile.ZipFile(r/'before.zip','x',zipfile.ZIP_DEFLATED) as out:
        for p in paths.values():out.write(disk(p),str(disk(p).relative_to(project)))
updates={}
for family,path in paths.items():
    payload=json.load(gzip.open(r/(family+'.json.gz'),'rt'));asset=u.load_asset(path)
    if path in saved and matches(asset,payload):continue
    updates[family]=(path,payload,asset)
revisions=[path for path,payload,asset in updates.values() if path in saved]
if revisions:
    with zipfile.ZipFile(r/('before-revision-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip'),'x',zipfile.ZIP_DEFLATED) as backup:
        for path in revisions:backup.write(disk(path),str(disk(path).relative_to(project)))
for family,(path,payload,asset) in updates.items():
    if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Import '+path)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save '+path)
    if not matches(asset,payload):raise RuntimeError('Saved values mismatch '+path)
    saved[path]=sha(path)
    (r/'install_receipt.json').write_text(json.dumps(dict(saved=saved,complete=len(saved)==6),indent=2))
(r/'install_receipt.json').write_text(json.dumps(dict(saved=saved,complete=len(saved)==6),indent=2))
print('M249_JOINT_ONLY_SAVED',len(saved))
