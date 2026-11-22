"""Beam-mounted lanterns in village repair assemblies; dimensions in house-local centimetres."""
from typing import NamedTuple

import unreal as u

from author_shop import require
from shop_staff_light import WICK, configure


class Pendant(NamedTuple):
    name: str
    state: str
    anchor: tuple
    bottom: float
    height: float
    yaw: float
    slope_y: float = 0.


BAKERY = Pendant('VillageBakery.CounterPendant','VillageBakery.Restored',(34,520,292),238,29,-12)
TAVERN = Pendant('VillageTavern.CounterPendant','VillageTavern.Repaired',(0,166,304.5),249,32,-14)
HAND = Pendant('VillageCarpenter.HandPendant','VillageCarpenter.Repaired',(300,-260,338),282,36,-78)
LOFT = Pendant('VillageCarpenter.LoftPendant','VillageCarpenter.Repaired',(140,-265,775.94),618,30,18,.90)

LANTERN = '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A'
CHAIN = '/Game/UndergroundTunnel/Meshes/Props/SM_ChainLink01a'
IRON = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron'
CYLINDER = '/Engine/BasicShapes/Cylinder'


def component(actor,cls):
    system = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    library = u.SubobjectDataBlueprintFunctionLibrary
    root = system.k2_gather_subobject_data_for_instance(actor)[0]
    handle,reason = system.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root,new_class=cls))
    obj = library.get_associated_object(library.get_data(handle))
    if not obj:
        raise RuntimeError(str(reason))
    return obj


def remove_components(actor, parts):
    if not parts:
        return
    system = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    root = system.k2_gather_subobject_data_for_instance(actor)[0]
    handles = [system.find_handle_for_object(root,p) for p in parts]
    if system.k2_delete_subobjects_from_instance(root,handles) != len(handles):
        raise RuntimeError('Could not detach the previous fixture on '+actor.get_actor_label())


def light_settings(light, frame, spec):
    x,y,_ = spec.anchor
    source = u.MathLibrary.transform_location(frame,u.Vector(x,y,spec.bottom+.46*spec.height))
    light.set_mobility(u.ComponentMobility.MOVABLE)
    light.set_world_location(source,False,True)
    configure(light)
    light.set_max_draw_distance(2400.)
    light.set_max_distance_fade_range(450.)


def hang(actor, frame, spec):
    actor.modify()
    remove_components(actor,[p for p in actor.get_components_by_class(u.SceneComponent)
                             if spec.name in map(str,p.component_tags)])
    x,y,soffit = spec.anchor
    crown = spec.bottom+spec.height
    compose = u.MathLibrary.compose_transforms
    lamp = require(LANTERN)
    box = lamp.get_bounding_box()
    centre = (box.max+box.min)*.5
    scale = spec.height/(box.max.z-box.min.z)
    local = u.Transform(location=(x,y,spec.bottom),rotation=u.Rotator(yaw=spec.yaw),scale=(scale,)*3)
    pivot = u.Transform(location=(-centre.x,-centre.y,-box.min.z))
    body = component(actor,u.StaticMeshComponent)
    body.set_mobility(u.ComponentMobility.STATIC)
    body.set_static_mesh(lamp)
    body.set_material(0,require(WICK))
    body.set_world_transform(compose(compose(pivot,local),frame),False,True)
    body.set_cast_shadow(False)

    # Rivet the plate to the timber. The drop rod stays plumb under a sloping rafter.
    plate = u.MathLibrary.make_rot_from_xz(u.Vector(1,0,0),u.Vector(0,-spec.slope_y,1))
    fixings = []
    def fitting(p, dimensions, rotation):
        fixings.append(u.Transform(location=p,rotation=rotation,scale=[d/100. for d in dimensions]))
    fitting((x,y,soffit+.1),(10.,6.6,2.),plate)
    for dx in (-3.6,3.6):
        fitting((x+dx,y,soffit-.85),(1.3,1.3,1.2),plate)
    pin = crown+10.
    fitting((x,y,(soffit+pin)*.5),(1.55,1.55,soffit-pin+1.),u.Rotator())
    for z in (pin,crown-.4):
        fitting((x,y,z),(1.1,1.1,4.4),u.Rotator(pitch=90.))
    iron = require(IRON)
    metal = component(actor,u.InstancedStaticMeshComponent)
    metal.set_mobility(u.ComponentMobility.STATIC)
    metal.set_static_mesh(require(CYLINDER))
    metal.set_material(0,iron)
    metal.set_world_transform(frame,False,True)
    metal.add_instances(fixings,False,False,False)

    links = component(actor,u.StaticMeshComponent)
    links.set_mobility(u.ComponentMobility.STATIC)
    mesh = require(CHAIN)
    links.set_static_mesh(mesh)
    links.set_material(0,iron)
    box = mesh.get_bounding_box()
    scale = 13./(box.max.x-box.min.x)
    section = u.Transform(location=(x,y,crown+4.7),rotation=u.Rotator(pitch=90.,yaw=20.),scale=(scale,)*3)
    links.set_world_transform(compose(compose(u.Transform(location=-(box.min+box.max)*.5),section),frame),False,True)
    no_collision = spec.name.split('.')[0]+'.NoCollision'
    for part in (body,metal,links):
        part.component_tags=[spec.name,spec.state,no_collision]
        part.set_collision_profile_name('NoCollision')
        part.set_editor_property('receives_decals',False)
        part.set_cull_distance(2600.)
        part.set_visibility(False)
        part.set_hidden_in_game(True)

    light = component(actor,u.PointLightComponent)
    light_settings(light,frame,spec)
    light.component_tags=[spec.name,spec.state]
    light.set_visibility(False)
    return dict(joist_house_cm=spec.anchor,lantern_base_cm=spec.bottom,task_light_lumens=light.get_editor_property('intensity'))
