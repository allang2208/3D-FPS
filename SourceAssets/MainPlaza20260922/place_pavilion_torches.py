"""Put bronze torches on every other column of the hub pavilion.

User request (2026-09-23): "在凉亭中间的柱子上，隔一根柱子安置青铜火把" -- on the pavilion's
columns, one torch every other column. The pavilion (RomanPavilion2_*) has 10 columns in a ring
of radius 360 around (1350, -400); the odd-numbered ones (01/03/05/07/09) get a torch, which
spaces them 72 degrees apart evenly.

Follows the convention already established for the six colonnade torches in
`SourceAssets/RomanColumn20260915/place_bronze_torches_v7_20260918.py`:
  * actor class `/Script/FPSGAME.BronzeTorch`, placed on the column axis;
  * the torch's local +X arm carries the flame and the light, so yaw is the RADIAL OUTWARD
    direction -- the arm reaches away from the pavilion centre instead of into it;
  * torch actor height = column base + 170 cm, the same offset the colonnade torches use
    (they sit at z=190 on columns whose base is z=20).

Idempotent: previous `PavilionTorch_*` actors are removed first. Tags are kept separate from
`ColdSteel.MainPlaza.Generated` so a plaza rebuild does not delete the torches.
No PIE.
"""
import json
import math
import traceback
from pathlib import Path

import unreal

HERE = Path(__file__).parent
MAP = '/Game/GameMaps/DayNight_Lighting'
TORCH_CLASS_PATH = '/Script/FPSGAME.BronzeTorch'
D = '/Game/Props/RomanColumn20260915'
MESH = D + '/SM_BronzeTorch'
MATERIAL = D + '/M_Bronze'
FLAME = '/Game/NiagaraExamples/FX_Misc/NS_Fire'
FLAME_SCALE = 0.35
IGNITE_HOUR = 16.5
EXTINGUISH_HOUR = 6.0
FLAME_OFFSET = unreal.Vector(50.0, 0.0, 16.0)
LIGHT_OFFSET = unreal.Vector(50.0, 0.0, 52.0)

PAVILION_CENTER = (1350.0, -400.0)
COLUMN_PREFIX = 'RomanPavilion2_Column_'
TORCH_LABEL = 'PavilionTorch_%02d'
TORCH_TAG = 'ColdSteel.PavilionTorch'
TORCH_Z_ABOVE_BASE = 170.0

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)


def set_prop(obj, snake, pascal, value):
    for name in (snake, pascal):
        try:
            obj.set_editor_property(name, value)
            return True
        except Exception:
            continue
    return False


def run():
    world = editor.get_editor_world()
    if world is None:
        raise RuntimeError('The editor has no world loaded; nothing was changed.')
    if editor.get_game_world() is not None:
        raise RuntimeError('PIE is active; nothing was changed.')
    current = world.get_path_name().split('.')[0]
    # Same convention as place_hub_altar.py: refuse when anything is dirty, otherwise open the
    # main map here and switch back after saving.
    previous_map = current
    switched = False
    if current != MAP:
        dirty_elsewhere = [p.get_path_name()
                           for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
        if dirty_elsewhere:
            raise RuntimeError('Preserve unsaved level edits before switching maps: %s; '
                               'nothing was changed.' % ', '.join(dirty_elsewhere))
        if not level.load_level(MAP):
            raise RuntimeError('Could not open %s; nothing was changed.' % MAP)
        switched = True
        world = editor.get_editor_world()
        if world is None or world.get_path_name().split('.')[0] != MAP:
            raise RuntimeError('Switching to %s did not take effect; nothing was changed.' % MAP)

    torch_class = unreal.load_class(None, TORCH_CLASS_PATH)
    if torch_class is None:
        raise RuntimeError('Missing %s; the class must be compiled into the editor build.'
                           % TORCH_CLASS_PATH)
    mesh = unreal.load_asset(MESH)
    material = unreal.load_asset(MATERIAL)
    flame = unreal.load_asset(FLAME)
    if mesh is None or material is None:
        raise RuntimeError('Missing torch mesh/material: %s / %s' % (MESH, MATERIAL))

    # idempotency: drop our own previous torches (by label and by tag)
    dropped = 0
    for actor in list(api.get_all_level_actors()):
        if (actor.get_actor_label().startswith('PavilionTorch_')
                or TORCH_TAG in [str(t) for t in actor.tags]):
            api.destroy_actor(actor)
            dropped += 1

    columns = [a for a in api.get_all_level_actors()
               if a.get_actor_label().startswith(COLUMN_PREFIX)]
    columns.sort(key=lambda a: a.get_actor_label())
    if len(columns) < 2:
        raise RuntimeError('Found %d pavilion columns; expected the 10-column ring.'
                           % len(columns))

    chosen = columns[0::2]                      # every other column
    receipt = dict(map=MAP, columns_found=len(columns), dropped_previous=dropped,
                   torches=[], saved=False)

    with unreal.ScopedEditorTransaction('Place bronze torches on the pavilion columns'):
        for index, column in enumerate(chosen):
            center, extent = column.get_actor_bounds(False)
            base_z = center.z - extent.z
            loc = column.get_actor_location()
            dx = loc.x - PAVILION_CENTER[0]
            dy = loc.y - PAVILION_CENTER[1]
            yaw = math.degrees(math.atan2(dy, dx)) if (dx or dy) else 0.0
            position = unreal.Vector(loc.x, loc.y, base_z + TORCH_Z_ABOVE_BASE)
            actor = api.spawn_actor_from_class(
                torch_class, position, unreal.Rotator(roll=0.0, pitch=0.0, yaw=yaw))
            if actor is None:
                raise RuntimeError('Torch spawn failed at %s' % (position,))
            label = TORCH_LABEL % (index + 1)
            actor.set_actor_label(label)
            set_prop(actor, 'body_mesh', 'BodyMesh', mesh)
            set_prop(actor, 'body_material', 'BodyMaterial', material)
            if flame:
                set_prop(actor, 'flame_system', 'FlameSystem', flame)
            set_prop(actor, 'flame_scale', 'FlameScale', FLAME_SCALE)
            set_prop(actor, 'ignite_hour', 'IgniteHour', IGNITE_HOUR)
            set_prop(actor, 'extinguish_hour', 'ExtinguishHour', EXTINGUISH_HOUR)
            body = actor.get_component_by_class(unreal.StaticMeshComponent)
            if body:
                body.set_static_mesh(mesh)
                body.set_material(0, material)
                body.set_collision_enabled(unreal.CollisionEnabled.QUERY_AND_PHYSICS)
            flame_comp = actor.get_component_by_class(unreal.NiagaraComponent)
            if flame_comp and flame:
                flame_comp.set_asset(flame)
                flame_comp.set_relative_location(FLAME_OFFSET, False, False)
            light_comp = actor.get_component_by_class(unreal.PointLightComponent)
            if light_comp:
                light_comp.set_relative_location(LIGHT_OFFSET, False, False)
            actor.tags = list(dict.fromkeys([str(t) for t in actor.tags] + [TORCH_TAG]))
            actor.set_folder_path('Main Plaza/Pavilion Torches')
            actor.set_editor_property('is_spatially_loaded', False)
            receipt['torches'].append(dict(label=label, host=column.get_actor_label(),
                                           loc=[round(position.x, 1), round(position.y, 1),
                                                round(position.z, 1)],
                                           yaw=round(yaw, 1)))

        if not level.save_current_level():
            raise RuntimeError('Main map save failed; torches exist in the editor but unsaved.')
        receipt['saved'] = True
        receipt['switched_from'] = previous_map if switched else None

    if switched:
        if not level.load_level(previous_map):
            unreal.log_warning('Torches saved; the previous editor map could not be restored: %s'
                               % previous_map)
    return receipt


try:
    result = run()
    (HERE / 'pavilion_torches.json').write_text(json.dumps(result, ensure_ascii=False, indent=2),
                                                encoding='utf-8')
    print('TORCH_OK placed=%d dropped=%d columns=%d saved=%s'
          % (len(result['torches']), result['dropped_previous'], result['columns_found'],
             result['saved']))
    for t in result['torches']:
        print('  %-18s <- %-26s %s yaw=%.1f'
              % (t['label'], t['host'], t['loc'], t['yaw']))
except Exception:
    (HERE / 'pavilion_torches_error.txt').write_text(traceback.format_exc(), encoding='utf-8')
    print('TORCH_FAILED')
    raise
