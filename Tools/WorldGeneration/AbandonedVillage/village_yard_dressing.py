"""Author the village's common outdoor spaces in metres, around the current plan."""
from array import array
from collections import Counter, defaultdict
import math
import random

import unreal as u

from village_boundary_dressing import MainStreet, dress_boundaries
from layout_geometry import house_paths, plot_geometry, rotate, wall_segments
from inn_forecourt import dress_forecourt, reserved

TAG = 'VillageYardDressing'
NORMANDY = '/Game/UnrealNormandy/StaticMeshes/'
HILLS = '/Game/WorldGeneration/TemperateHills/'
MESH = {
    'rough': NORMANDY+'SM_GrassTall_00A',
    'seedhead': NORMANDY+'SM_GrassTall_01A', 'bent': NORMANDY+'SM_Grass_01A',
    'stone': NORMANDY+'SM_Stone_01A', 'shard': NORMANDY+'SM_Stone_03A',
    'chips': NORMANDY+'SM_DebrisScatter_00A',
    'tuft': HILLS+'WetForest/ScannedGrass/SM_SoftWildGrassTuft',
    'grass': HILLS+'WetForest/ScannedGrass/SM_SoftWildGrassLow',
    'herb': NORMANDY+'SM_PlantTypeB_01A', 'leaf': NORMANDY+'SM_PlantTypeC_02A',
    'twig': HILLS+'WetForest/Underfoot/SM_ForestTwig02',
    'block': HILLS+'VillageCarpenter/Props/SM_CarpenterBlock',
    'woodpile': HILLS+'VillageCarpenter/Props/SM_CarpenterLogStack',
    'timber': HILLS+'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageAbandonedTimber',
    'sorting_table': HILLS+'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakTable',
    'sieve': HILLS+'VillageHerbalist/Props/SM_HerbalistGatheringSieve',
    'pot': HILLS+'VillageHerbalist/Props/SM_HerbalistWindowPot',
    'cask': '/Game/WorldGeneration/VillageTavern/Service/SM_TavernAleCask',
    'tap_cask': '/Game/WorldGeneration/VillageTavern/Service/SM_TavernTapCask',
    'pitcher': '/Game/WorldGeneration/VillageTavern/Service/SM_TavernPitcher',
}
PLANTS = {'tuft','grass','herb','leaf','rough','seedhead','bent'}
STONES = {'stone','shard'}
YARDS = {
    # The tapped barrel has its own notched cradle. The spout faces the standing space.
    # The head of the reserve barrel is inset below the rim and can take the empty pitcher.
    '02': ((2.7,1.65), [
        ('tap_cask',-.44,0,.84,-90,None), ('cask',.43,-.06,.65,8,None),
        ('pitcher',.48,-.04,.20,22,'cask')]),
    # Incoming stems can be screened at one end. The sorting pot and the clear working
    # surface at the other end are all reachable from the public side of the table.
    '03': ((3.25,1.92), [
        ('sorting_table',0,0,1.30,0,None), ('sieve',-.26,.035,.48,-7,'sorting_table'),
        ('pot',.35,-.09,.25,17,'sorting_table')]),
    # One domestic fuel station. Shop 04 already supplies its own working and ruined
    # timber yards. The entrances of the neighbouring houses have no need for more stock.
    '07': ((2.85,1.82), [
        ('woodpile',-.38,0,1.17,2,None), ('block',.67,.21,.44,-12,None)]),
}


def segment_distance(x,y,a,b):
    dx,dy = b[0]-a[0],b[1]-a[1]
    t = max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/max(1e-8,dx*dx+dy*dy)))
    return math.hypot(x-a[0]-dx*t,y-a[1]-dy*t)


def build_yard_dressing(world,source,plan,kit):
    samples = array('f')
    samples.frombytes((source/'DressingClearance.raw').read_bytes())
    width,height = 460,320
    if len(samples)!=width*height:
        raise RuntimeError('Invalid village dressing clearance dimensions')
    ex,ey = plan.get('surface_extent_m',plan['extent_m'])
    gx,gy = plan['extent_m']
    mesh = {role:u.load_asset(path) for role,path in MESH.items()}
    for role,obj in mesh.items():
        if not isinstance(obj,u.StaticMesh):
            raise RuntimeError('Missing village mesh '+MESH[role])
    boxes = {role:obj.get_bounding_box() for role,obj in mesh.items()}
    shapes = {h[0]:plot_geometry(h,kit[h[2]],plan) for h in plan['houses']}
    rectangles = [(s['center'],s['half'],s['angle']) for s in shapes.values()]
    rectangles += [(c['center'],c['half'],c['yaw']) for c in plan.get('service_clearings',[])]
    shoulder_rectangles = list(rectangles)
    smith = plan.get('blacksmith',{})
    if 'front_wall_clearance_local_m' in smith:
        left,right,near,far = smith['front_wall_clearance_local_m']
        house = next(h for h in plan['houses'] if h[0]==smith['house'])
        ox,oy = rotate((left+right)*.5,(near+far)*.5,house[5])
        shoulder_rectangles.append(((house[3]+ox,house[4]+oy),((right-left)*.5,(far-near)*.5),house[5]))
    paths = [(r['points'],r['width']) for r in plan['roads']] + house_paths(plan,kit)
    segments = [(a,b,w*.5+.13) for points,w in paths for a,b in zip(points,points[1:])]
    main_segments = len(plan['roads'][0]['points'])-1
    street = MainStreet(plan)
    segments += [(p[1:3],p[3:5],w+.12) for p,w in wall_segments(plan)]
    keepouts = [(x,y,1.15) for x,y in plan['rubble']]+[(x,y,.72) for x,y in plan['snags']]
    chapel = plan['chapel']
    keepouts.append((chapel['center'][0]+chapel['yard'][0]-9.,chapel['center'][1],4.8))
    occupied = []
    working_route = []
    batches = defaultdict(list)
    counts = Counter()

    def clear(x,y,r,median=False,shoulder=False):
        if abs(x)+r>gx-.35 or abs(y)+r>gy-.35:
            return False
        i,j = int((x+ex)*width/(2*ex)),int((y+ey)*height/(2*ey))
        if (not median and not shoulder and samples[j*width+i]<r) or any(math.hypot(x-a,y-b)<r+c for a,b,c in keepouts):
            return False
        for (cx,cy),(hx,hy),angle in (shoulder_rectangles if shoulder else rectangles):
            a,b = rotate(x-cx,y-cy,-angle)
            if math.hypot(max(0,abs(a)-hx),max(0,abs(b)-hy))<r+.15:
                return False
        if median:
            # In the cartway itself only the untracked centre is plantable.
            # Allow room for turning feet at crossings and for both wheel lines.
            if min(segment_distance(x,y,a,b) for a,b,_ in segments[:main_segments])+r>.50:
                return False
            return all(segment_distance(x,y,a,b)>r+w+1. for a,b,w in segments[main_segments:])
        if shoulder:
            # The full-width road exclusion raster would shear off every clump
            # at exactly the same line. Only the outer 40 cm of tread can
            # take a few short blades. Protect every other user of that raster.
            sx,sy,rx,ry = plan['square']
            if (math.hypot((x-sx)/rx,(y-sy)/ry)-1.)*min(rx,ry)<r+.15:
                return False
            cx,cy = chapel['center']
            front,back,side,_ = chapel['yard']
            if cx+front-.4-r < x < cx+back+.4+r and abs(y-cy)<side+.4+r:
                return False
            if abs(street.project(x,y)[1]) < street.half-.40+r:
                return False
            return all(segment_distance(x,y,a,b)>r+w for a,b,w in segments[main_segments:])
        return all(segment_distance(x,y,a,b)>r+w for a,b,w in segments)

    def prepare(role,x,y,size,yaw, *, support=None,median=False,shoulder=False):
        box = boxes[role]
        span = box.max-box.min
        # Dimensions refer to the long horizontal axis, including for log piles
        # and benches. Align that axis to the nominated wall or ground seam.
        scale = 100.*size/max(span.x,span.y,1.)
        if span.y>span.x:
            yaw -= 90.
        radius = .005*math.hypot(span.x,span.y)*scale
        if reserved(plan,x,y,radius):
            return None
        if not clear(x,y,radius,median,shoulder):
            return None
        # Let plant canopies mingle, while seating each solid object separately.
        separation = radius*(.38 if role in PLANTS else .82)
        if support is None and any(math.hypot(x-a,y-b)<separation+c for a,b,c in occupied):
            return None
        mid = (box.min+box.max)*.5
        ox,oy = rotate(mid.x*scale,mid.y*scale,yaw)
        z_scale = scale
        if shoulder and role in STONES:
            z_scale *= .65
        sink = span.z*z_scale*(.42 if shoulder else .26) if role in STONES else (.85 if role in PLANTS else .35)
        transform = u.Transform(location=[x*100-ox,y*100-oy,(support or 0.)-box.min.z*z_scale-sink],
                                rotation=u.Rotator(yaw=yaw),scale=[scale,scale,z_scale])
        return role,transform,(x,y,separation)

    def put(item,area):
        role,transform,footprint = item
        batches[role].append(transform)
        occupied.append(footprint)
        counts[area] += 1

    def scatter(role,x,y,size,yaw,area):
        item = prepare(role,x,y,size,yaw,shoulder=area in ('street_grass','street_scree','street_sward'))
        if item:
            put(item,area)
        return bool(item)

    for number,((along,out),props) in YARDS.items():
        shape = shapes[number]
        nx,ny = shape['normal']
        tx,ty = -ny,nx
        x = shape['entry'][0]+tx*along+nx*out
        y = shape['entry'][1]+ty*along+ny*out
        heading = math.degrees(math.atan2(ty,tx))
        surfaces = {}
        for role,a,b,size,turn,supporter in props:
            item = prepare(role,x+tx*a+nx*b,y+ty*a+ny*b,size,heading+turn,
                           support=surfaces[supporter] if supporter else None)
            if not item:
                raise RuntimeError(f'Yard {number}: no clearance for {role} at its authored station')
            put(item,'house_'+number)
            # Authored contact surfaces in local centimetres. Using the bounds
            # top would float the pitcher on the rim and the sieve on nail heads.
            if role in ('cask','sorting_table'):
                top = 68.15 if role=='cask' else 76.5
                surfaces[role] = u.MathLibrary.transform_location(item[1],u.Vector(0,0,top)).z
        # Leave a standing strip and a way back to this door as the small verge
        # plants are laid down later in the pass.
        work = (x+nx*.85,y+ny*.85)
        step = shape['step']
        for index in range(5):
            t = index/4.
            stop = (work[0]+t*(step[0]-work[0]),work[1]+t*(step[1]-work[1]),.53)
            occupied.append(stop)
            working_route.append(stop)

    # House 05 has lost its roof. Continue the fall line from its masonry pile
    # with one settled set of six broken boards, away from the intact doorway.
    cx,cy = shapes['05']['center']
    rx,ry = min(plan['rubble'],key=lambda p: math.dist(p,(cx,cy)))
    fall = math.atan2(ry-cy,rx-cx)+math.radians(-6.)
    scatter('timber',rx+1.97*math.cos(fall),ry+1.97*math.sin(fall),
            1.06,math.degrees(fall)+12.,'house_05')

    relations = dress_boundaries(world,plan,scatter)
    street.dress(plan,scatter,relations)
    street.grow_turf(plan,source,scatter)

    # Sunken lanes have short, interrupted grassy spines where the wheels
    # straddle the turf. Forks and heavily trafficked stretches stay bare.
    median_rng = random.Random(4193)
    main = plan['roads'][0]['points']
    for a,b in zip(main,main[1:]):
        dx,dy = b[0]-a[0],b[1]-a[1]
        length = math.hypot(dx,dy)
        if length<4.5:
            continue
        ux,uy = dx/length,dy/length
        centre = median_rng.uniform(.32,.68)*length
        for i in range(median_rng.randint(8,16)):
            t = centre+median_rng.uniform(-1.6,1.6)
            offset = median_rng.uniform(-.17,.17)
            role = 'grass' if i%4 else 'tuft'
            item = prepare(role,a[0]+ux*t-uy*offset,a[1]+uy*t+ux*offset,
                           median_rng.uniform(.17,.39),median_rng.uniform(-180.,180.),median=True)
            if item:
                put(item,'cartway_grass')

    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    # Share the actual foliage/ground-contact overrides on the authored
    # road verges. No changes to the original materials or shared meshes.
    verge_materials = {}
    verge_meshes = {mesh[r] for r in ('tuft','grass','herb','leaf','rough','seedhead','bent')}
    low_wall = [(p[1:3],p[3:5],w) for p,w in wall_segments(plan) if p[5] < .88]
    removed = Counter()
    for old in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if TAG in map(str,old.tags):
            if not actors.destroy_actor(old):
                raise RuntimeError('Could not replace old yard dressing')
            continue
        if not old.get_actor_label().startswith('Village_'):
            continue
        for comp in old.get_components_by_class(u.InstancedStaticMeshComponent):
            shared = comp.static_mesh
            if shared and str(comp.get_collision_profile_name()) == 'NoCollision':
                name = shared.get_name()
                pebble = name in {'SM_Stone_0%dA' % n for n in range(5)}
                lawn = name.startswith(('SM_Grass','SM_SoftWildGrass','SM_Plant','flower_'))
                # These older road bands predate the courtyards. Clear them from
                # active workspaces, and keep loose pebbles only beside low masonry.
                if (pebble or lawn) and old.get_actor_label().endswith('_'+name):
                    box = shared.get_bounding_box()
                    span = box.max-box.min
                    discard = []
                    for i in range(comp.get_instance_count()):
                        tr = comp.get_instance_transform(i, True)
                        mid = u.MathLibrary.transform_location(tr,(box.min+box.max)*.5)
                        x,y = mid.x*.01,mid.y*.01
                        radius = .005*math.hypot(span.x*tr.scale3d.x,span.y*tr.scale3d.y)
                        if pebble and radius > .27:
                            continue
                        in_use = reserved(plan,x,y,radius) or any(
                            math.hypot(x-a,y-b)<r+radius for a,b,r in working_route)
                        loose = pebble and not any(segment_distance(x,y,a,b)<w+.58 for a,b,w in low_wall)
                        # The original band pass also placed these specific
                        # two grass meshes and stones along both road faces.
                        # Replace those strips in the cart-road corridor only.
                        road_band = (pebble or name in ('SM_SoftWildGrassLow','SM_SoftWildGrassTuft')) and (
                            abs(street.project(x,y)[1]) < street.half+2.4)
                        if in_use or loose or road_band:
                            discard.append(i)
                    if discard:
                        if not comp.remove_instances(discard):
                            raise RuntimeError('Could not clear original verge at '+old.get_actor_label())
                        removed['pebbles' if pebble else 'plants'] += len(discard)
                    if pebble:
                        # A road-height RVT fade covers a palm-sized stone entirely.
                        # Retain its own albedo and normals on the exposed face.
                        for i,mat in enumerate(comp.get_editor_property('override_materials')):
                            if mat and '/EcologyUpgrade/Receivers/' in mat.get_path_name():
                                comp.set_material(i,shared.get_material(i))
            if shared not in verge_meshes:
                continue
            for i,material in enumerate(comp.get_editor_property('override_materials')):
                if material and '/EcologyUpgrade/' in material.get_path_name():
                    verge_materials[shared,i] = material
    anchor = actors.spawn_actor_from_class(u.Actor,u.Vector())
    anchor.set_actor_label('Village_Yards_And_Lanes')
    anchor.tags = [TAG]
    subs = u.get_engine_subsystem(u.SubobjectDataSubsystem)
    handles = u.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(anchor)[0]
    if not anchor.root_component:
        subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.SceneComponent))
    anchor.root_component.set_mobility(u.ComponentMobility.STATIC)
    for role,instances in batches.items():
        handle,reason = subs.add_new_subobject(u.AddNewSubobjectParams(
            parent_handle=parent,new_class=u.HierarchicalInstancedStaticMeshComponent))
        comp = handles.get_associated_object(handles.get_data(handle))
        if not comp:
            raise RuntimeError(str(reason))
        comp.set_mobility(u.ComponentMobility.STATIC)
        comp.set_static_mesh(mesh[role])
        for slot in range(comp.get_num_materials()):
            material = verge_materials.get((mesh[role],slot))
            if material:
                comp.set_material(slot,material)
        comp.component_tags = ['VillageYard.'+role]
        if role in ('cask','tap_cask','sorting_table'):
            comp.set_collision_profile_name('BlockAll')
        else:
            comp.set_collision_profile_name('NoCollision')
            comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        comp.set_editor_property('receives_decals',False)
        small = role in ('grass','tuft','twig','shard','chips')
        if small:
            comp.set_cast_shadow(False)
        comp.set_cull_distances(3800 if small else 7000,6200 if small else 11000)
        comp.add_instances(instances,False,True,False)
    # Cull after placement so the random sequence in all other yards remains stable.
    from smith_yard_clearance import clear_yard
    smith_cleared=clear_yard(world)
    from smith_yard_states import build as build_yard_states
    build_yard_states(world)
    court = dress_forecourt(world,plan,kit)
    return dict(tavern_forecourt=court,mesh_groups=len(batches),instances=sum(counts.values()),areas=dict(counts),smith_cleared=smith_cleared,
                boundary_sources=relations,old_verge_removed=dict(removed))
