"""Run only the production layout planner. Requires -DungeonLayoutProbe.

No geometry assembly, physics queries, profile writes, or package saves.
DUNGEON_PROBE_SEEDS / DUNGEON_PROBE_LABEL select a scoped repro.
"""
import json
import os
from pathlib import Path
import unreal as u

if 'DungeonLayoutProbe' not in u.SystemLibrary.get_command_line():
    raise RuntimeError('Explicit layout-only commandlet flag required')
project = Path(u.Paths.project_dir()).resolve()
catalog_path = os.environ.get('DUNGEON_PROBE_CATALOG')
if catalog_path:
    # The production export is identical input to the native planner. A transient
    # generator avoids loading the map's unrelated hard-referenced art assets.
    world = u.EditorLoadingAndSavingUtils.new_blank_map(False)
    generator = u.get_editor_subsystem(u.EditorActorSubsystem).spawn_actor_from_class(
        u.AuthoredDungeonGenerator, u.Vector(0, 0, 0), transient=True)
    generator.set_editor_property('module_catalog_json', Path(catalog_path).read_text(encoding='utf-8-sig'))
else:
    world = u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
    generators = u.GameplayStatics.get_all_actors_of_class(world, u.AuthoredDungeonGenerator)
    if len(generators) != 1:
        raise RuntimeError('Expected one saved dungeon generator')
    generator = generators[0]
out = project / 'Saved/DungeonRoutingFix20260927'
out.mkdir(exist_ok=True)
label = os.environ.get('DUNGEON_PROBE_LABEL', 'probe')
(out / (label + '-catalog.json')).write_text(generator.get_editor_property('module_catalog_json'), encoding='utf-8')
reports = []
source_catalog = generator.get_editor_property('module_catalog_json')
last_case_catalog = source_catalog
case_path = os.environ.get('DUNGEON_PROBE_CASES')
cases = json.loads(Path(case_path).read_text(encoding='utf-8-sig')) if case_path else [
    {'seed': int(seed)} for seed in os.environ.get('DUNGEON_PROBE_SEEDS', '1380107440').split(',')]
for case in cases:
    catalog = json.loads(source_catalog)
    bank_path = os.environ.get('DUNGEON_PROBE_BANK')
    if bank_path:
        catalog['facility_flow']['layout_bank'] = json.loads(Path(bank_path).read_text(encoding='utf-8-sig'))
    if 'themes' in case:
        catalog['facility_flow']['probe_pair_order'] = case['themes']
    case_catalog = json.dumps(catalog, ensure_ascii=False, separators=(',',':'))
    if case_catalog != last_case_catalog:
        generator.set_editor_property('module_catalog_json', case_catalog)
        last_case_catalog = case_catalog
    generator.set_editor_property('preview_seed', int(case['seed']))
    generator.call_method('GeneratePreview')
    report = json.loads(generator.get_editor_property('layout_description'))
    if 'id' in case:
        report['case_id'] = case['id']
    reports.append(report)
    (out / (label + '.json')).write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('DUNGEON_LAYOUT_PROBE ' + json.dumps({k: v for k, v in report.items() if k not in ('pieces', 'probe_pieces', 'mission_edges', 'loops')}))
failed = [report['seed'] for report in reports if not report['success']]
if failed:
    raise RuntimeError('Dungeon layout planning failed for seeds: ' + ', '.join(map(str, failed)))
