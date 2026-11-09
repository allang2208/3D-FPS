"""Save this M249 batch through the existing editor bridge or a headless commandlet."""
from pathlib import Path
import unreal as u,json,hashlib
root=Path(__file__).resolve().parents[1];project=root.parents[1]
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; preserve its unsaved assets')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Weapons/M249/')]
if dirty:raise RuntimeError('Preserve unsaved M249 packages '+str(dirty))
before=json.loads((root/'Repair04/before_hashes.json').read_text(encoding='utf8'))
changed=[n for n,h in before.items() if n.endswith('.uasset') and hashlib.sha256((project/n).read_bytes()).hexdigest()!=h]
if changed:raise RuntimeError('M249 asset changed since this batch began: '+str(changed))
for name in ('import_assets.py','import_motion.py'):
    p=root/name;exec(compile(p.read_text(encoding='utf8'),str(p),'exec'),{'__file__':str(p),'__name__':'__main__'})
retired=[]
for path in ('/Game/Weapons/M249/Assembly/SM_M249_holographic','/Game/Weapons/M249/Materials/M_M249_HoloReticle','/Game/Weapons/M249/Materials/M_M249_Riser'):
    if u.load_asset(path) and not u.EditorAssetLibrary.find_package_referencers_for_asset(path,True):
        if u.EditorAssetLibrary.delete_asset(path):retired.append(path)
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
(root/'Repair04/import_receipt.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')],retired=retired),indent=2))
print('M249_REPAIR04_SAVED',flush=True)
