"""Dress the former kitchen plot at the inn, in the village's metre frame."""
import math
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

import unreal as u

from layout_geometry import house_paths, plot_geometry, rotate, wall_segments


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'SourceAssets/HillsVillageWindmill/Millyard'))
from earth_form import elevation

HILLS = '/Game/WorldGeneration/TemperateHills/'
YARD = HILLS+'VillageWindmill/Yard/Meshes/SM_Mill'
MESH = {
    'bank': YARD+'EarthShoulder', 'fieldstone': YARD+'FieldstoneB', 'spall': YARD+'FieldstoneC',
    'chip': HILLS+'WhiteCliffs/Meshes/Fractures/SM_QuarryChip01',
    'flake': HILLS+'WhiteCliffs/Meshes/Fractures/SM_QuarryChip04',
    'hazel': HILLS+'ForestSpecies20261110/Meshes/SM_Hazel_B',
    'bent': HILLS+'Grass/SM_Meadow_lowGrass_02_02_SM',
    'fescue': HILLS+'Grass/SM_Meadow_lowGrass_08_02_SM',
    'herb': '/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeB_01A',
}
PLANTS = {'bent','fescue','herb','hazel'}
TAG = 'TavernWestForecourt'


def component(actor, cls):
    subs=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    root=subs.k2_gather_subobject_data_for_instance(actor)[0]
    handle,reason=subs.add_new_subobject(u.AddNewSubobjectParams(parent_handle=root,new_class=cls))
    lib=u.SubobjectDataBlueprintFunctionLibrary
    obj=lib.get_associated_object(lib.get_data(handle))
    if not obj:raise RuntimeError(str(reason))
    return obj


def remove_components(actor, parts):
    if not parts:return
    subs=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    root=subs.k2_gather_subobject_data_for_instance(actor)[0]
    handles=[subs.find_handle_for_object(root,part) for part in parts]
    if subs.k2_delete_subobjects_from_instance(root,handles)!=len(handles):
        raise RuntimeError('Could not remove the old garden components')


def reserved(plan,x,y,radius):
    site = plan['tavern_forecourt']
    ox,oy = site['origin']
    a,b = rotate(x-ox,y-oy,-site['yaw'])
    return math.hypot(max(0.,abs(a+.36)-4.52), max(0.,abs(b+2.64)-1.37)) < radius+.32


def road_gap(x,y,a,b):
    dx,dy = b[0]-a[0], b[1]-a[1]
    t = max(0.,min(1.,((x-a[0])*dx+(y-a[1])*dy)/max(1.e-6,dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)-a[2]-(b[2]-a[2])*t


def relief(plan):
    data=(ROOT/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl').read_text(encoding='utf8')
    table=data.split('Relief[Rows][Columns]={',1)[1].split('};',1)[0]
    grid=[list(map(int,line.split(','))) for line in re.findall(r'\{([-0-9,]+)\}',table)]
    ex,ey=plan['surface_extent_m']
    def sample(x,y):
        xx,yy=x+ex,y+ey
        i,j=math.floor(xx),math.floor(yy)
        f,g=xx-i,yy-j
        return (1-g)*((1-f)*grid[j][i]+f*grid[j][i+1])+g*((1-f)*grid[j+1][i]+f*grid[j+1][i+1])
    return sample


def remove_earlier_plot(world,plan):
    """The two sieves share a component. Only remove instances inside this site."""
    retired = {'seedbed','ridges','carrot_sprout','carrot_young','carrot_leafy','picked_carrot','sieve'}
    removed = {}
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if 'VillageYardDressing' not in map(str,actor.tags):
            continue
        drop = []
        for comp in actor.get_components_by_class(u.InstancedStaticMeshComponent):
            role=next((str(t)[12:] for t in comp.component_tags if str(t).startswith('VillageYard.')),None)
            if role not in retired:
                continue
            indices=[]
            for i in range(comp.get_instance_count()):
                p=comp.get_instance_transform(i,True).translation
                # The soil ridges share a pivot exactly on the adjacent lane.
                if role=='ridges':
                    here=math.dist((p.x*.01,p.y*.01),plan['tavern_forecourt']['origin']) < .1
                else:
                    here=reserved(plan,p.x*.01,p.y*.01,.20)
                if here:indices.append(i)
            if indices:
                actor.modify()
                comp.modify()
                if len(indices)==comp.get_instance_count():drop.append(comp)
                elif not comp.remove_instances(indices):raise RuntimeError('Could not detach garden '+role)
                removed[role]=len(indices)
        remove_components(actor,drop)
    return removed


def dress_forecourt(world,plan,kit):
    site=plan['tavern_forecourt']
    rng=random.Random(site['seed'])
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    for old in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        if TAG in map(str,old.tags) and not actors.destroy_actor(old):
            raise RuntimeError('Could not replace the previous inn verge')
    meshes={role:u.load_asset(path) for role,path in MESH.items()}
    for role,mesh in meshes.items():
        if not mesh:raise RuntimeError('Missing forecourt mesh '+MESH[role])
    boxes={role:mesh.get_bounding_box() for role,mesh in meshes.items()}
    paths=[[(x,y,width/2) for x,y in pts] for pts,width in
           [(r['points'],r['width']) for r in plan['roads']]+house_paths(plan,kit)]
    paths.extend([site['trail'],plan['tavern']['inn']['hall_road']['stations']])
    for piece,width in wall_segments(plan):
        paths.append([(*piece[1:3],width),(*piece[3:5],width)])
    segments=[(a,b) for pts in paths for a,b in zip(pts,pts[1:])]
    hall=next(h for h in plan['houses'] if h[0]==plan['tavern']['house'])
    shell=plot_geometry(hall,kit[hall[2]],plan)
    def clear(x,y,r):
        if any(road_gap(x,y,a,b)<r+.07 for a,b in segments):
            return False
        along,across=rotate(x-shell['shell_center'][0],y-shell['shell_center'][1],90-shell['angle'])
        # Working envelope of the western hitch rail, feed trough and horse aisle.
        return not (-7.27-r<along<.45+r and -11.55-r<across<-6.85+r)
    terrain=relief(plan)
    rows=defaultdict(list)
    banks=[]
    for x,y,angle,sx,sy,sz in site['banks']:
        # The narrow windmill shoulder tapers below the village terrain on all sides.
        samples=[rotate(a,b,angle) for a,b in [(0,0),(-1.26*sx,0),(1.26*sx,0),(0,.53*sy),(0,-.53*sy)]]
        if not all(clear(x+dx,y+dy,0) for dx,dy in samples):continue
        z=min(terrain(x+dx,y+dy) for dx,dy in samples)-.6
        banks.append((x,y,angle,sx,sy,sz,z))
        rows['bank'].append(u.Transform(location=[x*100,y*100,z],rotation=u.Rotator(yaw=angle),scale=[sx,sy,sz]))
    def surface(x,y):
        z=terrain(x,y)
        for bx,by,angle,sx,sy,sz,base in banks:
            dx,dy=rotate((x-bx)*100,(y-by)*100,-angle)
            if abs(dx)<126*sx and abs(dy)<55*sy:
                z=max(z,base+sz*elevation(dx/sx,-dy/sy,252,88,21,False))
        return z
    occupied=[]
    def place(role,x,y,w,h):
        sep=w*(.26 if role in PLANTS else .40)
        if not clear(x,y,w*.52) or any(math.hypot(x-ox,y-oy)<sep+radius for ox,oy,radius in occupied):
            return
        box=boxes[role]
        span=box.max-box.min
        scale=100*w/max(span.x,span.y)
        vertical=100*h/max(1.,span.z)
        yaw=rng.uniform(-180,180)
        mid=(box.min+box.max)*.5
        dx,dy=rotate(mid.x*scale,mid.y*scale,yaw)
        floor=surface(x,y)-(.8 if role in PLANTS else h*100*.38)
        rows[role].append(u.Transform(location=[x*100-dx,y*100-dy,floor-box.min.z*vertical],
                                      rotation=u.Rotator(yaw=yaw),scale=[scale,scale,vertical]))
        occupied.append((x,y,sep))
    for x,y,w,h in site['shrubs']:
        place('hazel',x,y,w,h)
    for x,y,heading,length,count in site['gravel_fans']:
        place('fieldstone',x,y,.34,.18)
        for i in range(count):
            t=rng.random()
            dx,dy=rotate(length*t,rng.gauss(0,.12+.20*t),heading)
            w=rng.uniform(.085,.24)*(1-.50*t)
            place(rng.choice(('chip','flake','spall')),x+dx,y+dy,w,w*rng.uniform(.28,.56))
    for x,y,length,width,heading,count in site['pockets']:
        for i in range(count):
            angle=rng.uniform(0,math.tau)
            r=math.sqrt(rng.random())
            dx,dy=rotate(length*r*math.cos(angle),width*r*math.sin(angle),heading)
            role=rng.choice(('bent','bent','fescue','herb','flake','spall'))
            w=rng.uniform(.17,.49) if role in PLANTS else rng.uniform(.075,.19)
            place(role,x+dx,y+dy,w,w*rng.uniform(.27,.64))
    actor=actors.spawn_actor_from_class(u.Actor,u.Vector())
    actor.set_actor_label('Village_Tavern_West_Forecourt')
    actor.tags=[TAG]
    if not actor.root_component:component(actor,u.SceneComponent)
    actor.root_component.set_mobility(u.ComponentMobility.STATIC)
    for role,instances in rows.items():
        c=component(actor,u.HierarchicalInstancedStaticMeshComponent)
        c.set_mobility(u.ComponentMobility.STATIC)
        c.set_static_mesh(meshes[role])
        c.component_tags=['InnForecourt.'+role]
        c.set_collision_profile_name('NoCollision')
        c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        c.set_editor_property('generate_overlap_events',False)
        c.set_cast_shadow(role in ('hazel','fieldstone','bank'))
        c.set_cull_distances(*( (4400,6400) if role in ('bank','hazel') else (2300,3800) ))
        c.add_instances(instances,False,True,False)
    return {role:len(items) for role,items in rows.items()}
