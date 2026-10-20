"""Merge only quick_melee into the five currently installed SVCH profiles."""
from pathlib import Path
import unreal as u,json,hashlib,shutil
O=Path(__file__).resolve().parent;P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary
source=O.parent/'ForegripFit20261019'
specs=json.loads((source/'install_receipt.json').read_text())['assets']
specs['base']=json.loads((source/'Inputs/manifest.json').read_text())['profile']
action='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_quick_melee'
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def digest(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def extract(asset):
    data={'family':str(asset.get_editor_property('family')),'clips':[]}
    for clip in asset.get_editor_property('clips'):
        if clip.get_editor_property('retained'):raise RuntimeError('Retained action needs explicit merge')
        data['clips'].append({'base':clip.get_editor_property('base').get_path_name().split('.')[0],
            'duration':clip.get_editor_property('duration'),
            'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),
                'values':list(t.get_editor_property('values'))} for t in clip.get_editor_property('tracks')]})
    return data
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():raise RuntimeError('Preserve active PIE; profile save deferred')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
receipt={'complete':False,'assets':{},'V9_written':False,'shared_sequences_written':False,'game_tested':False}
previous=json.loads((O/'install_receipt.json').read_text()) if (O/'install_receipt.json').exists() else {}
backup=Path('D:/FPS3D/FPSGAME_Backups/SVCHQuickMeleeWrist20261019');backup.mkdir(parents=True,exist_ok=True)
prepared=[]
for family in ('base','angled','vertical','canted','prism'):
    spec=specs[family];path=spec['path']
    if path in dirty:raise RuntimeError('Preserve unsaved profile '+path)
    prior=previous.get('assets',{}).get(family)
    if prior and digest(path)==prior['sha256']:
        receipt['assets'][family]=prior
        continue
    if digest(path)!=spec['sha256']:raise RuntimeError('Profile changed since input '+path)
    asset=u.load_asset(path);before=extract(asset)
    authored=json.loads((O/'Profiles'/(family+'.json')).read_text())
    replacement=next(x for x in authored['clips'] if x['base']==action)
    merged=dict(before);merged['clips']=[replacement if row['base']==action else row for row in before['clips']]
    prepared.append((family,path,asset,before,merged))
for family,path,asset,before,merged in prepared:
    file=backup/(family+'_'+digest(path)[:12]+'.uasset')
    if not file.exists():shutil.copy2(disk(path),file)
    if not asset.set_shared_clips_from_json(json.dumps(merged)):raise RuntimeError('Import failed '+family)
    after=extract(asset)
    if [c for c in before['clips'] if c['base']!=action]!=[c for c in after['clips'] if c['base']!=action]:
        raise RuntimeError('Unexpected non-target action change '+family)
    E.set_metadata_tag(asset,'SVCHQuickMeleeWrist','NativeV9Support20261019')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+family)
    receipt['assets'][family]={'path':path,'sha256':digest(path),'other_actions_identical':True}
    (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True
(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SVCH_QUICK_MELEE_PROFILES_SAVED',flush=True)
