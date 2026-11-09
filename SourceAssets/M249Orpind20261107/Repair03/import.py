"""Publish the M249 asset repair through the shared editor batch gate."""
from pathlib import Path
import unreal as u,json,hashlib
root=Path(__file__).resolve().parents[1]
project=root.parents[1]
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; preserve the running session and wait before saving M249 assets')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
       if p.get_path_name().startswith('/Game/Weapons/M249/')
       and p.get_path_name()!='/Game/Weapons/M249/Textures/T_M249_Color']
# T_M249_Color was dirtied by this repair's first import attempt before
# the live editor's stale AssetRegistry lookup returned no object.
if dirty:raise RuntimeError('Preserve unsaved M249 packages '+str(dirty))
before=json.loads((root/'Repair03/before_hashes.json').read_text())
changed=[name for name,digest in before.items() if not name.endswith('Textures\\T_M249_Color.uasset')
         and hashlib.sha256((project/name).read_bytes()).hexdigest()!=digest]
if changed:raise RuntimeError('M249 assets changed since this repair snapshot: '+str(changed))
for name in ('import_assets.py','import_motion.py'):
    script=root/name
    exec(compile(script.read_text(encoding='utf8'),str(script),'exec'),{'__file__':str(script),'__name__':'__main__'})
mesh=u.load_asset('/Game/Weapons/M249/SK_M249_V7')
morphs=[m.get_name() for m in mesh.get_editor_property('morph_targets')]
if not any(n.startswith('JC_Pose_') for n in morphs):raise RuntimeError('M249 V9 corrective import missing')
(root/'Repair03/import_receipt.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),morphs=morphs),indent=2))
print('M249_REPAIR03_SAVED',len(morphs),flush=True)
