"""Read-only scope discovery for the kitchen's actual UE production scene.
Run through the project's mcp_call_codex.ps1 when the editor is already loaded,
or in a background editor host when it is closed. Does not save any asset.
"""
from pathlib import Path
import json
import unreal as u
R = Path(__file__).resolve().parent
PROJECT = R.parents[2]
MAP = '/Game/GameMaps/L_CyberpunkApartment'
result = dict(stage='read_only', map=MAP, targets={}, materials={}, existing_receipts={})
try:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('Read production after stopping active PIE; never save an active game world')
    world = u.EditorLoadingAndSavingUtils.load_map(MAP)
    actors = {a.get_actor_label(): a for a in u.GameplayStatics.get_all_actors_of_class(world, u.Actor)}
    for label, a in actors.items():
        is_container = isinstance(a, u.ColdSteelSceneContainer)
        if is_container and not any(k in label for k in ['Kitchen','Fridge']):
            continue
        is_static = isinstance(a, u.StaticMeshActor)
        if not (is_container or (is_static and any(k in label for k in ['Kitchen','Fridge','Dining'])) or label == 'AP7_Atmosphere'):
            continue
        rot = a.get_actor_rotation()
        row = dict(class_name=a.get_class().get_name(), path=a.get_path_name(),
                   position=list(a.get_actor_location().to_tuple()),
                   rotation=dict(pitch=rot.pitch,yaw=rot.yaw,roll=rot.roll),
                   scale=list(a.get_actor_scale3d().to_tuple()))
        if is_container:
            row.update(id=a.get_editor_property('container_id'), hinge=list(a.door_hinge.relative_location.to_tuple()),
                       body=a.body.static_mesh.get_path_name() if a.body.static_mesh else None,
                       front=a.door.static_mesh.get_path_name() if a.door.static_mesh else None,
                       body_transform=dict(p=list(a.body.relative_location.to_tuple()),s=list(a.body.relative_scale3d.to_tuple())),
                       front_transform=dict(p=list(a.door.relative_location.to_tuple()),s=list(a.door.relative_scale3d.to_tuple())))
            for part,component in [('body',a.body),('front',a.door)]:
                if component.static_mesh:
                    bounds=component.static_mesh.get_bounding_box()
                    row[part+'_bounds_cm']=dict(min=list(bounds.min.to_tuple()),max=list(bounds.max.to_tuple()))
                    row[part+'_slots']=[str(s.material_slot_name) for s in component.static_mesh.get_editor_property('static_materials')]
                    row[part+'_materials']=[m.get_path_name() if m else None for m in component.get_materials()]
        elif is_static and a.static_mesh_component.static_mesh:
            c = a.static_mesh_component
            row.update(mesh=c.static_mesh.get_path_name(), materials=[m.get_path_name() if m else None for m in c.get_materials()])
        if label == 'AP7_Atmosphere':
            row['lights'] = [dict(light=b.actor.get_actor_label() if b.actor else None,
                                 room_index=b.room_index, fixtures=[f.get_actor_label() for f in b.fixtures if f]) for b in a.get_editor_property('lights')]
            row['clock'] = a.get_editor_property('animation_clock').get_path_name() if a.get_editor_property('animation_clock') else None
        result['targets'][label] = row
    result['dirty_maps'] = [p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
    for label in ['AP_Container_Kitchen_Base_2','AP_Container_Kitchen_Sink_0','AP_Container_Fridge_Lower','AP_Container_Fridge_Upper','AP_Kitchen_Run']:
        a=actors[label]
        row=dict(label=label,world_matrix=[list(r) for r in a.get_actor_transform().to_matrix()])
        for part in ['body','door']:
            if hasattr(a,part):
                c=getattr(a,part)
                row[part]=dict(world=[list(r) for r in c.get_world_transform().to_matrix()],bounds=list(c.bounds.to_tuple()) if hasattr(c.bounds,'to_tuple') else None)
        result.setdefault('transforms',{})[label]=row
    for key, rel in [('bedroom','BedroomPilot20261024/Integration20261024/installed.json'),
                     ('v21','RefinementV21/installed.json')]:
        p = R.parent / rel
        result['existing_receipts'][key] = json.loads(p.read_text('utf8')) if p.exists() else None
except Exception:
    import traceback
    result['error'] = traceback.format_exc()
finally:
    (R/'ue-scope.json').write_text(json.dumps(result, indent=2, default=str), encoding='utf8')
if 'error' in result:
    print(result['error'])
    raise RuntimeError('Kitchen UE scope discovery failed')
print('KITCHEN_SCOPE_DISCOVERED', len(result['targets']), 'targets; dirty maps', len(result['dirty_maps']))
