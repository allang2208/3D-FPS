"""Apply the plaza's level-side geometry optimizations to the actors already in the map.

Two changes, both on the 78 paving actors only:

  * `cast_shadow = false` -- retain the existing floor shadow policy.
  * Target LOD index 1 with UE's `ForcedLodModel = 2` encoding. Each source panel's LOD1 has
    about 12 k triangles versus 120 k at LOD0. This is a configured geometry reduction;
    actual submitted triangles and visual/FPS effects have not been measured by this script.

Requires optimize_plaza_assets.py to have run first: with only one LOD the forced index is ignored.

Idempotent. Aborts instead of saving when another task's unsaved level edits are present.
No PIE.
"""
import json
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
MAP = '/Game/GameMaps/DayNight_Lighting'
TAG_GEN = 'ColdSteel.MainPlaza.Generated'
TAG_PAVING = 'ColdSteel.MainPlaza.Paving'
TARGET_LOD_INDEX = 1
FORCED_LOD = TARGET_LOD_INDEX + 1  # UE: 0=auto, positive values encode LOD index + 1.

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def vec(v):
    return [round(v.x, 1), round(v.y, 1), round(v.z, 1)]


def set_shadow(comp, flag):
    for name in ('set_cast_shadow', 'set_cast_shadows'):
        fn = getattr(comp, name, None)
        if fn:
            fn(flag)
            return name
    comp.set_editor_property('cast_shadow', flag)
    return 'set_editor_property'


def set_forced_lod(comp, index):
    for name in ('set_forced_lod_model', 'set_forced_lod'):
        fn = getattr(comp, name, None)
        if fn:
            fn(index)
            return name
    comp.set_editor_property('forced_lod', index)
    return 'set_editor_property'


def read_forced_lod(comp):
    for name in ('get_forced_lod_model', 'get_forced_lod'):
        fn = getattr(comp, name, None)
        if fn:
            try:
                return fn()
            except Exception:
                pass
    try:
        return comp.get_editor_property('forced_lod')
    except Exception:
        return None


def run():
    world = editor.get_editor_world()
    if world is None:
        raise RuntimeError('The editor has no world loaded; nothing was changed.')
    if editor.get_game_world() is not None:
        raise RuntimeError('PIE is active; nothing was changed.')
    current = world.get_path_name().split('.')[0]
    if current != MAP:
        raise RuntimeError('The active map is %s, not %s; nothing was changed.' % (current, MAP))

    generated = [a for a in api.get_all_level_actors() if TAG_GEN in [str(t) for t in a.tags]]
    dirty = [p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    if dirty and not generated:
        raise RuntimeError('The active map has unsaved edits from another task (%s); '
                           'nothing was changed and the map was not saved.' % ', '.join(dirty))

    rows = []
    lods_available = {}
    changed = 0
    for actor in generated:
        tags = [str(t) for t in actor.tags]
        if TAG_PAVING not in tags or not isinstance(actor, unreal.StaticMeshActor):
            continue
        comp = actor.static_mesh_component
        mesh = comp.static_mesh if comp else None
        if mesh is None:
            continue
        key = mesh.get_path_name()
        if key not in lods_available:
            try:
                lods_available[key] = mesh.get_num_lods()
            except Exception:
                lods_available[key] = 1
        actor.modify()
        shadow_api = set_shadow(comp, False)
        applied_lod = None
        if lods_available[key] > TARGET_LOD_INDEX:
            set_forced_lod(comp, FORCED_LOD)
            applied_lod = read_forced_lod(comp)
        if len(rows) < 3:
            rows.append(dict(label=actor.get_actor_label(), mesh=key.split('/')[-1],
                             lods=lods_available[key], shadow_api=shadow_api,
                             forced_lod=applied_lod))
        changed += 1

    result = dict(map=MAP, paving_actors=changed, forced_lod=FORCED_LOD,
                  lod_counts=lods_available, samples=rows, saved=False)
    if changed == 0:
        raise RuntimeError('No generated paving actors found; nothing was changed.')
    if not level.save_current_level():
        raise RuntimeError('Main map save failed; the editor placement was left intact.')
    result['saved'] = True
    result['runtime_tested'] = False
    return result


try:
    out = run()
    (HERE / 'plaza_level_optimization.json').write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print('LEVEL_OPT_OK paving=%d forced_lod=%s saved=%s'
          % (out['paving_actors'], out['forced_lod'], out['saved']))
    print('LOD_COUNTS ' + json.dumps(out['lod_counts']))
    for s in out['samples']:
        print('  %-22s %s lods=%s shadow=%s forced=%s'
              % (s['label'], s['mesh'], s['lods'], s['shadow_api'], s['forced_lod']))
except Exception:
    (HERE / 'plaza_level_optimization_error.txt').write_text(traceback.format_exc(),
                                                             encoding='utf-8')
    print('LEVEL_OPT_FAILED')
    raise
