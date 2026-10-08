"""Read only the active player's Zhenmo field state; never start or alter PIE."""
from pathlib import Path
import json
import unreal as u

OUT = Path(__file__).resolve().parent
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
record = {'world': world.get_path_name() if world else None, 'players': []}

def obj(value):
    return value.get_path_name() if value else None

def prop(value, key):
    try:
        native = {'ends_at': 'EndsAt', 'radius_cm': 'RadiusCM', 'field_material': 'FieldMaterial',
                  'mote_system': 'MoteSystem', 'field_mid': 'FieldMID', 'field_surface': 'FieldSurface',
                  'field_motes': 'FieldMotes'}
        return value.get_editor_property(native.get(key, key))
    except Exception as exc:
        return {'unavailable': str(exc)}

if world:
    record['world_seconds'] = u.GameplayStatics.get_time_seconds(world)
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        components = [c for c in actor.get_components_by_class(u.ActorComponent)
                      if c.get_class().get_name() == 'ZhenmoRuneComponent']
        if not components:
            continue
        row = {'actor': actor.get_path_name(), 'location': str(actor.get_actor_location()), 'runes': []}
        row['visual_components'] = [c.get_name() for c in actor.get_components_by_class(u.SceneComponent)
                                    if 'Zhenmo' in c.get_name()]
        for rune in components:
            entry = {'component': rune.get_path_name(), 'tick': rune.is_component_tick_enabled()}
            for key in ('ends_at', 'radius_cm'):
                entry[key] = prop(rune, key)
            for key in ('field_material', 'mote_system'):
                value = prop(rune, key)
                entry[key] = value if isinstance(value, dict) else obj(value)
            mid = prop(rune, 'field_mid')
            visual = next((c for c in actor.get_components_by_class(u.DynamicMeshComponent)
                           if c.get_name() == 'ZhenmoSoftGround'), None)
            if visual:
                mid = visual.get_material(0)
            if isinstance(mid, u.MaterialInstanceDynamic):
                entry['opacity'] = mid.get_scalar_parameter_value('FieldOpacity')
                entry['center'] = str(mid.get_vector_parameter_value('FieldCenter'))
                entry['material_radius'] = mid.get_scalar_parameter_value('FieldRadius')
            surface = prop(rune, 'field_surface')
            if visual:
                surface = visual
            if isinstance(surface, u.DynamicMeshComponent):
                entry['surface'] = {'path': obj(surface), 'visible': surface.is_visible(),
                                    'location': str(surface.get_world_location()),
                                    'triangles': surface.get_dynamic_mesh().get_triangle_count()}
            else:
                entry['surface'] = surface if isinstance(surface, dict) else obj(surface)
            motes = prop(rune, 'field_motes')
            motes = next((c for c in actor.get_components_by_class(u.NiagaraComponent)
                          if c.get_name() == 'ZhenmoRisingGold'), None)
            if isinstance(motes, u.NiagaraComponent):
                entry['motes'] = {'path': obj(motes), 'active': motes.is_active(), 'visible': motes.is_visible()}
            row['runes'].append(entry)
        record['players'].append(row)
(OUT / 'live_state.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('ZHENMO_LIVE_STATE ' + json.dumps(record, ensure_ascii=False), flush=True)
