"""Install only the prism joint tracks, with hash guard and recoverable backup."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,zipfile,datetime
root=Path(__file__).resolve().parent;project=root.parents[2]
path='/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_prism'
disk=project/'Content'/(path.removeprefix('/Game/')+'.uasset')
sha=lambda:hashlib.sha256(disk.read_bytes()).hexdigest()
expected=json.loads((root.parent/'Wrist34/install_receipt.json').read_text())['saved'][path]
if any(p.get_path_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Dirty prism asset retained')
if sha()!=expected:raise RuntimeError('Prism source changed; retained '+path)
with zipfile.ZipFile(root/('before-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip'),'x',zipfile.ZIP_DEFLATED) as backup:backup.write(disk,str(disk.relative_to(project)))
payload=json.load(gzip.open(root/'prism.json.gz','rt'));asset=u.load_asset(path)
if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Prism import failed')
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Prism save failed')
clips=asset.get_editor_property('clips')
if len(clips)!=len(payload['clips']):raise RuntimeError('Saved clip count differs')
for actual,source in zip(clips,payload['clips']):
    if actual.get_editor_property('base').get_path_name()!=source['base']:raise RuntimeError('Saved base differs')
    tracks=actual.get_editor_property('tracks')
    if len(tracks)!=len(source['tracks']):raise RuntimeError('Saved track count differs')
    for track,src in zip(tracks,source['tracks']):
        if str(track.get_editor_property('bone'))!=src['bone']:raise RuntimeError('Saved bone differs')
        import struct
        f32=lambda x:struct.unpack('f',struct.pack('f',x))[0]
        if list(track.get_editor_property('times'))!=list(map(f32,src['times'])) or list(track.get_editor_property('values'))!=list(map(f32,src['values'])):raise RuntimeError('Saved tracks differ')
(root/'install_receipt.json').write_text(json.dumps(dict(saved={path:sha()},before=expected,complete=True),indent=2))
print('M249_WRIST35_SAVED',path)
