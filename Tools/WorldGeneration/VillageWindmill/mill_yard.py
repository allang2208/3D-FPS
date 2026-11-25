"""The working mill yard and three ceiling hangers, in the tower's own frame (cm)."""
from collections import Counter, defaultdict
import json
import math
import random
import sys
from pathlib import Path

import unreal as ue

from layout_geometry import rotate
from shop_staff_light import WICK, configure

HERE = Path(__file__).resolve().parents[3] / 'SourceAssets/HillsVillageWindmill/Millyard'
sys.path.insert(0,str(HERE))
from earth_form import elevation

HILLS = '/Game/WorldGeneration/TemperateHills/'
PREFIX = 'VillageWindmill.Yard.'
RESTORED = 'VillageWindmill.Restored'
SOLID = 'VillageWindmill.Solid'
PATHS = {role:HILLS+'VillageWindmill/Yard/Meshes/SM_Mill'+role for role in
         ('HayA','HayB','Chaff','Fork','Barrow','Stone','EarthShoulder','WheelRut','Hook',
          'Measure','Grain','StoneTools','SortingShade','SmokeHood','ApronWear')}
PATHS.update(Sack=HILLS+'VillageWindmill/Yard/Meshes/SM_MillTiedSack',
             Skid=HILLS+'VillageWindmill/Yard/Meshes/SM_MillOakSkid',
             Lamp='/Game/UnrealNormandy/StaticMeshes/SM_Props_Lantern_02A',
             Table=HILLS+'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakTable',
             Stool=HILLS+'VillageBlacksmith/ArtPassR2/Meshes/SM_VillageOakStool',
             Sieve=HILLS+'VillageHerbalist/Props/SM_HerbalistGatheringSieve',
             Cask='/Game/WorldGeneration/VillageTavern/Service/SM_TavernAleCask',
             ShortGrass=HILLS+'Grass/SM_Meadow_lowGrass_04_03_SM',
             TallGrass=HILLS+'Grass/SM_Meadow_grass_07_01_mesh')
for i in range(1,7):
    PATHS[f'Chip{i}'] = HILLS+f'WhiteCliffs/Meshes/Fractures/SM_QuarryChip{i:02}'
    PATHS[f'TreadChip{i}']=PATHS[f'Chip{i}']
for variant in 'ABCD':
    PATHS['MarginHazel'+variant]=HILLS+'ForestSpecies20261110/Meshes/SM_Hazel_'+variant
for variant in 'ABC':
    PATHS['MarginRock'+variant]=HILLS+'VillageWindmill/Yard/Meshes/SM_MillFieldstone'+variant
PATHS.update(MarginBank=PATHS['EarthShoulder'],MarginSurface=HILLS+'VillageWindmill/Yard/Meshes/SM_MillVergeSurface',
             MarginBent=HILLS+'Grass/SM_Meadow_lowGrass_02_02_SM',
             MarginSedge=HILLS+'Grass/SM_Meadow_grass_03_08_mesh',
             MarginTuft=HILLS+'Grass/SM_Meadow_lowGrass_09_02_SM',
             MarginFescue=HILLS+'Grass/SM_Meadow_lowGrass_08_02_SM',
             MarginStems=HILLS+'Grass/SM_Meadow_grass_05_03_mesh',
             MarginBroadleaf='/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeB_01A')
PATHS.update(GroveBeech=HILLS+'ForestSpecies20261110/Meshes/SM_BeechBackdrop_A',
             GroveBeechYoung=HILLS+'ForestSpecies20261110/Meshes/SM_BeechBackdrop_B',
             GroveAlder=HILLS+'VillageWindmill/Yard/Meshes/SM_MillGroveFieldAlder',
             GroveYoungAlder='/Game/BlackAlder/Geometry/SimpleWind/SM_BlackAlder_Sapling_01',
             GroveTwig=HILLS+'WetForest/Underfoot/SM_ForestTwig02',
             GroveSmallTwig=HILLS+'WetForest/Underfoot/SM_ForestTwig01',
             GroveStone=HILLS+'VillageWindmill/Yard/Meshes/SM_MillFieldstoneB',
             GroveSoftGrass=HILLS+'WetForest/ScannedGrass/SM_SoftWildGrassTuft',
             GroveFlower='/Game/PN_FoliageCollection/Meshes/flowerMesh/flower_07_01',
             GroveHerb='/Game/UnrealNormandy/StaticMeshes/SM_PlantTypeC_02A')

# Local +Y points out through the tower doors. Put the two banks along the back
# wall and the established hazel thicket. The furrow leads up to the single wheel.
FORMS = [('EarthShoulder',-183,-545,6,(1.05,.82,.95)),
         ('EarthShoulder',569,82,73,(.83,1.13,.76)),
         ('EarthShoulder',-660,217,13,(1.52,1.37,1.13)),
         ('EarthShoulder',-407,198,45,(.84,1.07,.78)),
         ('EarthShoulder',-193,-459,-13,(.74,1.24,.83)),
         ('WheelRut',495,434,23,(1.05,1.,1.))]
LAMP_ANCHORS = [('Receiving',-115,220,276.75,18),('Stones',-174,-155,556.75,82),
                ('Hoist',-148,-233,806.,-12)]


def install_mill_yard(site):
    site.modify()
    meshes = {role:ue.load_asset(path) for role,path in PATHS.items()}
    for role,mesh in meshes.items():
        if not mesh:
            raise RuntimeError('Missing mill-yard mesh '+PATHS[role])
    wick=ue.load_asset(WICK)
    if not wick:
        raise RuntimeError('Missing shop lamp wick '+WICK)
    ground=-site.get_actor_location().z
    groups=defaultdict(list)
    counts=Counter()
    old={t[len(PREFIX):]:c for c in site.get_components_by_class(ue.SceneComponent)
         for t in map(str,c.component_tags) if t.startswith(PREFIX)}
    subs=ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    handles=ue.SubobjectDataBlueprintFunctionLibrary
    parent=subs.k2_gather_subobject_data_for_instance(site)[0]

    def component(key,cls,restored,solid=False):
        c=old.pop(key,None)
        if not c:
            handle,error=subs.add_new_subobject(ue.AddNewSubobjectParams(parent_handle=parent,new_class=cls))
            c=handles.get_associated_object(handles.get_data(handle))
            if not c:
                raise RuntimeError(str(error))
        c.modify()
        c.component_tags=[PREFIX+key]+([RESTORED] if restored else [])+([SOLID,'HillsStaticSupport'] if solid else [])
        c.set_visibility(not restored)
        c.set_hidden_in_game(restored)
        return c

    def add(role,pose,*,solid=False,restored=True):
        groups[role,restored,solid].append(pose)
        counts[role]+=1

    def fit(role,x,y,z,size,yaw,*,solid=False):
        box=meshes[role].get_bounding_box()
        base=ue.Vector((box.min.x+box.max.x)*.5,(box.min.y+box.max.y)*.5,box.min.z)
        frame=ue.Transform(location=(x,y,z),rotation=ue.Rotator(yaw=yaw),scale=ue.Vector(*size)/(box.max-box.min))
        add(role,ue.MathLibrary.compose_transforms(ue.Transform(location=-base),frame),solid=solid)

    def native(role,x,y,z,yaw=0,*,solid=False,roll=0,scale=(1,1,1)):
        add(role,ue.Transform(location=(x,y,z),rotation=ue.Rotator(yaw=yaw,roll=roll),scale=scale),solid=solid)

    # Four bales make a dry base. Two cross the lower joints; the crown sits over both.
    # The stacks stay outside the old rectangular ruin as well as the round repair.
    def stack(x,y,z,role,size,turn):
        dx,dy=rotate(x,y,7)
        fit(role,-678+dx,380+dy,ground+z,size,7+turn,solid=True)
    for row,y in enumerate((-31,31)):
        for col,x in enumerate((-53,53)):
            stack(x,y,-1,('HayA','HayB')[(row+col)%2],(104,60,47),(-1,1,0,-2)[2*row+col])
    for x,role,turn in ((-32,'HayB',90),(31,'HayA',92)):
        stack(x,0,44,role,(111,60,46),turn)
    stack(2,1,87,'HayB',(98,56,44),-4)
    for x,y,yaw,scale in [(-656,299,5,1.15),(-597,334,62,.84),(-614,447,-21,.75),
                           (-720,302,-31,.67),(-643,268,52,.53)]:
        native('Chaff',x,y,ground,yaw,scale=(scale,scale,1))
    # Plant the tines in front; the grip rests against the player-facing upper bale.
    native('Fork',-637,478,ground,8,roll=-23)
    for x,y,yaw,s in [(-681,442,9,.98),(-621,461,-12,1.05),(-587,493,23,.76),
                       (-561,482,-26,.56),(-528,505,8,.48)]:
        native('Chaff',x,y,ground+1.2,yaw,scale=(s,s,1))

    # A second bale is being opened near the receiving door. The standing bags
    # are within carrying distance of both handles, clear of the door leaves.
    fit('HayA',440,269,ground-.8,(92,53,42),-14,solid=True)
    for x,y,yaw,scale in [(434,294,-14,.94),(382,304,32,.58),(462,245,12,.67)]:
        native('Chaff',x,y,ground,yaw,scale=(scale,scale,1))
    native('Barrow',320,360,ground-.3,-157,solid=True)
    for x,y,w,d,h,yaw in [(179,426,45,38,54,-8),(143,405,38,34,48,32)]:
        fit('Sack',x,y,ground-.8,(w,d,h),yaw)
    # The wheel is at negative chassis X. The scan has a 13 cm high bed between the handles.
    fit('Sack',313,358,ground+12.5,(44,32,43),-148)
    fit('Sack',344,370,ground+12.4,(34,29,34),-167)

    # Keep the sorting station on the straw side of the approach. Both long sides
    # of the table remain reachable, with standing room between it and the tower.
    native('Table',-350,425,ground-.5,13,solid=True)
    native('SortingShade',-350,425,ground-.5,13,solid=True)
    native('Sieve',-381,419,ground+76,11,scale=(1.03,1.03,1))
    native('Grain',-381,419,ground+77.5,23,scale=(1.28,1.18,1))
    native('Measure',-312,435,ground+76,22)
    native('Grain',-312,435,ground+96.2,27,scale=(1.13,1.26,1.48))
    fit('Stool',-421,457,ground-.3,(36,34,39),-19,solid=True)
    fit('Cask',-463,377,ground-.6,(58,58,68),28,solid=True)
    fit('Sack',-472,423,ground-.65,(37,34,51),-27)
    # Receiving bins flank the wall on the ground floor, below the hanging lamp.
    fit('Sack',-194,158,1.,(42,37,56),22)
    fit('Sack',-217,122,1.,(41,34,49),-9)

    # Two sleepers carry the horizontal spare stone at the restored dressing station.
    for y in (-484,-451):
        fit('Skid',-354,y,ground-1,(102,12,12),4)
    native('Stone',-355,-467,ground+10,32)
    # Stand the spare on edge between two chocks. Its 59 cm face and centre
    # bore can be seen from the lane behind the low wall.
    native('Stone',-426,-455,ground+33,18,roll=76,scale=(1.17,1.17,1.6))
    for x,y,turn in [(-427,-437,17),(-417,-464,21)]:
        fit('Skid',x,y,ground-.5,(54,12,10),turn)
    native('StoneTools',-354,-472,ground+15.8,12)
    for i in range(3):
        fit('Skid',-297+i*18,-470,ground-.7,(11,66-i*6,7),-9+i*4)

    for role,x,y,yaw,scale in FORMS:
        native(role,x,y,ground,yaw,solid=role=='EarthShoulder',scale=scale)

    def soil_height(x,y):
        z=0.
        for role,cx,cy,heading,s in FORMS:
            if role!='EarthShoulder':
                continue
            lx,ly=rotate(x-cx,y-cy,-heading)
            z=max(z,elevation(lx/s[0],-ly/s[1],252,88,21,False)*s[2])
        return z

    # The flat apron uses the original traffic mask on a mesh decal so wear
    # follows the mill's existing repair visibility along with the wheel rut.
    native('ApronWear',0,0,ground+1.5)

    margins=json.loads((HERE/'WorkDetails/MillVergeLayout.json').read_text(encoding='utf-8'))
    native('MarginSurface',0,0,0)
    for x,y,turn,scale,z in margins['banks']:
        native('MarginBank',x,y,z,turn,solid=True,scale=tuple(scale))
    for role,x,y,z,w,d,h,turn in margins['instances']:
        fit(role,x,y,z,(w,d,h),turn,solid=role.startswith('MarginRock'))

    # Registered to the outside of the single-wheel track. Keep the mesh's
    # native proportions and centre the trunk on its surveyed root point.
    grove=json.loads((HERE/'WorkDetails/MillEastGrove.json').read_text(encoding='utf8'))
    tree_report=[]
    for role,x,y,z,width,height,yaw,radius in grove['trees']:
        mesh=meshes[role]
        bounds=mesh.get_bounding_box()
        size=bounds.max-bounds.min
        scale=min(height/size.z,width/max(size.x,size.y))
        vertices=ue.ProceduralMeshLibrary.get_section_from_static_mesh(mesh,0,0)[0]
        # At this height most scan roots have converged on the stem, while the
        # lowermost foliage cards and bark skirts no longer bias the centre.
        band=[v for v in vertices if .035*size.z<=v.z-bounds.min.z<=.105*size.z]
        root=ue.Vector(0,0,bounds.min.z)
        if band:
            from statistics import median
            root.x=median(v.x for v in band)
            root.y=median(v.y for v in band)
        frame=ue.Transform(location=(x,y,z),rotation=ue.Rotator(yaw=yaw),scale=(scale,scale,scale))
        add(role,ue.MathLibrary.compose_transforms(ue.Transform(location=-root),frame),restored=False)
        # A narrow trunk blocks movement; leaf cards remain permeable at the road.
        trunk=component('Trunk.'+role,ue.CapsuleComponent,False,True)
        trunk.set_mobility(ue.ComponentMobility.STATIC)
        half=min(132.,size.z*scale*.28)
        trunk.set_capsule_size(radius,half,False)
        trunk.set_relative_location(ue.Vector(x,y,z+half),False,True)
        trunk.set_visibility(False)
        trunk.set_hidden_in_game(True)
        trunk.set_editor_property('generate_overlap_events',False)
        trunk.set_collision_profile_name('BlockAll')
        trunk.set_collision_enabled(ue.CollisionEnabled.QUERY_AND_PHYSICS)
        tree_report.append(dict(role=role,root_cm=[x,y,z],height_cm=round(size.z*scale),
                                crown_width_cm=round(max(size.x,size.y)*scale),trunk_radius_cm=radius))
    for role,x,y,z,w,d,h,turn in grove['instances']:
        fit(role,x,y,z,(w,d,h),turn,solid=role=='GroveStone')

    rng=random.Random(527622)
    # Fallen masonry near the wall, chips around the spare stones, and a sparse
    # gravel apron at the outer side of the cart. Leave the track centre open.
    for cx,cy,length,width,heading,count,size_range in (
        (-166,-537,120,33,6,32,(5,32)), (-485,-469,58,37,37,20,(4,21)),
        (568,90,84,28,73,21,(7,29)), (467,360,53,18,21,13,(3,14)),
        (-627,237,39,18,-12,8,(4,13)),
        (-665,219,141,34,13,23,(13,46)),(-403,200,69,26,45,12,(9,29))):
        placed=[]
        for _ in range(count*5):
            if len(placed)==count:
                break
            angle=rng.uniform(0,math.tau)
            radius=math.sqrt(rng.random())
            dx,dy=rotate(math.cos(angle)*radius*length,math.sin(angle)*radius*width,heading)
            x,y=cx+dx,cy+dy
            size=rng.uniform(*size_range)*(1.-.28*radius)
            if any(math.hypot(x-px,y-py)<(size+ps)*.37 for px,py,ps in placed):
                continue
            placed.append((x,y,size))
            height=size*rng.uniform(.37,.65)
            fit('Chip'+str(rng.randint(1,6)),x,y,ground+soil_height(x,y)-height*.38,
                (size,size*rng.uniform(.56,.89),height),rng.uniform(-180,180))

    # Flush, irregularly bedded threshold flags thin out into the dirt.
    # Mid-lane height stays below three cm, so neither feet nor wheels meet a curb.
    for x,y,w,d,angle in [
        (-51,405,49,31,12),(-8,409,37,30,-14),(34,406,42,31,8),(66,421,27,24,26),
        (-65,438,38,25,-11),(-29,439,35,26,18),(9,444,39,33,-6),(46,451,31,23,22),
        (-42,468,35,23,23),(-4,479,36,31,-19),(33,481,27,22,36),(-65,500,30,18,9),
        (-23,510,34,26,-14),(14,524,24,19,31),(-56,542,25,17,-22),(-13,559,22,16,7),
        (-73,582,17,14,23),(-39,613,15,12,-14)]:
        fit('Chip'+str(rng.randint(1,6)),x,y,ground-2.2,(w,d,rng.uniform(4.,5.2)),angle)

    # Grass and rubble collect behind the hay shelter and along the lee wall.
    # Leave the footpath, sieve and barrow workspace free.
    for cx,cy,rx,ry,heading,density in [
        (-665,225,157,45,13,19),(-438,209,74,28,45,10),(-721,302,56,23,11,7),
        (-222,-500,98,27,-15,10),(569,82,78,23,73,7)]:
        for j in range(density):
            angle=rng.uniform(0,math.tau)
            rad=math.sqrt(rng.random())
            dx,dy=rotate(rx*rad*math.cos(angle),ry*rad*math.sin(angle),heading)
            x,y=cx+dx,cy+dy
            w=rng.uniform(24,43)
            tall=j%4==0
            h=rng.uniform(28,43) if tall else rng.uniform(11,21)
            fit('TallGrass' if tall else 'ShortGrass',x,y,ground+soil_height(x,y)-1.2,
                (w,w*rng.uniform(.65,1.1),h),rng.uniform(0,360))

    lights=[]
    for name,x,y,beam,yaw in LAMP_ANCHORS:
        native('Hook',x,y,beam,yaw+90)
        bottom=beam-5.35-40.
        fit('Lamp',x,y,bottom,(21,21,40),yaw)
        native('SmokeHood',x,y,bottom+28.8,yaw)
        light=component('Light.'+name,ue.PointLightComponent,True)
        light.set_mobility(ue.ComponentMobility.MOVABLE)
        light.set_relative_location(ue.Vector(x,y,bottom+40*.42),False,True)
        configure(light)
        light.set_editor_property('max_draw_distance',2100.)
        lights.append(dict(station=name,underside_cm=[x,y,beam],lumens=light.get_editor_property('intensity'),
                           radius_cm=light.get_editor_property('attenuation_radius')))

    for (role,restored,solid),poses in groups.items():
        mesh=meshes[role]
        finishes=[slot.material_interface for slot in mesh.static_materials]
        if role=='Lamp':
            finishes[0]=wick
        if not finishes or not all(finishes):
            raise RuntimeError('Missing surface for '+role)
        instanced=len(poses)>1 and all(m.get_base_material().get_editor_property(
            'used_with_instanced_static_meshes') for m in finishes)
        key=role+('.Working' if restored else '.Common')
        batches=[poses] if instanced else [[p] for p in poses]
        for i,batch in enumerate(batches):
            cls=ue.InstancedStaticMeshComponent if instanced else ue.StaticMeshComponent
            c=component(key+('.Instances' if instanced else '.'+str(i)),cls,restored,solid)
            c.set_mobility(ue.ComponentMobility.STATIC)
            c.set_static_mesh(mesh)
            c.set_relative_transform(ue.Transform() if instanced else batch[0],False,True)
            if instanced:
                c.clear_instances()
                c.add_instances(batch,False,False,False)
                c.set_cull_distances(*((3900,6400) if role.startswith(('Chip','TreadChip')) else (8500,11500)))
            elif role.startswith(('Chip','TreadChip')):
                c.set_cull_distance(6400.)
            if role=='Lamp':
                c.set_material(0,wick)
            c.set_cast_shadow(role not in ('Lamp','WheelRut','ApronWear','Chaff','MarginSurface','MarginBent','MarginSedge','MarginBroadleaf',
                                            'MarginTuft','MarginFescue','MarginStems','ShortGrass','TallGrass',
                                            'GroveSoftGrass','GroveFlower','GroveHerb') and not role.startswith(('Chip','TreadChip')))
            if role.startswith(('Margin','Chip','TreadChip')) or role in ('ApronWear','ShortGrass','TallGrass'):
                c.set_editor_property('receives_decals',role=='MarginBank')
            c.set_editor_property('generate_overlap_events',False)
            c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
            c.set_collision_enabled(ue.CollisionEnabled.QUERY_AND_PHYSICS if solid and not restored
                                    else ue.CollisionEnabled.NO_COLLISION)
    if old:
        remove=[subs.find_handle_for_object(parent,c) for c in old.values()]
        if subs.k2_delete_subobjects_from_instance(parent,remove)!=len(remove):
            raise RuntimeError('Could not replace previous mill yard components')
    repair_visibility = {
        'persistent_mesh_instances': {role:len(poses) for (role,restored,_),poses in groups.items() if not restored},
        'restored_mesh_instances': sum(len(poses) for (_,restored,_),poses in groups.items() if restored),
        'restored_decal': 'ApronWear',
    }
    return dict(site=site.get_path_name(),instances=dict(counts),lights=lights,east_grove_trees=tree_report,
                repair_visibility=repair_visibility)
