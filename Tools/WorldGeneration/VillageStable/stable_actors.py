"""Shared actor authoring for stable construction and local perimeter repairs."""
import math
import unreal as ue

ROOT = '/Game/WorldGeneration/TemperateHills/VillageStable'
ASSEMBLY = 'VillageStable.Assembly'


def load_stable_mesh(role):
    mesh = ue.load_asset(ROOT+'/Meshes/SM_Stable_'+role)
    if not mesh:
        raise RuntimeError('Missing stable mesh '+role)
    return mesh


def label_stable(actor, name, tags):
    actor.set_actor_label(name)
    actor.set_folder_path('Village/EastGateStable')
    actor.set_editor_property('tags',tags)
    return actor


def add_door(actors, name, role, leafmesh, put, x,y,z,yaw,positive,tags,actor=None):
    rot = ue.Rotator(yaw=yaw)
    pos = ue.Vector(x,y,z)
    if actor is None:
        actor = label_stable(actors.spawn_actor_from_class(ue.ColdSteelDoor,pos,rot),
                             name,[*tags,'Door.OpenInwardOnly'])
    actor.set_actor_location_and_rotation(pos,rot,False,True)
    for field,value in (('hinge_on_positive_y',positive),('open_angle_degrees',90.),
                        ('open_seconds',.95 if role=='A07' else .65),('auto_close_seconds',0.)):
        actor.set_editor_property(field,value)
    parts = {c.get_name():c for c in actor.get_components_by_class(ue.SceneComponent)}
    parts['DoorFrame'].set_static_mesh(None)
    parts['DoorFrame'].set_collision_profile_name('NoCollision')
    leaf = parts['DoorLeaf']
    leaf.set_static_mesh(leafmesh)
    leaf.set_collision_profile_name('BlockAll')
    leaf.set_relative_rotation(ue.Rotator(yaw=180 if positive else 0),False,True)
    bounds = leafmesh.get_bounding_box()
    hinge = (bounds.max.y-bounds.min.y)*(.5 if positive else -.5)
    parts['DoorHinge'].set_relative_location(ue.Vector(0,hinge,0),False,True)
    leaf.set_relative_location(ue.Vector(-(bounds.min.x+bounds.max.x)*.5,
                               -hinge-(bounds.min.y+bounds.max.y)*.5,-bounds.min.z),False,True)
    rad = math.radians(yaw)
    hinge_x = x - hinge*math.sin(rad)
    hinge_y = y + hinge*math.cos(rad)
    pintle_yaw = yaw - 90. if not positive else yaw + 90.
    if abs((yaw % 180) - 90) < 1e-3:
        pintle_yaw = 0 if hinge_x < x else 180
    put('HingePintles',hinge_x,hinge_y,z,pintle_yaw,solid=False)


def add_instances(actors, groups, mesh, prefix, tags):
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    data = ue.SubobjectDataBlueprintFunctionLibrary
    components = {}
    for (role,solid),poses in groups.items():
        actor = label_stable(actors.spawn_actor_from_class(ue.Actor,ue.Vector()),
                             prefix+role+('' if solid else '_Detail'),tags)
        parent = subs.k2_gather_subobject_data_for_instance(actor)[0]
        handle,reason = subs.add_new_subobject(ue.AddNewSubobjectParams(
            parent_handle=parent,new_class=ue.InstancedStaticMeshComponent))
        comp = data.get_associated_object(data.get_data(handle))
        if not comp:
            raise RuntimeError(str(reason))
        comp.set_mobility(ue.ComponentMobility.STATIC)
        comp.set_static_mesh(mesh(role))
        comp.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        if not solid:
            comp.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        comp.set_editor_property('receives_decals',False)
        comp.add_instances(poses,False,True,False)
        components[role,solid]=comp
    return components
