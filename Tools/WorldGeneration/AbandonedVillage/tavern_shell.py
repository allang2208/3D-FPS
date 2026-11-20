"""House 02, remade as an open stone hall in its original street frontage."""
import math
from collections import defaultdict
from pathlib import Path
import sys

import unreal as u

from author_shop import require
from tavern_flue import flue_roof

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'VillageTavern'))
from install_chimney import attach_chimney


SITE_TAG = 'VillageTavern.Site'
NORMANDY = '/Game/UnrealNormandy/StaticMeshes/'
DECK = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Structure/SM_CarpenterDeck'
MORTAR = '/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A'


def room_frame(house, shape):
    return u.Transform(location=[shape['center'][0]*100., shape['center'][1]*100., 4.],
                       rotation=u.Rotator(yaw=house[5]-90.))


def set_tavern_vision(room, house, shape, plan):
    room.set_actor_label('Village_InteriorVision_02_西侧酒馆')
    room.set_actor_transform(room_frame(house, shape), False, False)
    # The physical inner faces are inset from the tile edges by about 40 cm.
    horizontal = plan['house_scale']*plan['tavern']['footprint_scale']
    room.set_editor_property('room_minimum', u.Vector(-450*horizontal+38, -300*horizontal+38, 0))
    room.set_editor_property('room_maximum', u.Vector(450*horizontal-38, 300*horizontal-38, 320))
    # The entrance opens straight into a deep stone hall. Let the eye adapt over the
    # first few steps while the village's daylight system retains the exterior exposure.
    room.set_editor_property('entrance_transition_cm', 78.)
    room.set_editor_property('additional_dark_adaptation_stops', 3.1)
    room.set_editor_property('exposure_compensation', .92)


def build_tavern(house, pieces, plan, shape):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    subs = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles = u.SubobjectDataBlueprintFunctionLibrary
    frame = room_frame(house, shape)
    anchor = actors.spawn_actor_from_class(u.Actor, frame.translation, frame.rotation.rotator())
    anchor.set_actor_label('Village_02_Tavern')
    anchor.tags = [SITE_TAG]
    if not anchor.root_component:
        root_handle = subs.k2_gather_subobject_data_for_instance(anchor)[0]
        subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root_handle,new_class=u.SceneComponent))
    anchor.root_component.set_mobility(u.ComponentMobility.STATIC)
    anchor.set_actor_transform(frame, False, False)

    z_scale = plan['house_scale']
    xy_scale = z_scale * plan['tavern']['footprint_scale']
    floor = shape['floor']
    source_cx, source_cy = [(lo+hi)*.5 for lo,hi in zip(shape['room_min'][:2], shape['room_max'][:2])]
    # Donor +X points towards the back wall. In the tavern it is room +Y.
    donor = u.Transform(location=[source_cy*xy_scale, -source_cx*xy_scale, -floor*z_scale],
                        rotation=u.Rotator(yaw=90))
    batches = defaultdict(list)

    def put(part, state='Common', mesh=None, location=None, lower_roof=False, yaw_override=None):
        path = mesh or part['mesh']
        x,y,z = location or part['pos']
        sx,sy,sz = part['scale']
        if lower_roof:
            z -= 300
            if 'SM_Roof' in path and abs(y-source_cy) > 200:
                # Lengthen only the two outside bays, keeping their laps with
                # the centre tiles fixed. The original verge ended inside the masonry.
                overhang = 30.
                y += math.copysign(overhang*.5/xy_scale, y-source_cy)
                sx *= 1. + overhang/(300.*xy_scale)
        pitch,yaw,roll = part['rot']
        if yaw_override is not None:
            yaw = yaw_override
        elif 'SM_Window_Shutter_00A' in path: yaw += 55
        elif 'SM_Window_Shutter_01A' in path: yaw -= 55
        t = u.Transform(location=[x*xy_scale,y*xy_scale,z*z_scale],
                        rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),
                        scale=[sx*xy_scale,sy*xy_scale,sz*z_scale])
        materials = () if mesh else tuple(part['materials'])
        room_tile = u.MathLibrary.compose_transforms(t,donor)
        if path.endswith('.SM_RoofEnd_00A') and room_tile.translation.x > 350 and room_tile.translation.y > 90:
            path = flue_roof(require(path), room_tile)
        batches[(state,path,materials,part['profile'])].append(room_tile)

    solid = next(p for p in pieces if p['mesh'].endswith('.SM_H_OldWall_00A')
                 and p['pos'][1] < -400 and p['pos'][2] < -200)
    # Copy the stone opening and its real hinge/frame offsets as one assembly.
    # The donor window faces -X; the back and gable windows must open to their own exterior.
    window = next(p for p in pieces if p['mesh'].endswith('.SM_H_OldWall_Window_00A')
                  and p['pos'][1] > source_cy and p['pos'][2] < -200)
    trim = [p for p in pieces if p['mesh'].rsplit('.',1)[-1].startswith('SM_Window_')
            and math.dist(p['pos'],window['pos']) < 105.]

    def window_bay(wall, yaw, surviving_leaf, opening):
        put(window, location=wall['pos'], yaw_override=yaw)
        turn = math.radians(yaw-window['rot'][1])
        cs,sn = math.cos(turn),math.sin(turn)
        for fitting in trim:
            dx,dy,dz = (a-b for a,b in zip(fitting['pos'],window['pos']))
            x,y,z = wall['pos']
            hinge = (x+cs*dx-sn*dy,y+sn*dx+cs*dy,z+dz)
            name = fitting['mesh'].rsplit('.',1)[-1]
            if name=='SM_Window_Frame_00A':
                put(fitting,location=hinge,yaw_override=yaw)
                continue
            # Mirrored leaves extend along opposite mesh X axes; in the closed
            # position both are turned 180 degrees with respect to the frame.
            direction = 1 if name=='SM_Window_Shutter_01A' else -1
            put(fitting,'Repaired',location=hinge,yaw_override=yaw+direction*(180.-opening))
            if direction==surviving_leaf:
                put(fitting,'Ruined',location=hinge,yaw_override=yaw+direction*137.)

    for p in pieces:
        name = p['mesh'].rsplit('.',1)[-1]
        x,y,z = p['pos']
        if name.startswith('SM_RoofDamaged'):
            put(p,'Ruined',lower_roof=True)
            put(p,'Repaired',NORMANDY+'SM_Roof_00A',lower_roof=True)
        elif name.startswith('SM_Roof') or name=='SM_H_OldWall_Triangle_00A':
            put(p,lower_roof=True)
        elif name.startswith('SM_WoodenFloor_'):
            # These matched sections retain the Normandy boards and box collision.
            # Their joints stagger over three sleepers. Reverse one complete pair
            # so an identical repair does not repeat along the length of the hall.
            reverse_pair = y > source_cy + 150
            east = (x > source_cx) != reverse_pair
            plank = dict(p,rot=[p['rot'][0],p['rot'][1]+180*reverse_pair,p['rot'][2]])
            put(plank,mesh=DECK+('East' if east else 'West'))
            if east:
                insert = dict(plank,profile='NoCollision')
                put(insert,'Ruined',DECK+'WornPlank')
                put(insert,'Repaired',DECK+'SplicedPlank')
        elif name.startswith('SM_Window_') or name in (
                'SM_H_OldWall_Window_00A','SM_H_OldWall_Door_00A'):
            put(p)
        elif name=='SM_H_OldWall_00A' and z < -200:
            # Leave the centre behind the backbar, and the damaged street-side gable, intact.
            if x>source_cx+240. and abs(y-source_cy)>200.:
                west = y>source_cy
                window_bay(p,90.,1 if west else -1,112. if west else 98.)
            elif y>source_cy+400. and x<source_cx:
                window_bay(p,180.,-1,105.)
            elif y<source_cy-400. and x>source_cx:
                window_bay(p,0.,1,103.)
            else:
                put(p)
        elif name=='SM_H_WallCorner_00A' and z < -200:
            put(p)
        elif y < -400 and x < 0 and z < -127 and (
                'Chunk_' in name or 'Piece' in name or name.startswith('SM_Brick')):
            # The fallen street-side half of the east gable uses the actual lower ruin stones.
            put(p, 'Ruined')
    put(solid, 'Repaired', location=(solid['pos'][0]-300, *solid['pos'][1:]))

    # Exposed oak tie beams support both roof pitches and the central post at each bent.
    timber_path = NORMANDY+'SM_HW_Plank_01A'
    bounds = require(timber_path).get_bounding_box()
    middle = (bounds.max+bounds.min)*.5
    size = bounds.max-bounds.min

    def beam(a,b,depth,height,profile='BlockAll'):
        v = u.Vector(*b)-u.Vector(*a)
        rot = u.Rotator(pitch=math.degrees(math.atan2(v.z, math.hypot(v.x,v.y))),
                        yaw=math.degrees(math.atan2(v.y,v.x)))
        t = u.Transform(location=(u.Vector(*a)+u.Vector(*b))*.5, rotation=rot,
                        scale=[v.length()/size.x, depth/size.y, height/size.z])
        batches[('Common',timber_path,(),profile)].append(
            u.MathLibrary.compose_transforms(u.Transform(location=-middle),t))

    bay = 300*xy_scale
    for y in (-60*xy_scale,0,60*xy_scale):
        for i in range(3):
            beam(((i-1.5)*bay,y,-5.5),((i-.5)*bay,y,-5.5),14,6,'NoCollision')
    for x in (-.5*bay,.5*bay):
        for y in (-bay,0):
            beam((x,y,-5.6),(x,y+bay,-5.6),12,6,'NoCollision')

    # Only the central joint between each pair of rough gable halves has
    # an opening below the ridge. Repoint it within the thickness of the stone.
    for x in (-440*xy_scale,440*xy_scale):
        batches[('Repaired','/Engine/BasicShapes/Cube',(MORTAR,),'NoCollision')].append(
            u.Transform(location=[x,-1,513.],scale=[.12,.23,.41]))

    for x in (-390,0,390):
        beam((x,-423,316),(x,423,316),19,23)
        beam((x,-417,314),(x,0,646),18,18)
        beam((x,0,646),(x,417,314),18,18)
        beam((x,0,321),(x,0,639),15,16)
        for s in (-1,1):
            beam((x,0,325),(x,s*209,480),11,12)

    parent = subs.k2_gather_subobject_data_for_instance(anchor)[0]
    for (state,path,materials,profile),transforms in batches.items():
        handle,reason = subs.add_new_subobject(u.AddNewSubobjectParams(
            parent_handle=parent, new_class=u.HierarchicalInstancedStaticMeshComponent))
        comp = handles.get_associated_object(handles.get_data(handle))
        if not comp:
            raise RuntimeError(str(reason))
        comp.set_mobility(u.ComponentMobility.STATIC)
        comp.set_relative_transform(u.Transform(),False,True)
        comp.set_static_mesh(require(path))
        for slot, material in enumerate(materials):
            if material:
                comp.set_material(slot, require(material))
        comp.set_collision_profile_name(profile)
        comp.set_editor_property('receives_decals', False)
        tags = ['VillageTavern.'+state]
        tags.append('VillageTavern.NoCollision' if profile=='NoCollision' else 'HillsStaticSupport')
        comp.component_tags = tags
        comp.add_instances(transforms,False,False,False)
        if state=='Repaired':
            comp.set_visibility(False)
            comp.set_hidden_in_game(True)
            comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    chimney = attach_chimney(anchor)
    return dict(house=house[0], states=['Ruined','Repaired'], anchor=SITE_TAG, chimney=chimney,
                footprint_cm=[900*xy_scale,600*xy_scale], centre_m=shape['center'],
                heading=house[5]-90., shell_instances=sum(map(len,batches.values())))
