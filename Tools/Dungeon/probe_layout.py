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
for seed in os.environ.get('DUNGEON_PROBE_SEEDS', '1380107440').split(','):
    generator.set_editor_property('preview_seed', int(seed))
    generator.call_method('GeneratePreview')
    report = json.loads(generator.get_editor_property('layout_description'))
    reports.append(report)
    (out / (label + '.json')).write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('DUNGEON_LAYOUT_PROBE ' + json.dumps({k: v for k, v in report.items() if k not in ('pieces', 'probe_pieces', 'mission_edges', 'loops')}))
failed = [report['seed'] for report in reports if not report['success']]
if failed:
    raise RuntimeError('Dungeon layout planning failed for seeds: ' + ', '.join(map(str, failed)))
