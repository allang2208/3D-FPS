"""Ground-floor finishing rack on the cold side of the working forge (all lengths in cm)."""
from collections import defaultdict

import unreal as u

from LoftR3.design import STATION

OWNER = 'VillageShop.SmithFinishRack'
OAK = '/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_00A'
WORN = '/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_01A'
SURFACES = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_Carpenter'
IRON = SURFACES + 'Iron'
BRASS = SURFACES + 'Brass'
ZHANMADAO = '/Game/Weapons/Zhanmadao20261018/V1/Meshes/SM_Zhanmadao_Complete_V1'
TANG_DAO = '/Game/Weapons/TangDao20261002/SurfaceV2/Meshes/SM_TangDao'
HAMMER = '/Game/Weapons/SteelWarhammer20261014/SM_SteelWarhammer'
KUKRI = '/Game/Weapons/Kukri20261020/SM_Kukri'
FILE = '/Game/Props/CastingStation20260926/SM_RackFile'
CYL = '/Engine/BasicShapes/Cylinder'


def _layout(mesh):
    groups = defaultdict(list)

    def add(state, path, t, material=None, collision=False):
        groups[state, path, material, collision].append(t)

    def timber(state, a, b, width, thickness, worn=False, collision=False):
        path = WORN if worn else OAK
        a, b = u.Vector(*a), u.Vector(*b)
        axis = b-a
        bounds = mesh(path).get_bounding_box()
        middle = (bounds.max+bounds.min)*.5
        span = bounds.max-bounds.min
        t = u.Transform(location=(a+b)*.5, rotation=u.MathLibrary.make_rot_from_x(axis),
                        scale=[axis.length()/span.x,width/span.y,thickness/span.z])
        add(state, path, u.MathLibrary.compose_transforms(u.Transform(location=-middle),t), collision=collision)

    def pin(state, a, b, radius, material=IRON):
        a, b = u.Vector(*a), u.Vector(*b)
        axis = b-a
        add(state, CYL, u.Transform(location=(a+b)*.5,rotation=u.MathLibrary.make_rot_from_z(axis),
                                    scale=[radius/50,radius/50,axis.length()/100]), material)

    def seated(state, path, xy, z, rot):
        bounds = mesh(path).get_bounding_box()
        basis = u.Transform(rotation=rot)
        corners = [u.MathLibrary.transform_location(basis,u.Vector(x,y,h)) for x in (bounds.min.x,bounds.max.x)
                   for y in (bounds.min.y,bounds.max.y) for h in (bounds.min.z,bounds.max.z)]
        cx = (max(p.x for p in corners)+min(p.x for p in corners))*.5
        cy = (max(p.y for p in corners)+min(p.y for p in corners))*.5
        t = u.Transform(location=[xy[0]-cx,xy[1]-cy,z-min(p.z for p in corners)],rotation=rot)
        add(state,path,t)
        return t

    # Rack backs to the solid east wall between the quench barrel at y=-210 and stock shelf
    # at y=180. Runners are self-supporting and leave the rough masonry clear.
    for y in (-149,77):
        timber('Common',(301,y,2.5),(352,y,2.5),10,8,True,True)
        timber('Common',(345,y,5),(345,y,204),8.5,8.5,True,True)
        timber('Common',(303,y,6),(344,y,53),5.3,6.5,True)
        for z in (20,94,179):
            pin('Common',(338.4,y,z),(341.8,y,z),1.15)
    for z in (20,94,179):
        timber('Common',(341,-152,z),(341,81,z),7,9,True)
    # The plinth on the two feet keeps the warhammer off the damp floor.
    for x in (314,326):
        timber('Common',(x,-151,9),(x,80,9),12,6,True,True)
    timber('Ruined',(341,-147,26),(342,27,138),3.5,5.5,True)
    timber('Repaired',(345,-145,25),(345,74,172),4,6)

    # The complete blade meshes point along local +Z. Keep the decorated flats
    # toward the aisle. The contact depths are measured at the grip and blade
    # sections of each full-size source mesh, not at its wider crossguard.
    for path, center_y, rail_z, grip_depth, blade_depth in (
        (ZHANMADAO, -50, 179, 2.27, 2.08),
        (TANG_DAO, -60, 94, 1.70, 2.17),
    ):
        bounds = mesh(path).get_bounding_box()
        width_x = bounds.max.x - bounds.min.x
        width_y = bounds.max.y - bounds.min.y
        # UE imports can swap the two transverse axes. Present the blade's
        # wide face toward the aisle, with local +Z running along the rail.
        vertical = u.Vector(0, 0, 1) if width_x >= width_y else u.Vector(-1, 0, 0)
        rotation = u.MathLibrary.make_rot_from_xz(vertical, u.Vector(0, 1, 0))
        length = bounds.max.z - bounds.min.z
        start_y = center_y - length * .5
        grip_y = start_y + length * .15
        blade_y = start_y + length * .67
        blade_height = rail_z + 1.25 + grip_depth
        add('Repaired', path, u.Transform(
            location=[320, start_y - bounds.min.z, blade_height], rotation=rotation))
        for y, depth in ((grip_y, grip_depth), (blade_y, blade_depth)):
            pin_z = blade_height - depth - 1.25
            pin('Repaired', (337.5,y,pin_z), (339.5,y,pin_z), 3.0)
            pin('Repaired', (338,y,pin_z), (315.5,y,pin_z), 1.25)
            pin('Repaired', (315.5,y,pin_z), (315.5,y,pin_z+4.0), 1.15)

    # One bent staple survives on the upper rail in the abandoned shop.
    pin('Ruined',(339,-73.5,179),(321,-73.5,177.5),1.25)
    pin('Ruined',(321,-73.5,177.5),(319,-74.5,179),1.15)

    # The heavy head sits in its own bay, clear of both blade tips.
    hammer_y = 54
    seated('Repaired',HAMMER,(320,hammer_y),12,u.Rotator(yaw=90))
    timber('Repaired',(341,hammer_y,93.5),(323,hammer_y,93.5),12.5,5)
    for v in (hammer_y-3.75,hammer_y+3.75):
        pin('Repaired',(325,v,94),(316.8,v,94.5),1.15)
        pin('Repaired',(316.8,v,94.5),(316.6,v,97.5),1.05)
    for v in (hammer_y-4.75,hammer_y+4.75):
        timber('Repaired',(313,v,14.1),(328,v,14.1),3.1,4.8)
    timber('Repaired',(328,hammer_y-5.75,14.1),(328,hammer_y+5.75,14.1),3,4.8)
    # Forged tools and a finished blade are laid on the existing counter across the aisle.
    # Project their imported bounds onto the table so neither old import pivot can float.
    def flat_tool(path,xy,angle):
        b=mesh(path).get_bounding_box()
        span=b.max-b.min
        sizes=(span.x,span.y,span.z)
        long_axis=max(range(3),key=sizes.__getitem__)
        thin_axis=min(range(3),key=sizes.__getitem__)
        directions=[u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]
        # Construct a right-handed world basis that maps length to X and thickness to Z.
        basis=[None,None,None]
        basis[long_axis]=directions[0]
        basis[thin_axis]=directions[2]
        idx=3-long_axis-thin_axis
        basis[idx]=basis[(idx+1)%3].cross(basis[(idx+2)%3])
        r=u.MathLibrary.make_rot_from_xz(basis[0],basis[2])
        rotation=u.MathLibrary.compose_rotators(r,u.Rotator(yaw=angle))
        seated('Repaired',path,xy,76.52,rotation)
    flat_tool(KUKRI,(-38,-282),8)
    flat_tool(FILE,(13,-261),-17)
    # A small sorted group of brass ferrule blanks beside the hand file.
    for x,y in ((27,-281),(30.4,-280.3),(28.8,-284.1)):
        pin('Repaired',(x,y,76.52),(x,y,79.0),1.2,BRASS)
    return groups


def install_forge_display(house=None, station=None):
    """Rebuild only the smith's weapon display in the loaded village. Caller owns map save."""
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    all_actors=list(actors.get_all_level_actors())
    if station is None:
        station=next(a for a in all_actors if a.get_actor_label()=='Village_01_Blacksmith_Forge')
    station_frame=station.get_actor_transform()
    local_floor=u.MathLibrary.compose_transforms(u.Transform(location=-u.Vector(*STATION)),station_frame)
    assets={}
    def load(path):
        if path not in assets:
            assets[path]=u.load_asset(path)
            if not assets[path]:raise RuntimeError('Missing smith display asset '+path)
        return assets[path]

    groups=_layout(load)
    owned=[a for a in all_actors if OWNER in {str(v) for v in a.tags}]
    keep=[a for a in station.get_editor_property('shop_assemblies') if a and a not in owned]
    station.modify()
    station.set_editor_property('shop_assemblies',keep)
    for a in owned:
        if not actors.destroy_actor(a):raise RuntimeError('Could not replace previous forge rack')
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles=u.SubobjectDataBlueprintFunctionLibrary
    assemblies={}
    for (state,path,material,collision),placements in groups.items():
        if state not in assemblies:
            a=actors.spawn_actor_from_class(u.Actor,u.Vector())
            a.set_actor_label('Village_Blacksmith_WeaponRack_'+state)
            a.tags=[OWNER]
            assemblies[state]=a
        actor=assemblies[state]
        # Unique weapons keep their original production material permutations.
        instanced=len(placements)>1
        cls=u.HierarchicalInstancedStaticMeshComponent if instanced else u.StaticMeshComponent
        root=sub.k2_gather_subobject_data_for_instance(actor)[0]
        handle,why=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root,new_class=cls))
        comp=handles.get_associated_object(handles.get_data(handle))
        if not comp:raise RuntimeError(str(why))
        comp.set_mobility(u.ComponentMobility.STATIC)
        comp.set_static_mesh(load(path))
        if material:comp.set_material(0,load(material))
        comp.set_editor_property('receives_decals',False)
        comp.set_collision_profile_name('BlockAll' if collision else 'NoCollision')
        tags=[] if state=='Common' else ['VillageShop.'+state]
        if not collision:tags.append('VillageShop.NoCollision')
        comp.component_tags=tags
        world_poses=[u.MathLibrary.compose_transforms(t,local_floor) for t in placements]
        if instanced:comp.add_instances(world_poses,False,True,False)
        else:comp.set_world_transform(world_poses[0],False,True)
        if state=='Repaired':
            comp.set_visibility(False)
            comp.set_hidden_in_game(True)
            comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    station.set_editor_property('shop_assemblies',keep+list(assemblies.values()))
    return {'meshes':[ZHANMADAO,TANG_DAO,HAMMER,KUKRI,FILE],
            'rack_weapons':[ZHANMADAO,TANG_DAO,HAMMER], 'counter_props':[KUKRI,FILE],
            'placements':{s:sum(len(v) for k,v in groups.items() if k[0]==s) for s in assemblies}}

