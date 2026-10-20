"""Read existing game-world sight instances without changing gameplay state."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
worlds=[world] if world else []
for other in u.EditorLevelLibrary.get_pie_worlds(False):
    if all(other.get_path_name()!=w.get_path_name() for w in worlds): worlds.append(other)
def prop(obj,name):
    try: return obj.get_editor_property(name)
    except Exception: return None
def xyz(v): return [v.x,v.y,v.z]
def mesh_path(c):
    if isinstance(c,u.StaticMeshComponent):
        m=c.static_mesh
    elif isinstance(c,u.SkeletalMeshComponent):
        m=c.get_skeletal_mesh_asset()
    else: m=None
    return m.get_path_name() if m else None
def state(c):
    parent=c.get_attach_parent()
    p=prop(c,'hidden_in_game')
    return dict(path=c.get_path_name(),name=c.get_name(),type=c.get_class().get_name(),
        visible=c.is_visible(),hidden_in_game=p,mesh=mesh_path(c),
        parent=parent.get_path_name() if parent else None,socket=str(c.get_attach_socket_name()),
        world_location=xyz(c.get_world_location()),relative_location=xyz(prop(c,'relative_location')),
        relative_scale=xyz(prop(c,'relative_scale3d')))
report=dict(world=world.get_name() if world else None,worlds=[w.get_path_name() for w in worlds],pawns=[])
for w in worlds:
    for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
        components=a.get_components_by_class(u.SceneComponent)
        has_sight=any((mesh_path(c) or '').startswith('/Game/Weapons/M4FoldingSights/') for c in components)
        if not has_sight and not any(c.get_name()=='AKMViewmodel' for c in components): continue
        row=dict(actor=a.get_path_name(),class_path=a.get_class().get_path_name(),actor_hidden=prop(a,'hidden'),components=[])
        for c in components:
            if isinstance(c,(u.StaticMeshComponent,u.SkeletalMeshComponent)) or 'Camera' in c.get_name():
                row['components'].append(state(c))
        report['pawns'].append(row)
(O/'runtime_sights.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SIGHT_RESIDUAL_RUNTIME_READ world='+str(report['world'])+' pawns='+str(len(report['pawns'])))
