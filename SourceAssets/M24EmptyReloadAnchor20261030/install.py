"""Merge only the VM_Root translation track into the two current profiles."""
import unreal as u,json,copy,ast,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='packed')),'packed','exec'))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; assets retained')
paths={f:'/Game/Weapons/M24/MotionPolish20261027/'+n for f,n in {'base':'DA_M24_SupportGrip','mag10':'DA_M24_Mag10'}.items()}
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p in dirty for p in paths.values()):raise RuntimeError('Unsaved M24 profile edits retained')
patch=json.loads((O/'translation_patch.json').read_text());snapshot=json.loads((O/'before.json').read_text())
live={f:u.load_asset(p) for f,p in paths.items()};staged={};backup=O/'Backups';backup.mkdir(exist_ok=True)
for family,asset in live.items():
    if any(c.get_editor_property('retained') for c in asset.get_editor_property('clips')):raise RuntimeError('Retained clip was added; retained asset')
    spec=packed(asset,family);change=patch[family]
    dst=next(c for c in spec['clips'] if c['base']==change['base'])
    prior=next(c for c in snapshot['profiles'][family]['clips'] if c['base']==change['base'])
    if dst!=prior:raise RuntimeError('Empty reload changed during authoring; retained '+family)
    (backup/(family+'.json')).write_text(json.dumps(spec),encoding='utf-8')
    disk=Path(u.Paths.project_content_dir())/(paths[family].removeprefix('/Game/')+'.uasset')
    if not (backup/disk.name).exists():shutil.copy2(disk,backup/disk.name)
    current=next((t for t in dst['tracks'] if t['bone']=='VM_Root'),None)
    if current is None:dst['tracks'].append(change['track'])
    else:current.update(change['track'])
    staged[family]=spec
receipt=dict(complete=False,saved=[],scope='empty reload VM_Root translation only',source_window_frames=[55,105],
    ordinary_reload_changed=False,mechanical_timing_changed=False,cpp_changed=False,runtime_tested=False)
for family,asset in live.items():
    if not asset.set_shared_clips_from_json(json.dumps(staged[family])):raise RuntimeError('Profile update failed '+family)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Profile save failed '+family)
    receipt['saved'].append(asset.get_path_name())
    (O/(family+'_profile.json')).write_text(json.dumps(staged[family]),encoding='utf-8')
    (O/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
receipt['complete']=True;(O/'install_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('M24_EMPTY_RELOAD_ANCHOR_SAVED',json.dumps(receipt),flush=True)
