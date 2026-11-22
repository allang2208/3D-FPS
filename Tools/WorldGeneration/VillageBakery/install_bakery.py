"""Replace the east longhouse on repair. All restored pieces share the surveyed doorway frame."""
from collections import defaultdict
from pathlib import Path
import sys

import unreal as ue

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent/'AbandonedVillage'), str(HERE.parent/'VillageBlacksmith')]
from author_shop import BENCH, CRATE, KIT, require, shell_transform
from layout_geometry import plot_geometry, rotate
from shop_staff_light import WICK, configure, apply_embers
from shop_pendants import BAKERY, hang
from room_daylight import SHOP_DAYLIGHT, apply_daylight
from repair_house_instances import transfer_ruin
from village_chimney import install_plume
from bakery_shell import build_shell
from bakery_furnish import COUNTER_X, COUNTER_Y, COUNTER_YAW, build_furnishings
from bakery_oven_details import build_oven_details
from bakery_windows import install_windows

SITE = 'VillageBakery.Site'
RESTORED = 'VillageBakery.Restored'
SOLID = 'VillageBakery.Solid'
GROUP = 'VillageBakery.Group.'
FLAGS = '/Game/WorldGeneration/TemperateHills/OldChapel/Meshes/SM_ChapelYardPathStone'


def door_walk(place):
    # The public gable looks towards the mill. Its old approach along the main street
    # bends around the south corner; the miller's shorter approach reaches the same landing.
    # Each broad flag is bedded in earth, with irregular smaller pieces at the turns.
    for x, y, length, width, heading, thickness in [
        (-31,-35,78,49,8,7), (44,-36,67,45,-7,7), (8,-84,75,54,17,7),
        (55,-119,59,44,-21,6), (93,-147,60,40,24,6), (148,-146,48,35,-13,6),
        (207,-131,63,47,24,6), (282,-124,48,36,7,5), (331,-109,61,42,-19,6),
        (387,-78,70,47,21,7), (415,-20,59,36,-9,6), (426,45,51,34,17,5),
        (-48,-114,57,35,-21,6), (-87,-174,52,41,14,6), (-126,-237,42,31,-9,5),
        (-169,-283,37,28,22,5)
    ]:
        place('DoorFlags', FLAGS, (x,y,-thickness-2), (length,width,thickness), heading)


def install_bakery(actors, plan, kit):
    house = next(h for h in plan['houses'] if h[0] == '06')
    pieces = kit[house[2]]
    shape = plot_geometry(house,pieces,plan)
    # Turn the long axis back into the longhouse plot. Put its shopfront on
    # the west gable, with the rear wall clear of the east courtyard dogleg.
    heading = house[5]-180.
    dx,dy = rotate(21.,-450.,heading)
    pos = ue.Vector(shape['center'][0]*100+dx,shape['center'][1]*100+dy,4.)
    current = list(actors.get_all_level_actors())
    site = next((a for a in current if SITE in map(str,a.tags)), None)
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    handles = ue.SubobjectDataBlueprintFunctionLibrary
    transferred = 0
    if not site:
        site = actors.spawn_actor_from_class(ue.Actor,pos,ue.Rotator(yaw=heading))
        site.set_actor_label('Village_06_Bakery')
        site.tags = [SITE]
        if not site.root_component:
            parent = subs.k2_gather_subobject_data_for_instance(site)[0]
            subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent,new_class=ue.SceneComponent))
        site.root_component.set_mobility(ue.ComponentMobility.STATIC)
        site.set_actor_transform(ue.Transform(location=pos,rotation=ue.Rotator(yaw=heading)),False,True)
        scale = plan['house_scale']
        original = ue.Transform(location=[house[3]*100,house[4]*100,4-shape['floor']*scale],
                                rotation=ue.Rotator(yaw=house[5]),scale=[scale]*3)
        expected = defaultdict(list)
        for piece in pieces:
            if not piece['mesh'].endswith('.SM_Door_00A'):
                expected[piece['mesh'].split('.')[0]].append(shell_transform(piece,original).translation)
        # Household pieces can have been moved since this particular level was
        # authored. Transfer the real furnishings inside the old house walls.
        transferred = transfer_ruin(current,site,expected,shape,prefix='VillageBakery',
                                    loose_furniture={KIT+'TimberBed',KIT+'OakTable',KIT+'OakShelf',BENCH,CRATE})
    site.modify()
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]
    tagged = {tag[len(GROUP):]: c for c in site.get_components_by_class(ue.SceneComponent)
              for tag in map(str,c.component_tags) if tag.startswith(GROUP)}
    live_keys = set()
    def component(key, cls):
        live_keys.add(key)
        obj = tagged.get(key)
        if not obj:
            handle, reason = subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent,new_class=cls))
            obj = handles.get_associated_object(handles.get_data(handle))
            if not obj:
                raise RuntimeError(str(reason))
        obj.modify()
        obj.component_tags = [RESTORED,GROUP+key]
        obj.set_visibility(False)
        obj.set_hidden_in_game(True)
        return obj

    assets = {}
    groups = defaultdict(list)
    roles = defaultdict(int)
    lamp_positions = []
    def place(role,mesh_path,center_xy_bottom_z,size_xyz,yaw=0,solid=False):
        if mesh_path not in assets:
            assets[mesh_path] = require(mesh_path)
        mesh = assets[mesh_path]
        bounds = mesh.get_bounding_box()
        span = bounds.max-bounds.min
        size = ue.Vector(*size_xyz)
        scale = size/span
        root = ue.Vector((bounds.min.x+bounds.max.x)*.5,(bounds.min.y+bounds.max.y)*.5,bounds.min.z)
        frame = ue.Transform(location=center_xy_bottom_z,rotation=ue.Rotator(yaw=yaw),scale=scale)
        pose = ue.MathLibrary.compose_transforms(ue.Transform(location=-root),frame)
        groups[(mesh_path,solid)].append(pose)
        roles[role] += 1
        if 'lantern' in mesh.get_name().lower():
            x,y,z = center_xy_bottom_z
            lamp_positions.append((x,y,z+size.z*.44))

    build_shell(place)
    build_furnishings(place)
    build_oven_details(place)
    # Keep the mill delivery off the damp floor; a smaller bag has been carried
    # over to the kneading bench. The scanned bags rest on their natural sides.
    grain = '/Game/WorldGeneration/TemperateHills/VillageBakery/Grain/SM_BakeryGrainSack'
    board = '/Game/WorldGeneration/TemperateHills/VillageBakery/Furnishings/SM_BakeryCoolingBoard'
    place('DeliverySlats',board,(95,718,0),(87,46,7),-14)
    place('MillFlourDelivery',grain,(94,718,4),(74.5,33.1,21.7),-18)
    place('PrepSlats',board,(-248,520,0),(68,38,7),74)
    place('WorkingFlourSack',grain,(-249,520,4),(62,27.6,18.1),78)
    door_walk(place)
    counter = component('ServiceCounter',ue.SceneComponent)
    counter.component_tags = [GROUP+'ServiceCounter','VillageBakery.ServiceCounter']
    counter.set_relative_transform(ue.Transform(location=(COUNTER_X,COUNTER_Y,0),
                                                rotation=ue.Rotator(yaw=COUNTER_YAW)),False,True)
    for (path,solid),poses in groups.items():
        key = path+('.Block' if solid else '.Art')
        comp = component(key,ue.InstancedStaticMeshComponent)
        comp.set_mobility(ue.ComponentMobility.STATIC)
        comp.set_relative_transform(ue.Transform(),False,True)
        comp.clear_instances()
        comp.set_static_mesh(assets[path])
        if solid:
            comp.component_tags = [RESTORED,GROUP+key,SOLID,'HillsStaticSupport']
        comp.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        comp.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        comp.set_editor_property('receives_decals',False)
        comp.set_editor_property('generate_overlap_events',False)
        if 'lantern' in assets[path].get_name().lower():
            comp.set_material(0,require(WICK))
            comp.set_cast_shadow(False)
        apply_embers(comp)
        comp.add_instances(poses,False,False,False)

    # The burning wood sits beneath the stone deck. A broad, low ember light
    # belongs in that recess; the display loaves above are lit through the mouth.
    lights = [('Light0',(-245,660,40))]
    lights.extend(('Light'+str(i),p) for i,p in enumerate(lamp_positions,2))
    for key,p in lights:
        light = component(key,ue.PointLightComponent)
        light.set_mobility(ue.ComponentMobility.MOVABLE)
        light.set_relative_location(ue.Vector(*p),False,True)
        configure(light)
        light.set_editor_property('max_draw_distance',2000.)
    for key,comp in tagged.items():
        if key in live_keys:
            continue
        comp.modify()
        comp.component_tags = [GROUP+key]
        comp.set_visibility(False)
        comp.set_hidden_in_game(True)
        if isinstance(comp,ue.InstancedStaticMeshComponent):
            comp.clear_instances()
    pendant = hang(site,site.get_actor_transform(),BAKERY)
    from trade_sign_layout import hang_trade
    hang_trade(site,site.get_actor_transform(),'Bakery')
    install_plume(site,(-245,811,1150*.76+1),.45,2.5)
    window_count = install_windows(actors,site,current,require)

    room = next((a for a in current if a.get_actor_label().startswith('Village_InteriorVision_06_')),None)
    if room:
        room.modify()
        room.set_actor_label('Village_InteriorVision_06_面包屋')
        room.set_actor_transform(site.get_actor_transform(),False,True)
        room.set_editor_property('room_minimum',ue.Vector(-367,13,0))
        room.set_editor_property('room_maximum',ue.Vector(367,876,625))
        apply_daylight(room, SHOP_DAYLIGHT['06'])
    return dict(house=house[0],ruin_instances_transferred=transferred,restored_mesh_groups=len(groups),
                restored_instances=sum(roles.values()),placements=dict(roles),interior_lights=len(lights)+1,counter_pendant=pendant,
                interactive_windows=window_count,
                counter_center_cm=[COUNTER_X,COUNTER_Y,0])
