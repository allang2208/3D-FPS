"""Clear retired palm-fist and slam-summon references; preserve standalone minions."""
from pathlib import Path
import json
import shutil
import unreal as u

root = Path(__file__).resolve().parent
project = root.parents[1]
output = root / 'AttackSimplification'
if Path(u.Paths.project_dir()).resolve() != project.resolve():
    raise RuntimeError('Wrong UE project')
# LevelEditor PIE queries require the interactive editor, not a commandlet.
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving hand Blueprints')
paths = ['/Game/Monsters/FleshHand/BP_FleshHand',
         '/Game/Monsters/FleshHand/BP_FleshHandMinion']
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths):
    raise RuntimeError('Preserving unsaved hand Blueprints: ' + str(sorted(dirty.intersection(paths))))
output.mkdir(parents=True, exist_ok=True)
pending = []
for path in paths:
    bp = u.load_asset(path)
    if bp is None:
        raise RuntimeError('Missing hand Blueprint: ' + path)
    cdo = u.get_default_object(bp.generated_class())
    pending.append((path, bp, cdo))

report = {'state': 'saving', 'saved': [], 'cleared': {},
          'active_attacks': ['Slam', 'GrandSlam', 'Charge'],
          'standalone_minion_retained': True, 'runtime_tested': False}
def record():
    (output / 'installation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

record()
for path, bp, cdo in pending:
    file = project / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    backup = (Path(__file__).resolve().parents[2] / 'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/AttackSimplification/Before') / file.relative_to(project / 'Content')
    if file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
    bp.modify()
    cdo.modify()
    cleared = {}
    for prop in ['palm_fist_mesh', 'hammer_clip', 'minion_class']:
        value = cdo.get_editor_property(prop)
        cleared[prop] = value.get_path_name() if value else None
        cdo.set_editor_property(prop, None)
    fist = u.find_object(cdo, 'PalmFist')
    if fist:
        fist.modify()
        fist.set_static_mesh(None)
        fist.set_visibility(False)
    u.EditorAssetLibrary.set_metadata_tag(bp, 'FleshHand.Attacks', 'SlamsAndChargeOnly20260927')
    report['cleared'][path] = cleared
    record()
    if not u.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError('Save failed: ' + path)
    report['saved'].append(path)
    record()
report['state'] = 'assets_saved'
record()
print('FLESHHAND_ATTACKS_SAVED ' + str(output / 'installation.json'))
