"""Merge only the equip correction into current production profiles."""
import unreal as u,json,ast,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('PIE is active; current assets retained')
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in paths.values()):raise RuntimeError('Unsaved M24 profile edits retained')
patch=json.loads((O/'equip_patch.json').read_text());before=json.loads((O/'before.json').read_text())
backup=O/'Before';backup.mkdir(exist_ok=True);staged={};live={}
for family,path in paths.items():
    asset=u.load_asset(path);live[family]=asset
    if any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):raise RuntimeError('Retained clip added during authoring; current profile retained')
    spec=packed(asset,str(asset.get_editor_property('family')))
    change=patch[family];dst=next(c for c in spec['clips'] if c['base']==change['base'])
    prior=next(c for c in before['profiles'][family]['clips'] if c['base']==change['base'])
    if dst!=prior:raise RuntimeError('Equip changed during authoring; current '+family+' retained')
    (backup/(family+'.json')).write_text(json.dumps(spec),encoding='utf-8')
    disk=Path(u.Paths.project_content_dir())/(path.removeprefix('/Game/')+'.uasset')
    if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
    owned={t['bone'] for t in change['tracks']}
    dst['tracks']=[t for t in dst['tracks'] if t['bone'] not in owned]+change['tracks']
    staged[family]=spec
receipt=dict(complete=False,saved=[],scope='equip, base and mag10',duration_changed=False,mechanical_timing_changed=False,cpp_changed=False,runtime_tested=False)
for family,asset in live.items():
    if not asset.set_shared_clips_from_json(json.dumps(staged[family])):raise RuntimeError('Profile merge failed '+family)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed '+family)
    receipt['saved'].append(asset.get_path_name())
    (O/(family+'_profile.json')).write_text(json.dumps(staged[family]),encoding='utf-8')
    (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2))
print('M24_EQUIP_DIRECT_SAVED',json.dumps(receipt),flush=True)
