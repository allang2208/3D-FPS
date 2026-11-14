from pathlib import Path
import unreal as u
R=Path(__file__).resolve().parent
def apply(w,req):
    api=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor)}
    mesh=u.load_asset('/Game/SceneTests/FreightSurfaceStudy20261112/Meshes/SM_PackingConcreteRelief')
    if not mesh:raise RuntimeError('Registered fracture scan unavailable')
    rows=[('PipeBracket',(6480,-3034.65,247),180,.64,.41),('ReturnToe',(6177.25,-2463,23),90,.62,.33),('CabinetToe',(6548,-3032.35,20),180,.30,.37)]
    for leaf,loc,yaw,width,height in rows:
        key='OppositePlatform_'+leaf;rot=u.Rotator(yaw=yaw)
        a=actors.get(key) or api.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*loc),rot)
        a.set_actor_label(key);a.set_folder_path('StationLine/OppositePlatform');a.set_actor_scale3d(u.Vector(width,.80,height))
        c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_collision_profile_name('NoCollision');c.set_editor_property('can_ever_affect_navigation',False);c.set_cast_shadow(False)
    return [i[0] for i in rows]
