"""The working lantern suspended from the eastern bay's floor joist."""
from collections import defaultdict

import unreal as u

from author_shop import pose, require, standing

LANTERN = '/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A'
CHAIN = '/Game/UndergroundTunnel/Meshes/Props/SM_ChainLink01a'
IRON = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron'
CYLINDER = '/Engine/BasicShapes/Cylinder'
PENDANT = 'VillageCarpenter.HandPendant'
REPAIRED = 'VillageCarpenter.Repaired'
NO_COLLISION = 'VillageCarpenter.NoCollision'

# The second full-width joist crosses y=-260. Its lower face is at 360-14-8.
X, Y, SOFFIT = 300., -260., 338.
LAMP_BOTTOM, LAMP_HEIGHT = 282., 36.


def indoor_wick(lamp):
    # Same Normandy flame mask as the tavern's tabletop lanterns. Its exterior
    # intensity would overexpose the glass and compete with the task light.
    folder = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces'
    name = 'MI_CarpenterPendantWick'
    library = u.EditorAssetLibrary
    if library.does_asset_exist(folder+'/'+name):
        return require(folder+'/'+name)
    instance = u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,
        u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    materials = u.MaterialEditingLibrary
    materials.set_material_instance_parent(instance,lamp.get_material(0))
    materials.set_material_instance_scalar_parameter_value(instance,'TS00_Emissive_Multiplier',15.)
    if not library.save_loaded_asset(instance,False):
        raise RuntimeError('Could not save '+name)
    return instance


def component(actor,cls):
    system = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    library = u.SubobjectDataBlueprintFunctionLibrary
    root = system.k2_gather_subobject_data_for_instance(actor)[0]
    handle,reason = system.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root,new_class=cls))
    obj = library.get_associated_object(library.get_data(handle))
    if not obj:
        raise RuntimeError(str(reason))
    return obj


def install_pendant(house,repaired):
    frame = pose(house,0,0)
    lamp = require(LANTERN)
    bounds = lamp.get_bounding_box()
    scale = LAMP_HEIGHT/(bounds.max.z-bounds.min.z)
    body = component(repaired,u.StaticMeshComponent)
    body.set_mobility(u.ComponentMobility.STATIC)
    body.set_static_mesh(lamp)
    body.set_material(0,indoor_wick(lamp))
    body.set_world_transform(standing(house,LANTERN,X,Y,LAMP_BOTTOM,-78,scale),False,True)

    # Ceiling plate sits across the 9 cm-wide soffit; the two rivets, stem
    # and pins carry the short chain down to the lantern's crown.
    fixings = []
    def fitting(x,y,z,dimensions,pitch=0.):
        local = u.Transform(location=[x,y,z],rotation=u.Rotator(pitch=pitch),
                            scale=[d/100. for d in dimensions])
        fixings.append(u.MathLibrary.compose_transforms(local,frame))
    fitting(X,Y,SOFFIT-.25,(12.,6.7,1.4))
    for side in (-1,1):
        fitting(X+side*4.1,Y,SOFFIT-1.,(1.25,1.25,.85))
    fitting(X,Y,332.6,(1.45,1.45,10.3))
    fitting(X,Y,328.0,(1.1,1.1,4.4),90.)
    fitting(X,Y,317.3,(1.1,1.1,4.4),90.)
    iron = require(IRON)
    metal = component(repaired,u.InstancedStaticMeshComponent)
    metal.set_mobility(u.ComponentMobility.STATIC)
    metal.set_static_mesh(require(CYLINDER))
    metal.set_material(0,iron)
    metal.add_instances(fixings,False,True,False)

    # The donor is a short group of interlocked links laid along local X.
    links = component(repaired,u.StaticMeshComponent)
    links.set_mobility(u.ComponentMobility.STATIC)
    chain_mesh = require(CHAIN)
    links.set_static_mesh(chain_mesh)
    links.set_material(0,iron)
    box = chain_mesh.get_bounding_box()
    link_scale = 13./(box.max.x-box.min.x)
    section = u.Transform(location=[X,Y,322.65],rotation=u.Rotator(pitch=90.,yaw=20.),
                          scale=[link_scale]*3)
    offset = u.Transform(location=-(box.max+box.min)*.5)
    links.set_world_transform(u.MathLibrary.compose_transforms(
        u.MathLibrary.compose_transforms(offset,section),frame),False,True)

    for mesh in (body,metal,links):
        mesh.component_tags = [PENDANT,REPAIRED,NO_COLLISION]
        mesh.set_collision_profile_name('NoCollision')
        mesh.set_editor_property('receives_decals',False)
        mesh.set_cull_distance(2600.)
        mesh.set_visibility(False)
        mesh.set_hidden_in_game(True)
    # The shell's opaque reservoir would occlude its own analytic lamp;
    # the joist, worker, bench and tools continue to cast real shadows.
    body.set_cast_shadow(False)

    light = component(repaired,u.SpotLightComponent)
    light.set_mobility(u.ComponentMobility.MOVABLE)
    source = pose(house,X,Y,LAMP_BOTTOM+.46*LAMP_HEIGHT).translation
    target = pose(house,297.,-208.,83.).translation
    light.set_world_location_and_rotation(source,u.MathLibrary.find_look_at_rotation(source,target),False,True)
    light.set_intensity_units(u.LightUnits.LUMENS)
    light.set_intensity(820.)
    light.set_editor_property('use_temperature',True)
    light.set_temperature(2675.)
    light.set_inner_cone_angle(31.)
    light.set_outer_cone_angle(62.)
    light.set_attenuation_radius(415.)
    light.set_source_radius(4.)
    light.set_soft_source_radius(7.)
    light.set_specular_scale(.62)
    light.set_volumetric_scattering_intensity(.075)
    light.set_cast_shadows(True)
    light.set_max_draw_distance(2400.)
    light.set_max_distance_fade_range(450.)
    light.component_tags = [PENDANT,REPAIRED]
    # HillsCarpenterWorkshop toggles light visibility on repair and reset.
    light.set_visibility(False)
    return dict(joist_house_cm=[X,Y,SOFFIT],lantern_base_cm=LAMP_BOTTOM,task_light_lumens=820)


def replace_hand_lantern(house,repaired):
    """Migrate just the downstairs fixture on the saved Village_Carpenter_Repaired."""
    old_top = -1.06+76.5
    old_x,old_y = 340.,-267.
    old_light = pose(house,old_x,old_y,old_top+20.5).translation
    lantern_mesh = require(LANTERN)
    bounds = lantern_mesh.get_bounding_box()
    span = bounds.max-bounds.min
    old_body = standing(house,LANTERN,old_x,old_y,old_top,-78,28./max(span.x,span.y,span.z)).translation
    previous = []
    instances = defaultdict(list)
    old_lights = 0
    old_lanterns = 0
    already_hanging = False
    for part in repaired.get_components_by_class(u.SceneComponent):
        if PENDANT in map(str,part.component_tags):
            previous.append(part)
            already_hanging = True
        elif isinstance(part,u.PointLightComponent) and (part.get_world_location()-old_light).length()<2.:
            previous.append(part)
            old_lights += 1
        elif isinstance(part,u.StaticMeshComponent) and part.static_mesh==lantern_mesh:
            if isinstance(part,u.InstancedStaticMeshComponent):
                for i in range(part.get_instance_count()):
                    if (part.get_instance_transform(i,True).translation-old_body).length()<2.:
                        instances[part].append(i)
                        old_lanterns += 1
            elif (part.get_world_location()-old_body).length()<2.:
                previous.append(part)
                old_lanterns += 1
    if not already_hanging and (old_lights!=1 or old_lanterns!=1):
        raise RuntimeError(f'Hand table contains {old_lanterns} matching lanterns and {old_lights} matching lights')
    if not previous and not instances:
        raise RuntimeError('The saved hand-table fixture was not found on '+repaired.get_actor_label())
    repaired.modify()
    system = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    root = system.k2_gather_subobject_data_for_instance(repaired)[0]
    if previous:
        handles = [system.find_handle_for_object(root,obj) for obj in previous]
        if system.k2_delete_subobjects_from_instance(root,handles)!=len(handles):
            raise RuntimeError('Could not replace the original carpenter fixture')
    for part,indices in instances.items():
        part.modify()
        for index in reversed(indices):
            if not part.remove_instance(index):
                raise RuntimeError('Could not remove the hand-table lantern instance')
    result = install_pendant(house,repaired)
    result.update(replaced_table_lanterns=old_lanterns,replaced_table_lights=old_lights)
    return result
