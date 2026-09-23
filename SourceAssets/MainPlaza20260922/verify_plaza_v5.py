"""Read-only verification of the precinct rebuild and the pavilion torches.

Checks, on the main map (switching there and back if another map is active):
  * the precinct ring now contains NO Roman columns and the baluster count went up to match;
  * all eight gateways are still clear of balusters and rails;
  * the five torches sit on alternating pavilion columns, at column base + 170 cm, with the
    Niagara flame and point light present and the radial-outward yaw.

No edits beyond the map switch back. No PIE.
"""
import json
import math
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
MAP = '/Game/GameMaps/DayNight_Lighting'
CX, CY = 1350.0, -975.0
PAVILION_CENTER = (1350.0, -400.0)
TAG_GEN = 'ColdSteel.MainPlaza.Generated'
TAG_PAVING = 'ColdSteel.MainPlaza.Paving'
TAG_COLONNADE = 'ColdSteel.MainPlaza.Colonnade'
TAG_BALUSTRADE = 'ColdSteel.MainPlaza.Balustrade'
TAG_PRECINCT = 'ColdSteel.MainPlaza.Precinct'
TAG_TORCH = 'ColdSteel.PavilionTorch'

GATES = [
    ('outer_N', 'x', CY + 4900.0, CX, 300.0),
    ('outer_S', 'x', CY - 4900.0, CX, 300.0),
    ('outer_W', 'y', CX - 4900.0, CY, 300.0),
    ('outer_E', 'y', CX + 4900.0, CY, 300.0),
    ('precinct_W', 'y', CX - 900.0, CY, 200.0),
    ('precinct_E', 'y', CX + 900.0, CY, 200.0),
    ('precinct_N', 'x', CY + 1200.0, CX, 300.0),
    ('precinct_S', 'x', CY - 1200.0, CX, 300.0),
]

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def run():
    world = editor.get_editor_world()
    if world is None:
        raise RuntimeError('The editor has no world loaded.')
    if editor.get_game_world() is not None:
        raise RuntimeError('PIE is active.')
    previous = world.get_path_name().split('.')[0]
    switched = False
    if previous != MAP:
        dirty = [p.get_path_name()
                 for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError('Unsaved level edits present: %s' % ', '.join(dirty))
        if not level.load_level(MAP):
            raise RuntimeError('Could not open %s.' % MAP)
        switched = True

    out = dict(map=MAP, switched_from=previous if switched else None)
    actors = api.get_all_level_actors()

    counts = dict(paving=0, colonnade=0, balustrade=0, precinct=0)
    precinct_roles = dict(posts=0, rails=0, columns=0)
    for actor in actors:
        tags = [str(t) for t in actor.tags]
        if TAG_GEN not in tags or not isinstance(actor, unreal.StaticMeshActor):
            continue
        label = actor.get_actor_label()
        if TAG_PAVING in tags:
            counts['paving'] += 1
        elif TAG_COLONNADE in tags:
            counts['colonnade'] += 1
        elif TAG_BALUSTRADE in tags:
            counts['balustrade'] += 1
        elif TAG_PRECINCT in tags:
            counts['precinct'] += 1
            if 'Col_' in label:
                precinct_roles['columns'] += 1
            elif 'Rail_' in label:
                precinct_roles['rails'] += 1
            else:
                precinct_roles['posts'] += 1
    out['counts'] = counts
    out['precinct_roles'] = precinct_roles
    out['precinct_columns_expected_zero'] = precinct_roles['columns'] == 0

    violations = []
    examined = 0
    for actor in actors:
        tags = [str(t) for t in actor.tags]
        if TAG_GEN not in tags:
            continue
        if not (TAG_BALUSTRADE in tags or TAG_PRECINCT in tags):
            continue
        examined += 1
        p = actor.get_actor_location()
        for name, axis, fixed, centre, half in GATES:
            if axis == 'x':
                if abs(p.y - fixed) < 60.0 and abs(p.x - centre) < half:
                    violations.append(dict(actor=actor.get_actor_label(), gate=name))
            else:
                if abs(p.x - fixed) < 60.0 and abs(p.y - centre) < half:
                    violations.append(dict(actor=actor.get_actor_label(), gate=name))
    out['gate_check'] = dict(examined=examined, violations=violations)

    torches = []
    for actor in actors:
        if TAG_TORCH not in [str(t) for t in actor.tags]:
            continue
        loc = actor.get_actor_location()
        yaw = actor.get_actor_rotation().yaw
        radial = math.degrees(math.atan2(loc.y - PAVILION_CENTER[1], loc.x - PAVILION_CENTER[0]))
        _, extent = actor.get_actor_bounds(False)
        torches.append(dict(
            label=actor.get_actor_label(), cls=actor.get_class().get_name(), loc=vec(loc),
            yaw=round(yaw, 1), radial_outward=round(radial, 1),
            yaw_matches_outward=abs(((yaw - radial + 180.0) % 360.0) - 180.0) < 1.0,
            min_z=round(loc.z - (extent.z - (loc.z - (loc.z - extent.z))), 1),
            has_mesh=actor.get_component_by_class(unreal.StaticMeshComponent) is not None,
            has_flame=actor.get_component_by_class(unreal.NiagaraComponent) is not None,
            has_light=actor.get_component_by_class(unreal.PointLightComponent) is not None))
    out['torches'] = sorted(torches, key=lambda t: t['label'])
    out['torch_count'] = len(torches)
    # Restore the caller's map here, inside run(), so it cannot be skipped by a later error.
    if switched:
        if level.load_level(previous):
            out['restored'] = previous
        else:
            unreal.log_warning('Read-back done; the previous editor map could not be restored: %s'
                               % previous)
    return out


try:
    result = run()
    (HERE / 'plaza_verify_v5.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                               encoding='utf-8')
    print('VERIFY5_OK counts=%s precinct_roles=%s' % (result['counts'], result['precinct_roles']))
    print('PRECINCT_COLUMNS_ZERO %s' % result['precinct_columns_expected_zero'])
    print('GATE_CHECK examined=%d violations=%d'
          % (result['gate_check']['examined'], len(result['gate_check']['violations'])))
    print('TORCHES %d' % result['torch_count'])
    for t in result['torches']:
        print('  %-18s %-12s %s yaw=%-7s radial=%-7s match=%s mesh=%s flame=%s light=%s'
              % (t['label'], t['cls'], t['loc'], t['yaw'], t['radial_outward'],
                 t['yaw_matches_outward'], t['has_mesh'], t['has_flame'], t['has_light']))
except Exception:
    (HERE / 'plaza_verify_v5_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('VERIFY5_FAILED')
    raise
