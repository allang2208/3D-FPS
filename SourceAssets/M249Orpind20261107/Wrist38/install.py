"""Install the right-approach correction over the exact saved W37 profiles."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,zipfile,struct,datetime
root=Path(__file__).resolve().parent;project=root.parents[2]
expected={p:v['after'] for p,v in json.loads((root.parent/'Wrist37/assets-after.json').read_text()).items()}
paths={f:'/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+f for f in ['vertical','angled','canted','prism']}
paths['base']='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip'
disk=lambda p:project/'Content'/(p.removeprefix('/Game/')+'.uasset')
sha=lambda p:hashlib.sha256(disk(p).read_bytes()).hexdigest()
saved=json.loads((root/'install_receipt.json').read_text())['saved'] if (root/'install_receipt.json').exists() else {}
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for p,h in expected.items():
    if sha(p)!=saved.get(p,h):raise RuntimeError('Changed input retained '+p)
for p in paths.values():
    if p in dirty:raise RuntimeError('Dirty input retained '+p)
backup=root/('before-revision-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip')
with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
    for p in paths.values():z.write(disk(p),str(disk(p).relative_to(project)))
for family,path in paths.items():
    payload=json.load(gzip.open(root/(family+'.json.gz'),'rt'));asset=u.load_asset(path)
    if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Import failed '+path)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
    f32=lambda x:struct.unpack('f',struct.pack('f',x))[0]
    clips=asset.get_editor_property('clips')
    if len(clips)!=len(payload['clips']):raise RuntimeError('Clip count mismatch')
    for actual,src in zip(clips,payload['clips']):
        if actual.get_editor_property('base').get_path_name()!=src['base']:raise RuntimeError('Base mismatch')
        tracks=actual.get_editor_property('tracks')
        if len(tracks)!=len(src['tracks']):raise RuntimeError('Track count mismatch')
        for a,b in zip(tracks,src['tracks']):
            if str(a.get_editor_property('bone'))!=b['bone'] or list(a.get_editor_property('times'))!=list(map(f32,b['times'])) or list(a.get_editor_property('values'))!=list(map(f32,b['values'])):
                raise RuntimeError('Saved track mismatch')
    saved[path]=sha(path)
    (root/'install_receipt.json').write_text(json.dumps(dict(saved=saved,complete=len(saved)==5),indent=2))
(root/'assets-after.json').write_text(json.dumps({p:dict(before=h,after=sha(p),unchanged=h==sha(p)) for p,h in expected.items()},indent=2))
print('M249_WRIST38_SAVED',len(saved))
