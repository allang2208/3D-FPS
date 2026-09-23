"""Verify (and finish) the plaza's level-side optimization, reading the real property names.

The previous run applied `cast_shadow=false` to all 78 paving actors and saved, but the
forced-LOD read-back came out `None`, which may only mean the property is named
`forced_lod_model` rather than `forced_lod`. This script reads the real property, sets it when
it is not already 2 (LOD1), reads the applied property, and saves only if something changed.

Idempotent. No PIE.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
MAP = '/Game/GameMaps/DayNight_Lighting'
TAG_GEN = 'ColdSteel.MainPlaza.Generated'
TAG_PAVING = 'ColdSteel.MainPlaza.Paving'
TAG_COLONNADE = 'ColdSteel.MainPlaza.Colonnade'
TAG_BALUSTRADE = 'ColdSteel.MainPlaza.Balustrade'
WANT_LOD = 2  # 0=auto; 1=LOD0; 2=LOD1.

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

FORCED_PROPS = ('forced_lod_model', 'forced_lod')
SHADOW_PROPS = ('cast_shadow', 'cast_shadows')


def read_first(obj, names):
    for name in names:
        try:
            return name, obj.get_editor_property(name)
        except Exception:
            continue
    return None, None


def write_first(obj, names, value):
    for name in names:
        try:
            obj.set_editor_property(name, value)
            return name
        except Exception:
            continue
    return None


def run():
    world = editor.get_editor_world()
    if world is None:
        raise RuntimeError('The editor has no world loaded; nothing was changed.')
    if editor.get_game_world() is not None:
        raise RuntimeError('PIE is active; nothing was changed.')
    if world.get_path_name().split('.')[0] != MAP:
        raise RuntimeError('The active map is not %s; nothing was changed.' % MAP)

    paving, columns, balusters = [], [], []
    for actor in api.get_all_level_actors():
        tags = [str(t) for t in actor.tags]
        if TAG_GEN not in tags or not isinstance(actor, unreal.StaticMeshActor):
            continue
        if TAG_PAVING in tags:
            paving.append(actor)
        elif TAG_COLONNADE in tags:
            columns.append(actor)
        elif TAG_BALUSTRADE in tags:
            balusters.append(actor)

    out = dict(map=MAP, paving=len(paving), columns=len(columns), balusters=len(balusters),
               changed=0, saved=False, samples=[])
    if not paving:
        raise RuntimeError('No generated paving actors found.')

    for actor in paving:
        comp = actor.static_mesh_component
        prop, current = read_first(comp, FORCED_PROPS)
        if current != WANT_LOD:
            actor.modify()
            used = write_first(comp, FORCED_PROPS, WANT_LOD)
            _, after = read_first(comp, FORCED_PROPS)
            if after != WANT_LOD:
                raise RuntimeError('Forced LOD did not stick on %s (prop=%s, read=%s)'
                                   % (actor.get_actor_label(), used, after))
            out['changed'] += 1
        if len(out['samples']) < 3:
            mesh = comp.static_mesh
            shadow_prop, shadow_val = read_first(comp, SHADOW_PROPS)
            out['samples'].append(dict(
                label=actor.get_actor_label(),
                forced_prop=prop, forced_lod=current,
                shadow_prop=shadow_prop, cast_shadow=shadow_val,
                mesh_lods=mesh.get_num_lods() if mesh else None))

    # Columns and balusters intentionally keep no forced LOD: they are small on screen, so the
    # screen-size thresholds drop them to LOD1/LOD2 by themselves.
    out['column_sample'] = dict(
        label=columns[0].get_actor_label(),
        mesh_lods=columns[0].static_mesh_component.static_mesh.get_num_lods()) if columns else None
    out['baluster_sample'] = dict(
        label=balusters[0].get_actor_label(),
        mesh_lods=balusters[0].static_mesh_component.static_mesh.get_num_lods()) if balusters else None

    if out['changed']:
        if not level.save_current_level():
            raise RuntimeError('Main map save failed; the editor placement was left intact.')
        out['saved'] = True
    return out


try:
    result = run()
    (HERE / 'plaza_level_optimization.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('VERIFY_OK paving=%d changed=%d saved=%s' % (result['paving'], result['changed'],
                                                       result['saved']))
    for s in result['samples']:
        print('  %-22s forced(%s)=%s  shadow(%s)=%s  mesh_lods=%s'
              % (s['label'], s['forced_prop'], s['forced_lod'], s['shadow_prop'],
                 s['cast_shadow'], s['mesh_lods']))
    print('  column   %s' % (result['column_sample'],))
    print('  baluster %s' % (result['baluster_sample'],))
except Exception:
    (HERE / 'plaza_level_optimization_error.txt').write_text(traceback.format_exc(),
                                                             encoding='utf-8')
    print('VERIFY_FAILED')
    raise
