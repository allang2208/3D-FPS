"""Dress the saved R3 yard and the working interior without rebuilding their doors."""
from collections import Counter, defaultdict
import math
import random
import unreal as ue

from stable_actors import ASSEMBLY, ROOT, add_instances

TAG='VillageStable.GroundDetailR4'
YARD='/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Meshes/SM_Mill'
CHIP='/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/Fractures/SM_QuarryChip'
SURFACES=ROOT+'/GroundDetailR4/'


def install_ground_detail(actors):
    owned=[a for a in actors.get_all_level_actors() if ASSEMBLY in map(str,a.tags)]
    def part(label,cls):
        found=[a.get_component_by_class(cls) for a in owned if a.get_actor_label()=='Village_Stable_'+label]
        if len(found)!=1 or not found[0]:
            raise RuntimeError('Cannot locate stable '+label)
        return found[0]
    floor=part('PackedFloor',ue.InstancedStaticMeshComponent)
    traffic=part('Traffic',ue.DecalComponent)
    before=dict(floor=floor.get_material(0).get_path_name(),yard=traffic.get_decal_material().get_path_name(),
                floor_receives_decals=floor.get_editor_property('receives_decals'))
    def load(path):
        asset=ue.load_asset(path)
        if not asset:
            raise RuntimeError('Missing stable detail '+path)
        return asset
    meshes={k:load(YARD+k) for k in ('EarthShoulder','FieldstoneA','FieldstoneB','FieldstoneC',
                                      'Chaff','Fork','Barrow','Measure','Grain','TiedSack')}
    for i in range(1,7):
        meshes['Chip'+str(i)]=load(CHIP+f'{i:02}')
    bounds={k:v.get_bounding_box() for k,v in meshes.items()}
    floor_mat=load(SURFACES+'M_StableStallFloor')
    yard_mat=load(SURFACES+'M_StableYardSoil')
    for a in owned:
        if TAG in map(str,a.tags):
            actors.destroy_actor(a)
    floor.modify()
    floor.set_material(0,floor_mat)
    traffic.modify()
    traffic.get_owner().modify()
    traffic.get_owner().set_actor_location(ue.Vector(4500,2500,1),False,True)
    traffic.set_editor_property('decal_size',ue.Vector(9,2200,1800))
    traffic.set_decal_material(yard_mat)

    placed=defaultdict(list)
    zones=Counter()
    rng=random.Random(61748)
    def fit(zone,role,x,y,z,w,d,h,yaw,solid=False):
        b=bounds[role]
        base=ue.Vector((b.min.x+b.max.x)/2,(b.min.y+b.max.y)/2,b.min.z)
        frame=ue.Transform(location=(x,y,z),rotation=ue.Rotator(yaw=yaw),
                           scale=ue.Vector(w,d,h)/(b.max-b.min))
        placed[role,solid].append(ue.MathLibrary.compose_transforms(ue.Transform(location=-base),frame))
        zones[zone]+=1

    # Restrict stone pockets to measured margins away from every gate, the
    # watering approach, the mill drive and the full cart turning circle.
    pockets=[('bakery edge',4268,2040,45,65),('bakery edge',4410,2260,36,41),
             ('cart verge',5754,2000,19,69),('cart verge',5756,2800,18,61),
             ('water yard',2850,3505,20,58),('water yard',2851,4020,19,58),
             ('back fence',3650,4543,90,15),('back fence',4888,4547,78,16),
             ('feed gable',5754,3730,19,49)]
    for j,(zone,cx,cy,rx,ry) in enumerate(pockets):
        used=[]
        for i in range(15):
            angle=rng.uniform(0,math.tau)
            offset=math.sqrt(rng.random())
            px,py=cx+rx*offset*math.cos(angle),cy+ry*offset*math.sin(angle)
            w=rng.uniform(12,20) if not used else rng.uniform(3,10)
            if any(math.hypot(px-x,py-y)<(s+w)*.55 for x,y,s in used):
                continue
            role=('Fieldstone'+'ABC'[j%3]) if not used else 'Chip'+str(rng.randint(1,6))
            used.append((px,py,w))
            h=w*rng.uniform(.30,.49)
            fit(zone,role,px,py,-h*rng.uniform(.35,.59),w,w*rng.uniform(.61,.87),h,rng.uniform(0,180))
    for x,y,w,d,h,angle in [(5754,2290,168,52,7,88),(2870,3804,122,45,5,86),
                              (4395,4535,198,49,6,2)]:
        fit('fence footing','EarthShoulder',x,y,-2.7,w,d,h,angle)

    # Scatter outwards from the mangers and the split bale. Low crossed wisps
    # sit on the clay, away from both door sweeps and the drain flags.
    for i,cx in enumerate((3520,3960,4400,4840)):
        for dx,cy,w,d in [(-125,3760,105,49),(118,3882,87,44),(-106,3910,59,26)]:
            fit('stall '+str(i+1),'Chaff',cx+dx+rng.uniform(-6,6),cy+rng.uniform(-8,8),
                .83,w*rng.uniform(.86,1.1),d,rng.uniform(1.5,3.5),rng.uniform(-40,48))
    for px,py,w,d in [(5362,3764,74,43),(5377,3943,59,37),(5401,4056,48,28)]:
        fit('fodder store','Chaff',px,py,.85,w,d,2.5,rng.uniform(-55,55))
    fit('fodder store','TiedSack',5480,4010,.65,35,32,45,12,True)
    fit('fodder store','Measure',5448,4065,.69,29,23,20,-17,True)
    fit('fodder store','Grain',5410,4038,.80,24,16,1.7,-24)

    # The tines span local Y. Pitch around that line to seat both tips on
    # the clay; at the upper bale lip the handle reaches its west face.
    pose=ue.Transform(location=(5343,3875,1.25),rotation=ue.Rotator(pitch=-18))
    placed['Fork',False].append(pose)
    zones['fodder store']+=1
    # Park the wheelbarrow against the east gable outside the unload bay.
    fit('service strip','Barrow',5646,3820,-.35,163,65,47,91,True)
    fit('service strip','Chaff',5641,3734,.35,44,31,2.2,32)
    comps=add_instances(actors,placed,meshes.__getitem__,'Village_Stable_Dressing_',[ASSEMBLY,TAG])
    for (role,_),c in comps.items():
        if role.startswith('Chip') or role in ('Chaff','Grain'):
            c.set_cast_shadow(False)
            c.set_cull_distances(16500,19500)
    return dict(scope='ground_detail',previous_bindings=before,
                yard=traffic.get_decal_material().get_path_name(),floor=floor.get_material(0).get_path_name(),
                instances={role:c.get_instance_count() for (role,_),c in comps.items()},zones=dict(zones))
