"""Install the two open-cover windows over the exact W38 and handguard inputs."""
from pathlib import Path
import gzip
import hashlib
import json
import struct
import zipfile
import unreal as ue

here=Path(__file__).resolve().parent
project=here.parents[2]
inputs=json.loads((here.parent/'Wrist38/install_receipt.json').read_text())['saved']
bare=json.loads((project/'SourceAssets/LMGStabilityGrip20261111/Review02/support_install.json').read_text())['M249']
inputs[bare['path']]=bare['sha256']
receipt=here/'saved.json'
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
disk=lambda path:project/'Content'/(path.removeprefix('/Game/')+'.uasset')
sha=lambda path:hashlib.sha256(disk(path).read_bytes()).hexdigest()
get=lambda obj,key:obj.get_editor_property(key)
f32=lambda x:struct.unpack('f',struct.pack('f',x))[0]
if '-run=pythonscript' not in ue.SystemLibrary.get_command_line().lower():
    if ue.get_editor_subsystem(ue.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('Finish PIE before saving grip profiles')
dirty={p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path,h in inputs.items():
    if path in dirty or sha(path) not in (h,saved.get(path)):raise RuntimeError('Input changed: '+path)
backup=here/'accepted-before.zip'
if not backup.exists():
    with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as out:
        for path in inputs:out.write(disk(path),str(disk(path).relative_to(project)))
for path in inputs:
    family=path.split('_')[-1].lower()
    if family=='supportgrip':family='base'
    with gzip.open(here/(family+'.json.gz'),'rt') as stream:data=json.load(stream)
    asset=ue.load_asset(path)
    if not asset.set_shared_clips_from_json(json.dumps(data)):raise RuntimeError(path)
    if not ue.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+path)
    clips=get(asset,'clips')
    if len(clips)!=len(data['clips']):raise RuntimeError('Clip count: '+path)
    for clip,row in zip(clips,data['clips']):
        tracks=get(clip,'tracks')
        if get(clip,'base').get_path_name()!=row['base'] or len(tracks)!=len(row['tracks']):raise RuntimeError('Clip: '+path)
        for actual,track in zip(tracks,row['tracks']):
            if str(get(actual,'bone'))!=track['bone'] or list(get(actual,'times'))!=list(map(f32,track['times'])) or list(get(actual,'values'))!=list(map(f32,track['values'])):
                raise RuntimeError('Readback: '+path+' '+row['base']+' '+track['bone'])
    saved[path]=sha(path)
    receipt.write_text(json.dumps(saved,indent=2))
    print('SAVED_M249_LID',path,saved[path])
