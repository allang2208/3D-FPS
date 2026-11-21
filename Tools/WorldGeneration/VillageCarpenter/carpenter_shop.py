"""Furnish plot 04, including its real scene station and both restoration states."""
import json
from collections import defaultdict
from pathlib import Path

import unreal as u

from author_shop import CRATE, KIT, pose, require, standing
from carpenter_pendant import LANTERN, component, install_pendant
from carpenter_shell import assemble_shell
from carpenter_weapon_display import STATIC_DISPLAY, add_weapon_display

ROOT = Path(__file__).resolve().parents[3]
PROPS = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/SM_Carpenter'
QUX = '/Game/Dungeons/TunnelStyleLiving20261112/Quixel/'
STATION = (238., 248., -1.47, -90.)  # x, y, floor height, yaw in the house frame
# Standing surfaces on the floorboards inside the eastern street screen.
HAND_TABLE_BASE = -1.06
HAND_TABLE_TOP = HAND_TABLE_BASE + 76.5
RACK_BASE = -1.06
LOFT = 360.
SOIL = -4.  # pose() is referenced to the wood floor, four centimetres above the yard.
ROOM_MIN = (-378., -378., LOFT)
ROOM_MAX = (378., 378., 850.)


def furnish(house, add):
    def place(state, path, x, y, z, yaw=0, scale=1, profile='BlockAll'):
        add(state, path, standing(house, path, x, y, z, yaw, scale), profile=profile)

    def prop(state, name, *args, **kwargs):
        place(state, PROPS + name, *args, **kwargs)

    def small(path, x, y, z, yaw, length, pitch=0):
        # Scanned books stand on their spine. Fit their rotated footprint before
        # resting the lowest face on a shelf or desktop.
        bounds = require(path).get_bounding_box()
        span = bounds.max - bounds.min
        scale = length / max(span.x, span.y, span.z)
        basis = u.Transform(rotation=u.Rotator(pitch=pitch,yaw=yaw), scale=[scale]*3)
        corners = [u.MathLibrary.transform_location(basis,u.Vector(a,b,c))
                   for a in (bounds.min.x,bounds.max.x) for b in (bounds.min.y,bounds.max.y)
                   for c in (bounds.min.z,bounds.max.z)]
        cx = (max(v.x for v in corners) + min(v.x for v in corners)) / 2
        cy = (max(v.y for v in corners) + min(v.y for v in corners)) / 2
        basis.translation = u.Vector(x-cx,y-cy,z-min(v.z for v in corners))
        add('Repaired',path,u.MathLibrary.compose_transforms(basis,pose(house,0,0)),profile='NoCollision')
        return max(v.z for v in corners) - min(v.z for v in corners)

    # Stock is received in the forecourt, seasoned on the east side, cut at the
    # powered bench in the rear corner and finished at the street-side hand table.
    prop('Common','Block',-246,-529,SOIL,18)
    prop('Repaired','LogStack',-234,-703,SOIL,9)
    prop('Repaired','DryingRack',520,-150,SOIL,87)
    prop('Ruined','SpoiledStock',-226,-700,SOIL,-12)
    prop('Ruined','SpoiledStock',512,-167,SOIL,72,.86)
    place('Ruined',KIT+'AbandonedTimber',-156,-260,0,-21,.85)
    place('Ruined',CRATE,342,-50,RACK_BASE,-18,.52)
    prop('Ruined','Shavings',-256,-565,SOIL+.04,5,.50,profile='NoCollision')

    # Keep the tabletop clear around the operational saw socket and its clamps.
    place('Common',KIT+'OakTable',329,-222,HAND_TABLE_BASE,-90)
    prop('Repaired','Tools',328,-199,HAND_TABLE_TOP,-95,profile='NoCollision')
    place('Repaired',KIT+'OakShelf',345,-50,RACK_BASE,90)
    place('Repaired',CRATE,346,-50,RACK_BASE+13.5,0,.28)
    for x,y,z,yaw,scale in [(-216,-574,SOIL+.04,-27,.80),(-276,-552,SOIL+.04,73,.48),
                             (125,130,-.73,-72,.85),(116,170,-2.61,-129,.40),
                             (281,-191,-1.07,-77,.68),(278,-253,-.83,-146,.42)]:
        prop('Repaired','Shavings',x,y,z,yaw,scale,profile='NoCollision')

    # Register the current production tool by its real blade tip, then rotate
    # the handle away from the chopping face. It is an authored scenic axe.
    tools = json.loads((ROOT/'Content/ColdSteelData/production_tools.json').read_text(encoding='utf-8'))
    axe = tools['tool_axe']['tool_mesh']
    head = u.Vector(11.,0.,30.)
    tilt = u.Transform(rotation=u.Rotator(pitch=-108,yaw=-28))
    offset = u.MathLibrary.transform_location(tilt,head)
    tilt.translation = u.Vector(-246,-529,SOIL+41.) - offset
    add('Repaired',axe,u.MathLibrary.compose_transforms(tilt,pose(house,0,0)),profile='NoCollision')

    # The wide landing discharges at (-157,-100). Keep the whole western
    # circulation strip free and place the bed and everyday storage to its east.
    place('Repaired',KIT+'TimberBed',262,206,LOFT,0)
    place('Repaired',KIT+'OakShelf',62,318,LOFT,0,.87)
    place('Repaired',CRATE,79,136,LOFT,-6,.53)
    place('Repaired',KIT+'OakTable',200,-265,LOFT,0)
    place('Repaired',KIT+'OakStool',182,-172,LOFT,-13)
    small(LANTERN,237,-274,LOFT+76.5,18,30)
    book=QUX+'Book_43a26a5c/Meshes/SM_Book_43a26a5c'
    ledger=QUX+'Book_634f4e59/Meshes/SM_Book_634f4e59'
    linen=QUX+'FoldedTowel_72036b54/Meshes/SM_FoldedTowel_72036b54'
    small(book,168,-257,LOFT+76.5,-8,26,90)
    small(linen,81,317,LOFT+65.5*.87,4,33)
    h=small(ledger,38,315,LOFT+117.5*.87,0,23,90)
    small(book,39,315,LOFT+117.5*.87+h,6,20,90)
    place('Ruined',KIT+'AbandonedTimber',239,230,LOFT,8,.89)
    place('Ruined',KIT+'OakStool',245,-252,LOFT,-38)
    # Bolt the sign under the front lintel, above the right-hand working bay.
    add('Common',PROPS+'Sign',pose(house,155,-405,282),profile='NoCollision')
    add('Ruined',KIT+'ClosedPlaque',pose(house,-365,-405,146),profile='NoCollision')


def vision_room(room,house):
    room.set_actor_label('Village_InteriorVision_04_木工工坊楼上')
    room.set_actor_transform(pose(house,0,0),False,False)
    room.set_editor_property('room_minimum',u.Vector(*ROOM_MIN))
    room.set_editor_property('room_maximum',u.Vector(*ROOM_MAX))
    room.set_editor_property('additional_dark_adaptation_stops',2.25)
    room.set_editor_property('exposure_compensation',.65)
    room.set_editor_property('entrance_transition_cm',100.)


def build_workshop(house):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    groups = defaultdict(list)
    def add(state,path,transform,mats=(),profile='BlockAll',extra=()):
        groups[(state,path,tuple(mats),profile,tuple(extra))].append(transform)

    assemble_shell(house,add)
    furnish(house,add)
    display=add_weapon_display(house,add)
    assemblies={}

    for (state,path,mats,profile,extra),transforms in groups.items():
        if state not in assemblies:
            actor=actors.spawn_actor_from_class(u.Actor,u.Vector())
            actor.set_actor_label('Village_Carpenter_'+state)
            actor.tags=['VillageCarpenter.Assembly']
            assemblies[state]=actor
        actor=assemblies[state]
        # Furniture and scanned one-offs can use their original static material
        # permutations. Repeated structure and wood chips use the shared kit ISMs.
        instance=len(transforms)>1 and not path.startswith(QUX) and STATIC_DISPLAY not in extra
        for batch in ([transforms] if instance else [[t] for t in transforms]):
            comp=component(actor,u.HierarchicalInstancedStaticMeshComponent if instance else u.StaticMeshComponent)
            comp.set_mobility(u.ComponentMobility.STATIC)
            comp.set_static_mesh(require(path))
            for slot,mat in enumerate(mats):
                if mat: comp.set_material(slot,require(mat))
            comp.set_collision_profile_name(profile)
            comp.set_editor_property('receives_decals',False)
            tags=list(extra)
            if state!='Common': tags.append('VillageCarpenter.'+state)
            if profile=='NoCollision': tags.append('VillageCarpenter.NoCollision')
            comp.component_tags=tags
            if instance:
                comp.add_instances(batch,False,True,False)
            else:
                comp.set_world_transform(batch[0],False,True)
            if path.endswith('Shavings') or path.startswith(QUX):
                comp.set_cast_shadow(False)
                comp.set_cull_distance(2800.)
            if state=='Repaired':
                comp.set_visibility(False)
                comp.set_hidden_in_game(True)
                comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)

    ground_floor_lantern = install_pendant(house,assemblies['Repaired'])
    # The upstairs reading light stays on the bedroom table.
    lamp=component(assemblies['Repaired'],u.PointLightComponent)
    lamp.set_mobility(u.ComponentMobility.MOVABLE)
    lamp.set_world_location(pose(house,237,-274,LOFT+98).translation,False,True)
    lamp.set_editor_property('intensity_units',u.LightUnits.LUMENS)
    lamp.set_intensity(270.)
    lamp.set_attenuation_radius(300.)
    lamp.set_light_color(u.LinearColor(1.,.69,.40,1.))
    lamp.set_cast_shadows(False)
    lamp.set_editor_property('max_draw_distance',2400.)
    lamp.set_editor_property('max_distance_fade_range',400.)
    lamp.component_tags=['VillageCarpenter.Repaired']
    lamp.set_visibility(False)

    station=actors.spawn_actor_from_class(u.HillsCarpenterWorkshop,u.Vector())
    station.set_actor_label('Village_04_Carpenter_Workbench')
    station_pose = pose(house,*STATION)
    station.set_actor_transform(station_pose,False,False)
    palette=require('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    row=next(p for p in palette.get_editor_property('components') if str(p.get_editor_property('id'))=='woodworking_bench')
    mesh=row.get_editor_property('mesh')
    station.set_editor_property('station_mesh',mesh)
    body=station.get_component_by_class(u.StaticMeshComponent)
    body.set_static_mesh(mesh)
    body.set_editor_property('receives_decals',False)
    station.set_editor_property('shop_assemblies',list(assemblies.values()))
    # Both anchors belong to the house. Express them in the rotated station frame.
    resident = pose(house,245,-175,.12,-29)
    station.set_editor_property('resident_pose',u.MathLibrary.make_relative_transform(resident,station_pose))
    center = pose(house,80,-205,433.65).translation
    station.set_editor_property('repair_area_center',u.MathLibrary.inverse_transform_location(station_pose,center))
    station.set_editor_property('repair_area_half_extent',u.Vector(657,548,465))
    return dict(house=house[0],station_mesh=mesh.get_path_name(),assemblies=list(assemblies),
                station_pose_house_cm_yaw=STATION,resident_feet_house_cm=[245,-175,.12],
                instances={s:sum(len(v) for k,v in groups.items() if k[0]==s) for s in assemblies},
                loft_floor_cm=LOFT,authored_windows=3,weapon_display=display,ground_floor_lantern=ground_floor_lantern)
