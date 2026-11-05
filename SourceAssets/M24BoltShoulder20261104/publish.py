"""Merge the two shoulder correction tracks into the live M24 profiles."""
from pathlib import Path
import ast
import gzip
import hashlib
import json
import shutil
import unreal as u

O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
serializer=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')
exec(compile(ast.unparse(serializer),'profile reader','exec'))
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE active. Profile changes were not dispatched.')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
def disk(path):
    return Path(u.Paths.project_content_dir())/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()
def role(clip):
    return clip['base'].split('.')[-1].removeprefix('A_M24_')
with gzip.open(O/'input_motion.json.gz','rt') as f:expected=json.load(f)['profiles']
with gzip.open(O/'shoulder_tracks.json.gz','rt') as f:patch=json.load(f)
paths=json.loads((O/'input_assets.json').read_text())
for path,sha in json.loads((O/'input_dependency_hashes.json').read_text()).items():
    if path.split('.')[0] in dirty or digest(disk(path))!=sha:raise RuntimeError('Changed source preserved: '+path)

receipt_file=O/'publish_receipt.json'
patch_hash=digest(O/'shoulder_tracks.json.gz')
receipt=json.loads(receipt_file.read_text()) if receipt_file.exists() else {'complete':False,'saved':{},'patch_sha256':patch_hash,'runtime_tested':False}
if receipt['patch_sha256']!=patch_hash:raise RuntimeError('A different patch already owns this receipt.')
def record():
    tmp=receipt_file.with_suffix('.tmp')
    tmp.write_text(json.dumps(receipt,indent=2));tmp.replace(receipt_file)
backup=O/'BeforePublish';backup.mkdir(exist_ok=True)
live={}
for family,changes in patch.items():
    if not changes:continue
    path=paths[family]['path'];file=disk(path);sha=digest(file)
    if path in dirty:raise RuntimeError('Unsaved profile preserved: '+path)
    if family in receipt['saved']:
        if sha!=receipt['saved'][family]['sha256']:raise RuntimeError('Changed published profile preserved: '+path)
        continue
    asset=u.load_asset(path)
    if not asset or any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):
        raise RuntimeError('Unavailable or retained clip: '+path)
    family_name=str(asset.get_editor_property('family'))
    current=packed(asset,family_name)
    observed={role(c):c for c in current['clips']}
    for c in expected[family]['clips']:
        if observed.get(role(c))!=c:raise RuntimeError('Concurrent bolt source change preserved: '+path+' '+role(c))
    dest=backup/file.name
    if dest.exists() and digest(dest)!=sha:raise RuntimeError('Different prior backup preserved: '+path)
    if not dest.exists():shutil.copy2(file,dest)
    live[family]=(asset,family_name,file,sha)

record()
for family,(asset,family_name,file,sha) in live.items():
    if digest(file)!=sha:raise RuntimeError('Concurrent write preserved: '+str(file))
    current=packed(asset,family_name)
    for clip in current['clips']:
        changes=patch[family].get(role(clip))
        if not changes:continue
        replacements={tr['bone']:tr for tr in changes}
        clip['tracks']=[replacements.pop(tr['bone'],tr) for tr in clip['tracks']]
        if replacements:raise RuntimeError('Missing shoulder track: '+str(replacements.keys()))
    if not asset.set_shared_clips_from_json(json.dumps(current,separators=(',',':'))):raise RuntimeError('Failed to convert '+family)
    u.EditorAssetLibrary.set_metadata_tag(asset,'M24BoltShoulder','M24BoltShoulder20261104')
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Failed to save '+family)
    receipt['saved'][family]={'asset':asset.get_path_name(),'roles':list(patch[family]),'sha256':digest(file)}
    record();print('M24_BOLT_SHOULDER_SAVED',family,flush=True)
receipt['complete']=True;record()
print('M24_BOLT_SHOULDER_PUBLISH_COMPLETE',len(receipt['saved']),flush=True)
