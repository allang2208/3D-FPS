"""Native Normandy repairs and the working apothecary at plot 03."""
from collections import defaultdict

import unreal as u

from author_shop import pose, require, shell_transform
from dressing import STATION, furnish
from herbalist_lights import add_fixtures, add_lighting
from herbalist_living import add_living_light, furnish_living
from shop_staff_light import WICK
from herbalist_loft import add_loft
from room_daylight import SHOP_DAYLIGHT, apply_daylight
from trade_sign_layout import crossroads, hang_trade


SITE_TAG = 'VillageHerbalist.Site03'
STATE_PREFIX = 'VillageHerbalist.'
NORMANDY = '/Game/UnrealNormandy/StaticMeshes/'
DECK = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Structure/SM_CarpenterDeck'


def is_stateful_shell(part):
    """The remaining original shell stays in the village-wide instance groups."""
    name = part['mesh'].rsplit('.', 1)[-1]
    return (name.startswith(('SM_MortarChunk_', 'SM_HB_Wall4x4Chunk_', 'SM_Brick_'))
            or '_Piece' in name
            or (name in ('SM_Roof_00A','SM_WoodenFloor_00A') and part['pos'][1] < 0))


def add_shell_repairs(house, pieces, base, add):
    for part in pieces:
        if not is_stateful_shell(part):
            continue
        transform = shell_transform(part, base)
        if part['mesh'].endswith('.SM_WoodenFloor_00A'):
            # Reverse the matched pair so its replaceable plank sits on the
            # entrance side. Both permanent tiles keep the source walk height.
            inside_entry = part['pos'][0] < 0
            pitch,yaw,roll = part['rot']
            floor = shell_transform(dict(part,rot=[pitch,yaw+180,roll]),base)
            add('Common',DECK+('East' if inside_entry else 'West'),floor,profile=part['profile'])
            if inside_entry:
                add('Ruined',DECK+'WornPlank',floor,profile='NoCollision')
                add('Repaired',DECK+'SplicedPlank',floor,profile='NoCollision')
        elif part['mesh'].endswith('.SM_Roof_00A'):
            add('Ruined', NORMANDY+'SM_RoofDamaged_01A', transform, profile=part['profile'])
            add('Repaired', part['mesh'], transform, part['materials'], part['profile'])
        else:
            add('Ruined', part['mesh'], transform, part['materials'], part['profile'])

    solid = next(p for p in pieces if p['mesh'].endswith('.SM_H_OldWall_00A')
                 and p['pos'][0] < 0 and p['pos'][1] > 285 and p['pos'][2] < -200)
    west, right = -288.5354, 291.4646
    lower, upper = -297.4087, 2.5913
    # The lower west bay and upper east rear bay receive window assemblies.
    # The intact west upper rear bay stays in the shared shell.
    for x, y, z, yaw in (
        (west, 150, lower, -90), (west, -150, upper, -90),
        (right, -150, lower, 90), (right, 150, lower, 90),
        (right, -150, upper, 90),
    ):
        part = dict(solid, pos=[x,y,z], rot=[0,yaw,0])
        add('Repaired', part['mesh'], shell_transform(part, base), part['materials'], part['profile'])

    # Reuse the two upstairs Normandy window sets with their individual hinge
    # offsets. The right set drops to the street. The left set also fits each
    # side wall when turned as a complete bay, including the shutters.
    window_wall = 'SM_H_OldWall_Window_00A'
    donor = next(p for p in pieces if p['mesh'].endswith('.'+window_wall)
                 and p['pos'][0] < 0 and p['pos'][1] < 0)
    donor_x, donor_y, donor_z = donor['pos']
    fitted_wall = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Meshes/SM_SmithWindowWall_R7'
    for part in pieces:
        name = part['mesh'].rsplit('.', 1)[-1]
        x,y,z = part['pos']
        if y >= 0 or (name != window_wall and not name.startswith('SM_Window_')):
            continue
        if x > 0:
            bay = dict(part, pos=[x,y,z-290])
            add('Repaired', part['mesh'], shell_transform(bay, base), part['materials'], part['profile'])
        else:
            pitch,yaw,roll = part['rot']
            # Rotate -90 degrees about the donor wall centre, including the
            # shutter pins. Negative donor Y now sits outside the west masonry.
            bay = dict(part, pos=[west+(y-donor_y), -150-(x-donor_x), lower+(z-donor_z)],
                       rot=[pitch,yaw-90,roll])
            # The stock wall uses a single collision box across its opening.
            # This village variant uses the same render mesh and an open reveal.
            path = fitted_wall if name == window_wall else part['mesh']
            profile = 'NoCollision' if name == 'SM_Window_Frame_00A' else part['profile']
            add('Repaired', path, shell_transform(bay, base), part['materials'], profile)
            # Bedside daylight comes from the east, opposite the enclosed stairs.
            # Fit the entire window in place of the full upper masonry panel.
            bedside = dict(part, pos=[right-(y-donor_y), 150+(x-donor_x), upper+(z-donor_z)],
                           rot=[pitch,yaw+90,roll])
            add('Repaired', path, shell_transform(bedside, base), part['materials'], profile)

    # Over the upper living area the tie lands inside both wall heads.
    # The principal rafters and king post meet under the tile ridge.
    timber = NORMANDY+'SM_HW_Plank_01A'
    bounds = require(timber).get_bounding_box()
    size = bounds.max-bounds.min
    centre = (bounds.min+bounds.max)*.5
    frame = pose(house,0,0)

    def beam(a, b, width, depth):
        a, b = u.Vector(*a), u.Vector(*b)
        axis = b-a
        t = u.Transform(location=(a+b)*.5, rotation=u.MathLibrary.make_rot_from_x(axis),
                        scale=[axis.length()/size.x,width/size.y,depth/size.z])
        add('Common',timber,u.MathLibrary.compose_transforms(
            u.MathLibrary.compose_transforms(u.Transform(location=-centre),t),frame),profile='NoCollision')

    x = 1.76
    beam((x,-351,679),(x,351,679),26,23)
    beam((x,-349,685),(x,0,1023),21,19)
    beam((x,0,1023),(x,349,685),21,19)
    beam((x,0,687),(x,0,1016),15,15)
    for direction in (-1,1):
        beam((x,0,696),(x,direction*178,849),12,13)


def set_herbalist_daylight(room):
    # Meter the shelves sooner after crossing the threshold. The room's
    # existing weather-aware blend tapers off outdoors and after sundown.
    apply_daylight(room, SHOP_DAYLIGHT['03'])
    room.set_editor_property('highlight_contrast',.65)


def build_herbalist(house, pieces, base):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    subs = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles = u.SubobjectDataBlueprintFunctionLibrary
    groups = defaultdict(list)

    def add(state,path,world_transform,mats=(),profile='BlockAll',extra=()):
        groups[state,path,tuple(mats),profile,tuple(extra)].append(world_transform)

    add_shell_repairs(house,pieces,base,add)
    loft = add_loft(house,add)
    furnish(house,add)
    furnish_living(house,add)
    add_fixtures(house,add)

    def component(actor,cls):
        parent = subs.k2_gather_subobject_data_for_instance(actor)[0]
        handle,reason = subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=cls))
        comp = handles.get_associated_object(handles.get_data(handle))
        if not comp:
            raise RuntimeError(str(reason))
        return comp

    # Singletons retain their donor material permutations (including glass and
    # foliage). Original Normandy masonry instances share their static batches.
    assemblies = {}
    counts = defaultdict(int)
    for (state,path,mats,profile,extra),transforms in groups.items():
        if state not in assemblies:
            actor = actors.spawn_actor_from_class(u.Actor,u.Vector())
            actor.set_actor_label('Village_Herbalist_'+state)
            actor.tags = [SITE_TAG]
            if not actor.root_component:
                component(actor,u.SceneComponent)
            actor.root_component.set_mobility(u.ComponentMobility.STATIC)
            assemblies[state] = actor
        actor = assemblies[state]
        mesh = require(path)
        instance = len(transforms) > 1 and (path.startswith(NORMANDY) or path.startswith('/Engine/BasicShapes/'))
        for batch in ([transforms] if instance else [[t] for t in transforms]):
            cls = u.HierarchicalInstancedStaticMeshComponent if instance else u.StaticMeshComponent
            comp = component(actor,cls)
            comp.set_mobility(u.ComponentMobility.STATIC)
            comp.set_static_mesh(mesh)
            if WICK in mats:
                comp.set_cast_shadow(False)
            for i,mat in enumerate(mats):
                if mat:
                    comp.set_material(i,require(mat))
            comp.set_collision_profile_name(profile)
            comp.set_editor_property('receives_decals',False)
            tags = [STATE_PREFIX+state,*extra]
            if profile == 'NoCollision':
                tags.append(STATE_PREFIX+'NoCollision')
            comp.component_tags = tags
            if instance:
                comp.add_instances(batch,False,True,False)
            else:
                comp.set_world_transform(batch[0],False,True)
            if state == 'Repaired':
                comp.set_visibility(False)
                comp.set_hidden_in_game(True)
                comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        counts[state] += len(transforms)

    torch_lights = add_lighting(house,assemblies['Repaired'],component)
    hang_trade(assemblies['Common'],pose(house,0,0),'Herbalist')
    crossroads(actors,'Herbalist')
    living_lights = add_living_light(house,assemblies['Repaired'],component)
    station = actors.spawn_actor_from_class(u.HillsHerbalistWorkshop,u.Vector())
    station.tags = list(station.tags)+[SITE_TAG]
    station.set_actor_label('Village_03_Herbalist_Workbench')
    station_pose = pose(house,*STATION)
    station.set_actor_transform(station_pose,False,False)
    palette = require('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    definition = next(d for d in palette.get_editor_property('components')
                      if str(d.get_editor_property('id'))=='potion_workbench')
    mesh = definition.get_editor_property('mesh')
    if not mesh:
        raise RuntimeError('The potion_workbench palette entry has no mesh')
    station.set_editor_property('station_mesh',mesh)
    station.set_editor_property('shop_assemblies',list(assemblies.values()))
    station_body = station.get_component_by_class(u.StaticMeshComponent)
    station_body.set_editor_property('receives_decals',False)
    # The saved level opens in the ruined state. Configure supplies the bench
    # and its tabletop equipment when the world's repair state is applied.
    station.set_actor_hidden_in_game(True)
    station.set_actor_enable_collision(False)
    center = pose(house,0,-15,508).translation
    station.set_editor_property('repair_area_center',u.MathLibrary.inverse_transform_location(station_pose,center))
    # A square in plan covers the complete shop at each supported station quarter turn.
    station.set_editor_property('repair_area_half_extent',u.Vector(415,415,535))
    return dict(house=house[0],station=mesh.get_path_name(),state_instances=dict(counts),
                station_pose_house_cm_yaw=list(STATION),restored_side_wall_bays=7,
                restored_shop_window=True,restored_west_window=True,restored_loft_window=True,
                torch_lights=torch_lights,
                spliced_entry_plank=True,floor_count=2,loft=loft,
                living_lights=living_lights,default_state='Ruined')
