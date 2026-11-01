"""Merge only quick_melee in both current M24 profiles, preserving parallel work."""
import unreal as u,json,copy,ast,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
tree=ast.parse((O.parent/'M24SprintSupport20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
expected=json.loads((O/'ue_before.json').read_text())
patch=json.loads((O/'quick_melee_patch.json').read_text())
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE owns the M24 profiles; nothing modified')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in paths.values()):raise RuntimeError('Unsaved M24 profiles retained')
live={f:u.load_asset(p) for f,p in paths.items()}
if any(p is None for p in live.values()):raise RuntimeError('M24 profile missing')
for profile in live.values():
    if any(c.get_editor_property('retained') is not None for c in profile.get_editor_property('clips')):
        raise RuntimeError('Retained clip needs its own merge; current asset preserved')
before={f:packed(p,f) for f,p in live.items()};spec=copy.deepcopy(before)
for family,replacement in patch.items():
    path=replacement['base']
    actual=next(c for c in before[family]['clips'] if c['base']==path)
    old=next(c for c in expected['profiles'][family] if c['base']==path)
    if actual!=old:raise RuntimeError('Concurrent M24 quick-melee edit retained: '+family)
    for i,clip in enumerate(spec[family]['clips']):
        if clip['base']==path:spec[family]['clips'][i]=replacement
backup=O/'Backups';backup.mkdir(exist_ok=True)
report={'complete':False,'saved':[],'roles':['quick_melee'],'runtime_tested':False,'rendered':True}
for family,p in live.items():
    file=Path(u.Paths.project_content_dir())/(paths[family].removeprefix('/Game/')+'.uasset')
    saved=backup/file.name
    if not saved.exists():shutil.copy2(file,saved)
    (backup/(family+'.json')).write_text(json.dumps(before[family]),encoding='utf-8')
    if not p.set_shared_clips_from_json(json.dumps(spec[family])):raise RuntimeError('Profile import failed: '+family)
    u.EditorAssetLibrary.set_metadata_tag(p,'M24QuickMeleeAuthor','SourceAssets/M24QuickMeleeContact20261028: stock-neck club regrip; 0.9s, contact .25s')
    if not u.EditorAssetLibrary.save_loaded_asset(p,False):raise RuntimeError('Profile save failed: '+family)
    report['saved'].append({'path':p.get_path_name(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
                            'track_count':len(patch[family]['tracks'])})
    (O/'install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
report['complete']=True
(O/'install_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M24_STOCK_BASH_SAVED',json.dumps(report),flush=True)
