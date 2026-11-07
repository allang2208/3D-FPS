"""Merge the corrected animation roles into the existing project assets."""
import ast
import gzip
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

work = Path(__file__).resolve().parent
previous = work.parent/'M24StockQuickMelee20261106'
root = '/Game/Weapons/M24/ReceiverGripRebuild20261031/Profiles'
library = u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE_ACTIVE: save postponed while the project is playing')
tree = ast.parse((work.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')), 'existing grip serializer','exec'))

def package(path):
    return Path(u.Paths.project_content_dir())/(path[6:].split('.')[0]+'.uasset')

def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()

saved_baseline = {i['family']:i for i in json.loads((previous/'publish_receipt.json').read_text())['saved']}
inputs = json.loads((previous/'input_dependency_hashes.json').read_text())
for item in json.loads((previous/'assembly.json').read_text()).values():
    inputs[item['path']] = item['sha256']
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path, expected in inputs.items():
    if path.split('.')[0] in dirty or digest(package(path)) != expected:
        raise RuntimeError('Changed model or base sequence: '+path)

receipt_file = work/'publication.json'
receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {'saved':{},'complete':False,'runtime_tested':False}
def record():
    temp=receipt_file.with_suffix('.tmp')
    temp.write_text(json.dumps(receipt,indent=2));temp.replace(receipt_file)

backup = work/'BeforePublish'
backup.mkdir(exist_ok=True)
assets_to_save = []
source_roles = None
for family, old in saved_baseline.items():
    shared=old['asset'].split('.')[0];solo=root+'/CarbonMelee/'+shared.rsplit('/',1)[-1]
    patch=work/(family+'.json.gz');patch_hash=digest(patch)
    for variant,path in (('stock',shared),('carbon',solo)):
        if path in dirty:raise RuntimeError('Unsaved package: '+path)
        file=package(path)
        prior=receipt['saved'].get(path)
        if prior:
            if not file.exists() or digest(file)!=prior['sha256'] or patch_hash!=prior['input']:
                raise RuntimeError('Changed asset or authoring input since partial publication: '+path)
            continue
        if variant=='carbon' and (file.exists() or library.does_asset_exist(path)):
            raise RuntimeError('Existing carbon asset outside this publication: '+path)
        if variant=='stock':
            current_digest=digest(file)
            if current_digest!=old['sha256']:
                if source_roles is None:source_roles=json.load(gzip.open(previous/'saved_motion.json.gz','rt'))
                asset=u.load_asset(path);current=packed(asset,family)
                for expected in source_roles[family]['clips']:
                    match=next((c for c in current['clips'] if c['base']==expected['base']),None)
                    if match!=expected:raise RuntimeError('Concurrent idle or melee edit: '+path)
                del current
            backup_file=backup/file.name
            if backup_file.exists() and digest(backup_file)!=current_digest:
                raise RuntimeError('Previous backup differs: '+path)
            if not backup_file.exists():shutil.copy2(file,backup_file)
        assets_to_save.append((family,variant,path,patch,patch_hash,current_digest if variant=='stock' else None))

factory=u.DataAssetFactory()
factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
for family,variant,path,patch,patch_hash,previous_hash in assets_to_save:
    with gzip.open(patch,'rt') as source: edit=json.load(source)
    if variant=='stock':
        if digest(package(path))!=previous_hash:raise RuntimeError('Concurrent save: '+path)
        asset=u.load_asset(path)
        if any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):
            raise RuntimeError('Unexpected retained clip: '+path)
        data=packed(asset,family)
        roles={edit[key]['base']:edit[key] for key in ('stock','idle') if key in edit}
        data['clips']=[roles.get(clip['base'],clip) for clip in data['clips']]
    else:
        parent,name=path.rsplit('/',1)
        library.make_directory(parent)
        asset=u.AssetToolsHelpers.get_asset_tools().create_asset(name,parent,u.WeaponGripProfile,factory)
        data={'family':family,'clips':[edit['carbon']]}
    if not asset or not asset.set_shared_clips_from_json(json.dumps(data,separators=(',',':'))):
        raise RuntimeError('Animation conversion failed: '+path)
    library.set_metadata_tag(asset,'M24QuickMeleeAuthor','M24HandContinuity20261107 '+variant)
    if not library.save_loaded_asset(asset,False):raise RuntimeError('Could not save '+path)
    receipt['saved'][path]={'family':family,'variant':variant,'sha256':digest(package(path)),'input':patch_hash}
    record();print('M24_HAND_SAVED',variant,family,flush=True)
    del data,edit
receipt['complete']=len(receipt['saved'])==2*len(saved_baseline)
record()
print('M24_HAND_PUBLICATION_COMPLETE',len(receipt['saved']),flush=True)
