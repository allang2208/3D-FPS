"""Save only the new SVCH quick-melee entries into the five current profiles."""
from pathlib import Path
import unreal as u,json,hashlib,shutil,gzip
O=Path(__file__).resolve().parent;P=Path(u.Paths.project_dir()).resolve();E=u.EditorAssetLibrary
manifest=json.loads((O/'Inputs/manifest.json').read_text())
action='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_quick_melee'
def disk(path):return P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def digest(path):return hashlib.sha256(disk(path).read_bytes()).hexdigest()
def extract(asset):
    result={'family':str(asset.get_editor_property('family')),'clips':[]}
    for c in asset.get_editor_property('clips'):
        r=c.get_editor_property('retained')
        result['clips'].append({'base':c.get_editor_property('base').get_path_name().split('.')[0],
            'retained':r.get_path_name().split('.')[0] if r else None,'duration':c.get_editor_property('duration'),
            'tracks':[{'bone':str(t.get_editor_property('bone')),'times':list(t.get_editor_property('times')),
                'values':list(t.get_editor_property('values'))} for t in c.get_editor_property('tracks')]})
    return result
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if es and es.get_game_world():raise RuntimeError('PIE active; preserve session')
sources=json.load(gzip.open(O/'Inputs/compressed.json.gz','rt'))['clips']
surfaces=json.loads((O/'Inputs/surfaces-manifest.json').read_text())
for spec in list(sources.values())+list(surfaces.values()):
    if digest(spec['path'])!=spec['sha256']:raise RuntimeError('Authoring input changed '+spec['path'])
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
receipt={'complete':False,'assets':{},'V9_written':False,'shared_sequences_written':False,'other_actions_written':False,
    'game_tested':False,'revision':'SVCHQuickMeleeSVDReferenceR2_20261019'}
rp=O/'install_receipt.json';previous=json.loads(rp.read_text()) if rp.exists() else {}
backup=Path('D:/FPS3D/FPSGAME_Backups/SVCHQuickMeleeSVDReferenceR2_20261019');backup.mkdir(exist_ok=True,parents=True)
prepared=[]
for family in ('base','angled','vertical','canted','prism'):
    spec=manifest['svch_'+family];path=spec['path']
    if path in dirty:raise RuntimeError('Unsaved target '+path)
    prior=previous.get('assets',{}).get(family)
    if prior and digest(path)==prior['sha256']:
        receipt['assets'][family]=prior;continue
    if digest(path)!=spec['sha256']:raise RuntimeError('Target changed since authoring '+path)
    asset=u.load_asset(path);before=extract(asset)
    if any(c['retained'] for c in before['clips']):raise RuntimeError('Retained clips require a lossless importer')
    replacement=next(c for c in json.loads((O/'Profiles'/(family+'.json')).read_text())['clips'] if c['base']==action)
    after=dict(before);after['clips']=[replacement if c['base']==action else c for c in before['clips']]
    prepared.append((family,path,asset,before,after))
for family,path,asset,before,after in prepared:
    b=backup/(family+'_'+digest(path)[:12]+'.uasset')
    if not b.exists():shutil.copy2(disk(path),b)
    if not asset.set_shared_clips_from_json(json.dumps(after)):raise RuntimeError('Import failed '+family)
    readback=extract(asset)
    if [c for c in before['clips'] if c['base']!=action]!=[c for c in readback['clips'] if c['base']!=action]:
        raise RuntimeError('Non-target action changed '+family)
    E.set_metadata_tag(asset,'SVCHQuickMeleeRevision',receipt['revision'])
    E.set_metadata_tag(asset,'SVCHQuickMeleeWrist','Superseded by SVD complete-arm support R2; previous candidate rejected')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+family)
    receipt['assets'][family]={'path':path,'sha256':digest(path),'other_actions_identical':True,'backup':str(b)}
    (O/'SavedReadback').mkdir(exist_ok=True)
    (O/'SavedReadback'/(family+'.json')).write_text(json.dumps(readback,separators=(',',':')))
    rp.write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;rp.write_text(json.dumps(receipt,indent=2))
print('SVCH_R2_FIVE_PROFILES_SAVED',flush=True)
