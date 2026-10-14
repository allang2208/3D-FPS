"""Read actual saved light components; this is separate from the native spawn probe."""
from pathlib import Path
import json, math
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    raise RuntimeError('Isolated commandlet only; do not replace an open editor world')
prior = json.loads((PROJECT/'SourceAssets/DungeonFixtureLighting20261009/Receipts/install.json').read_text('utf8'))
reception = json.loads((PROJECT/'SourceAssets/ReceptionLighting20261009/Receipts/saved-readback.json').read_text('utf8'))
targets = [(entry['path'], prior['fixed'] if entry['path'].endswith('L_Dungeon_Randomized') else entry['lights']) for entry in prior['maps']]
targets.append(('/Game/GameMaps/Design/L_ReceptionHall_Subject', [dict(label='Reception_'+r['id'], type=r['type'],
    position=r['position_cm'], forward=r['forward'], intensity=r['intensity']) for r in reception['subject']]))
report = dict(stage='saved_component_directions_checked', maps=[], game_run=False, map_saved=False)
def vector(v): return [v.x, v.y, v.z]
for path, expected in targets:
    # Load the map as a world so externally stored actors are available too.
    world = u.EditorLoadingAndSavingUtils.load_map(path)
    actors = {a.get_actor_label(): a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)}
    rows = []
    for entry in expected:
        actor = actors[entry['label']]
        component = actor.get_component_by_class(u.LocalLightComponent)
        position, forward = vector(component.get_world_location()), vector(component.get_forward_vector())
        row = dict(label=entry['label'], type=component.get_class().get_name(), actual_position=position,
            actual_forward=forward, expected_forward=entry['forward'], intensity=component.intensity)
        if row['type'] != entry['type'] or math.dist(forward, entry['forward']) > .001:
            raise RuntimeError('Saved light direction or class changed: '+str(row))
        if math.dist(position, entry['position']) > .025:
            raise RuntimeError('Saved light position changed: '+str(row))
        if isinstance(component, u.SpotLightComponent):
            row.update(outer_cone=component.outer_cone_angle, source_length=component.source_length)
        rows.append(row)
    report['maps'].append(dict(path=path, lights=rows))
report['count'] = sum(len(m['lights']) for m in report['maps'])
(ROOT/'Receipts/saved-component-directions.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
print('SAVED_LIGHT_COMPONENT_DIRECTIONS', report['count'], 'actual components;', len(report['maps']), 'saved worlds; no save/game')
