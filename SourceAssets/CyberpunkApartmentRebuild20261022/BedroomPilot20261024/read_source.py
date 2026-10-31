"""Read the live bedroom authoring inputs without rendering or running gameplay."""
from pathlib import Path
import unreal as u
import json

R = Path(__file__).resolve().parent
MAP = '/Game/GameMaps/L_CyberpunkApartment'
s = u.get_editor_subsystem(u.UnrealEditorSubsystem)
w = s.get_editor_world()
previous = w.get_path_name().split('.')[0] if w else ''
state = dict(previous_map=previous, play_world=bool(s.get_game_world()),
             dirty_maps=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
if state['play_world'] and previous != MAP:
    (R/'editor_state.json').write_text(json.dumps(state, indent=2), encoding='utf8')
    raise RuntimeError('Preserve active play session; target map is not the editor world')
if state['dirty_maps'] and previous != MAP:
    raise RuntimeError('Cannot switch an unsaved map')
if previous != MAP:
    w = u.EditorLoadingAndSavingUtils.load_map(MAP)

def xyz(v): return list(v.to_tuple())
def rot(v): return dict(pitch=v.pitch, yaw=v.yaw, roll=v.roll)

rows = {}
for a in u.GameplayStatics.get_all_actors_of_class(w, u.Actor):
    label = a.get_actor_label()
    p = a.get_actor_location()
    center, extent = a.get_actor_bounds(False)
    in_room = 2130 < center.x < 2985 and -1020 < center.y < 0
    if not ('Bed2' in label or in_room or label in ('AP7_Atmosphere', 'AP_Floor_Bed2', 'AP_Walls', 'AP_Ceiling')):
        continue
    row = dict(position=xyz(p), rotation=rot(a.get_actor_rotation()), scale=xyz(a.get_actor_scale3d()),
               class_name=a.get_class().get_name(), bounds_center=xyz(center), bounds_extent=xyz(extent),
               tags=[str(t) for t in a.tags], components=[])
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:
            continue
        b = c.static_mesh.get_bounding_box()
        row['components'].append(dict(name=c.get_name(), mesh=c.static_mesh.get_path_name(),
            minimum=xyz(b.min), maximum=xyz(b.max), position=xyz(c.get_world_location()),
            rotation=rot(c.get_world_rotation()), scale=xyz(c.get_world_scale()),
            slots=[str(m.material_slot_name) for m in c.static_mesh.static_materials],
            materials=[m.get_path_name() if m else None for m in c.get_materials()],
            collision_profile=str(c.get_collision_profile_name())))
    for c in a.get_components_by_class(u.LightComponent):
        row['light'] = dict(intensity=c.intensity, color=str(c.light_color),
                            rotation=rot(c.get_world_rotation()))
    if label == 'AP7_Atmosphere':
        row['light_bindings'] = [dict(actor=b.actor.get_actor_label() if b.actor else None,
            room=b.room_index, fixtures=[f.get_actor_label() for f in b.fixtures if f])
            for b in a.get_editor_property('lights')]
    rows[label] = row
state.update(map=MAP, actors=rows)
(R/'source.json').write_text(json.dumps(state, indent=2), encoding='utf8')
if previous.startswith('/Game/') and previous != MAP:
    u.EditorLoadingAndSavingUtils.load_map(previous)
print('BEDROOM_AUTHORING_SOURCE', len(rows), state['dirty_maps'])
