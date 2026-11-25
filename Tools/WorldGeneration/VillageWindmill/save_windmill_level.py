"""Update only the mill site in the current village package."""
import json
import hashlib
import os
import shutil
import sys
from pathlib import Path

import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from install_windmill import PROJECT, install_windmill

WORK = Path(os.environ['WINDMILL_ART'])
run = Path(os.environ.get('WINDMILL_LEVEL_RUN', WORK))
host_content = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_content_dir()))
if os.environ.get('WINDMILL_YARD_ONLY') == '1':
    owned=host_content/'WorldGeneration/TemperateHills/VillageWindmill/Yard'
    prior={p.relative_to(host_content).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
           for p in owned.rglob('*') if p.is_file()}
    (run/'previous-yard.json').write_text(json.dumps(prior),encoding='utf-8')
if os.environ.get('WINDMILL_IMPORT_YARD') == '1':
    from import_mill_yard import author_yard_assets
    author_yard_assets()
if os.environ.get('WINDMILL_YARD_ONLY') == '1':
    from import_work_details import author
    author()
LEVEL = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage'
package = host_content / (LEVEL.removeprefix('/Game/') + '.umap')
if os.environ.get('WINDMILL_YARD_ONLY') == '1':
    # Engine startup and asset imports can outlast another village edit.
    # Rebase this isolated, still unopened map before placing the mill yard.
    production_package = PROJECT / 'Content' / package.relative_to(host_content)
    if package.resolve() == production_package.resolve():
        raise RuntimeError('Expected an isolated mill yard authoring map')
    shutil.copy2(production_package, package)
initial_stamp = package.stat().st_mtime_ns
src = PROJECT / 'SourceAssets/TemperateHillsVillage'
plan = json.loads((src / 'layout.json').read_text(encoding='utf-8'))
kit = json.loads((src / 'house-pieces.json').read_text(encoding='utf-8'))
backup_root = run if os.environ.get('WINDMILL_YARD_ONLY') == '1' else WORK
before = backup_root / 'Before' / str(initial_stamp) / package.name
before.parent.mkdir(parents=True, exist_ok=True)
if not before.exists():
    shutil.copy2(package, before)
world = ue.EditorLoadingAndSavingUtils.load_map(LEVEL)
if not world:
    raise RuntimeError('Could not open the saved village')
actors = ue.get_editor_subsystem(ue.EditorActorSubsystem) or ue.new_object(ue.EditorActorSubsystem)
if os.environ.get('WINDMILL_YARD_ONLY') == '1':
    from mill_yard import install_mill_yard
    from install_windmill import SITE_TAG
    site, = [a for a in actors.get_all_level_actors() if SITE_TAG in map(str, a.tags)]
    report = install_mill_yard(site)
else:
    report = install_windmill(actors, plan, kit)
if package.stat().st_mtime_ns != initial_stamp:
    raise RuntimeError('Village changed on disk while preparing the mill. Reload the current revision.')
if not ue.EditorLoadingAndSavingUtils.save_map(world, LEVEL):
    raise RuntimeError('Could not save windmill site in ' + LEVEL)
report.update(level=LEVEL, previous_package=str(before), runtime_tested=False)
for directory in ({run} if os.environ.get('WINDMILL_YARD_ONLY') == '1' else {WORK,run}):
    (directory / 'level-saved.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
ue.log('WINDMILL_LEVEL_SAVED ' + LEVEL)
