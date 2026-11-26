"""Assemble the east-gate stable in village-local centimetres on the existing streamed level."""
from collections import defaultdict
import math
import re
import unreal as ue

from stable_actors import ASSEMBLY as TAG, ROOT, add_door, add_instances, label_stable
from stable_perimeter import install_stable_perimeter
from stable_master_house import install_stable_master_house
from stable_ground_detail import install_ground_detail
from stable_horses import install_horses

MILL='/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Meshes/SM_Mill'
CART=[(5900,500),(5690,530),(5500,630),(5370,810),(5270,1070),(5250,1310),(5250,1600)]
HORSE=[(5140,505),(4930,630),(4770,820),(4650,1080),(4625,1350),(4625,1600)]


def load(path):
    asset=ue.load_asset(path)
    if not asset:
        raise RuntimeError('Missing stable dependency '+path)
    return asset


def distance_to_segment(x,y,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=min(1,max(0,((x-a[0])*dx+(y-a[1])*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-a[0]-t*dx,y-a[1]-t*dy)


def clear_old_scatter(actors):
    removed=defaultdict(int)
    for actor in actors.get_all_level_actors():
        if not re.match(r'^Village_\d+_',actor.get_actor_label()):
            continue
        for comp in actor.get_components_by_class(ue.InstancedStaticMeshComponent):
            mesh=comp.static_mesh
            if not mesh or not any(k in mesh.get_name().lower() for k in
                  ('grass','planttype','flower','rubblepile','deadtree','sm_stone_')):
                continue
            bounds=mesh.get_bounding_box()
            center=(bounds.min+bounds.max)*.5
            for i in reversed(range(comp.get_instance_count())):
                pose=comp.get_instance_transform(i,True)
                p=ue.MathLibrary.transform_location(pose,center)
                x,y=p.x,p.y
                if x<800 or x>6400 or y<190 or y>4720:
                    continue
                radius=min(170,max((bounds.max.x-bounds.min.x)*abs(pose.scale3d.x),
                                   (bounds.max.y-bounds.min.y)*abs(pose.scale3d.y))*.5)
                def overlaps(ax,ay,bx,by):
                    return math.hypot(max(ax-x,0,x-bx),max(ay-y,0,y-by))<=radius
                occupied=(overlaps(880,3220,5850,4680) or overlaps(4490,1590,5810,3220) or
                          any(distance_to_segment(x,y,a,b)<=width+radius for line,width in ((CART,200),(HORSE,110))
                              for a,b in zip(line,line[1:])))
                if occupied:
                    comp.modify()
                    if not comp.remove_instance(i):
                        raise RuntimeError('Could not clear reserved pad at '+str((x,y)))
                    removed[mesh.get_name()]+=1
    return dict(removed)


def install_stable(actors):
    for actor in actors.get_all_level_actors():
        if TAG in map(str,actor.tags):
            actors.destroy_actor(actor)
    cleared=clear_old_scatter(actors)
    groups=defaultdict(list)
    meshes={}
    doors=[]
    def mesh(role):
        if role not in meshes:
            src=MILL+role if role in ('HayA','HayB','Chaff','OakSkid','TiedSack') else ROOT+'/Meshes/SM_Stable_'+role
            meshes[role]=load(src)
        return meshes[role]


    def put(role,x,y,z=0,yaw=0,scale=(1,1,1),solid=True):
        groups[role,solid].append(ue.Transform(location=(x,y,z),rotation=ue.Rotator(yaw=yaw),scale=scale))

    def fit(role,x,y,z,w,d,h,yaw=0,solid=True):
        box=mesh(role).get_bounding_box()
        base=ue.Vector((box.min.x+box.max.x)*.5,(box.min.y+box.max.y)*.5,box.min.z)
        frame=ue.Transform(location=(x,y,z),rotation=ue.Rotator(yaw=yaw),scale=ue.Vector(w,d,h)/(box.max-box.min))
        groups[role,solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-base),frame))

    def door(name,role,x,y,z,yaw,positive):
        add_door(actors,'Village_Stable_'+name,role,mesh(role),put,x,y,z,yaw,positive,[TAG])
        doors.append(name)

    for i in range(6):
        x=3300+440*i
        for role,solid in (('A01_Bent',True),('PierShoes',True),('BentJoint',False)):
            put(role,x,3950,solid=solid)
        if 0<i<5:
            put('SlateSeam',x,3950,solid=False)
    for i in range(5):
        x=3520+440*i
        # End bays shelter the projecting external gables; all inner joints remain on their bents.
        roof_x=x+(-17.5 if i==0 else 17.5 if i==4 else 0)
        put('A01_Roof',roof_x,3950,scale=((475/440 if i in (0,4) else 1),1,1))
        put('LongPlates',x,3950,solid=False)
        put('RearVentWall',x,4350)
        put('AisleFlags',x,4272,-.8,solid=False)
        if i==4:
            continue
        put('A03',x,3550)
        put('RearHalfDoorSides',x,4070)
        put('A05',x+220,3812,0,90,(504/495,1,1))
        door('Stall%02d_Court'%(i+1),'A04',x,3564,3.5,90,True)
        door('Stall%02d_Aisle'%(i+1),'A04',x,4058,3.5,-90,False)
        put('HayCrib',x-181,3816,0,90)
        fit('Chaff',x-13,3810,.3,259,217,3.8,-3+i*2,False)
        fit('HayB' if i%2 else 'HayA',x-181,3819,52,94,28,31,90,False)
    put('A02',3280,3950,0,-90)
    put('A02',5520,3950,0,90)
    put('PackedFloor',4400,3950)
    for x in (5008,5492):
        put('GatePier',x,1600,scale=(24/31,1,1))
    door('WagonGate_West','A07',5136.5,1617,4.5,90,True)
    door('WagonGate_East','A07',5363.5,1617,4.5,90,False)

    for y in (3740,4136):
        put('A08',3242,y,0,90)
    put('A09',2975,4080,0,90)
    put('TroughWater',2975,4080,57.5,90,solid=False)

    # The unloading side keeps its centre open. Stack and skid sit against the east wall.
    fit('OakSkid',5426,3834,0,109,221,13)
    for i,y in enumerate((3781,3887)):
        fit('HayA' if i==0 else 'HayB',5426,y,13,101,99,53,i*2)
    fit('HayB',5426,3834,65,104,91,48,87)
    fit('TiedSack',5435,3992,0,48,43,62,15)
    fit('Chaff',5291,3810,.5,175,173,2.6,17,False)

    add_instances(actors,groups,mesh,'Village_Stable_',[TAG])
    ground=label_stable(actors.spawn_actor_from_class(ue.DecalActor,ue.Vector(4500,2400,1),ue.Rotator(pitch=-90)),'Village_Stable_Traffic',[TAG])
    decal=ground.get_component_by_class(ue.DecalComponent)
    decal.set_editor_property('decal_size',ue.Vector(9,2100,1800))
    decal.set_decal_material(load(ROOT+'/Materials/M_StableTraffic'))
    decal.set_fade_screen_size(.001)
    perimeter=install_stable_perimeter(actors)
    master_house=install_stable_master_house(actors)
    ground_detail=install_ground_detail(actors)
    residents=install_horses(actors)
    counts=defaultdict(int,perimeter['instances'])
    for role,count in master_house['instances'].items():
        counts[role]+=count
    for role,count in ground_detail['instances'].items():
        counts[role]+=count
    for (role,_),poses in groups.items():
        counts[role]+=len(poses)
    return dict(instances=dict(counts),doors=doors+perimeter['doors'],horses=residents['horses'],
                cleared_scatter=cleared,footprint_cm=[3300,3550,5500,4350],
                turning_circle_cm=[5265,2440,450],cart_opening_cm=460,horse_opening_cm=220)
