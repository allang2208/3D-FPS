"""Build the village sublevel in local centimetres. All Normandy meshes remain shared."""
import json
import math
import os
import random
import sys
from array import array
from collections import defaultdict
from pathlib import Path
import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
sys.path.insert(0, str(root/'Tools/WorldGeneration/AbandonedVillage'))
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageBlacksmith'))
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageCarpenter'))
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageHerbalist'))
from author_shop import build_shop, furnish_home
from carpenter_shop import build_workshop, vision_room as carpenter_vision_room
from author_shop03 import build_herbalist, is_stateful_shell, set_herbalist_daylight
from layout_geometry import plot_geometry
from room_daylight import RESIDENTIAL_DAYLIGHT, RESIDENTIAL_PLOTS, SHOP_DAYLIGHT, apply_daylight
from tavern_shell import build_tavern, set_tavern_vision
from wall_support import fit_plan
from wall_ground_material import dress_wall
from yard_house_masonry import bind_yard_wall, house_materials
source = root/'SourceAssets/TemperateHillsVillage'
plan = json.loads((source/'layout.json').read_text(encoding='utf-8'))
fit_plan(plan)
dressing = plan['ground_dressing']
kit = json.loads((source/'house-pieces.json').read_text(encoding='utf-8'))
dest = '/Game/WorldGeneration/TemperateHills/AbandonedVillage'
pack = '/Game/UnrealNormandy/'
level = dest+'/L_AbandonedVillage'
lib, edit = u.EditorAssetLibrary,u.MaterialEditingLibrary
assets = u.AssetToolsHelpers.get_asset_tools()
lib.make_directory(dest)

def require(path):
    obj = u.load_asset(path)
    if not obj: raise RuntimeError(path)
    return obj
def save(obj):
    if not lib.save_loaded_asset(obj,False): raise RuntimeError('Save failed: '+obj.get_path_name())

ex,ey=plan.get('surface_extent_m',plan['extent_m'])
def import_road_mask():
    maskname='T_VillageRoadMask'
    task=u.AssetImportTask()
    task.filename=str(source/'RoadMask.png')
    task.destination_path=dest
    task.destination_name=maskname
    task.automated=True
    task.replace_existing=True
    assets.import_asset_tasks([task])
    mask=require(dest+'/'+maskname)
    mask.srgb=False
    mask.compression_no_alpha=False
    mask.compression_settings=u.TextureCompressionSettings.TC_MASKS
    mask.address_x=mask.address_y=u.TextureAddress.TA_CLAMP
    save(mask)

import_road_mask()
world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
actors=u.get_editor_subsystem(u.EditorActorSubsystem)
sub=u.get_engine_subsystem(u.SubobjectDataSubsystem)
handles=u.SubobjectDataBlueprintFunctionLibrary
rng=random.Random(1381)
groups=defaultdict(list)
def group(mesh,transform,materials=(),profile='NoCollision'):
    groups[(mesh,tuple(materials),profile)].append(transform)
def rotate(x,y,degrees):
    a=math.radians(degrees)
    return x*math.cos(a)-y*math.sin(a),x*math.sin(a)+y*math.cos(a)
def place(mesh,x,y,z,yaw=0,scale=1,profile='NoCollision'):
    if mesh.startswith('SM_H_RubblePile_'):
        # Preserve the deterministic draw order while reserving the working yard.
        for area in plan.get('service_clearings',[]):
            if area.get('owner')=='Carpenter04':
                lx,ly=rotate(x-area['center'][0],y-area['center'][1],-area['yaw'])
                if abs(lx)<area['half'][0]+.5 and abs(ly)<area['half'][1]+.5:return
    t=u.Transform(location=[x*100,y*100,z*100],rotation=u.Rotator(yaw=yaw),scale=[scale]*3)
    group(pack+'StaticMeshes/'+mesh,t,profile=profile)

footprints=[]
house_scale=plan.get('house_scale',1.)
vision_rooms=[]
interior_receipt=[]
for house in plan['houses']:
    num,label,model,x,y,yaw=house
    pieces=kit[model]
    geometry=plot_geometry(house,pieces,plan)
    base=u.Transform(location=[x*100,y*100,4-geometry['floor']*house_scale],
                     rotation=u.Rotator(yaw=yaw),scale=[house_scale]*3)
    smith=num==plan.get('blacksmith',{}).get('house')
    carpenter=num==plan.get('carpenter',{}).get('house')
    tavern=num==plan.get('tavern',{}).get('house')
    herbalist=num==plan.get('herbalist',{}).get('house')
    if smith:
        interior_receipt.append(build_shop(house,pieces,base,geometry))
    elif carpenter:
        interior_receipt.append(build_workshop(house))
    elif tavern:
        interior_receipt.append(build_tavern(house,pieces,plan,geometry))
    elif herbalist:
        interior_receipt.append(build_herbalist(house,pieces,base))
    else:
        interior_receipt.append(furnish_home(house,pieces,geometry,house_scale,group))
    for p in ([] if smith or carpenter or tavern else pieces):
        # Leave the source doorways open. The fixed, closed meshes have no interactive hinge.
        if p['mesh'].endswith('.SM_Door_00A'):continue
        if herbalist and is_stateful_shell(p):continue
        pitch,angle,roll=p['rot']
        if 'SM_Window_Shutter_00A' in p['mesh']:
            angle+=55
        elif 'SM_Window_Shutter_01A' in p['mesh']:
            angle-=55
        piece=u.Transform(location=p['pos'],rotation=u.Rotator(pitch=pitch,yaw=angle,roll=roll),scale=p['scale'])
        group(p['mesh'],u.MathLibrary.compose_transforms(piece,base),p['materials'],p['profile'])
    vision_rooms.append((num,label,base,geometry,model))
    footprints.append((*geometry['center'],yaw,*geometry['half']))

wall_bounds={}
boundary_group_counts=defaultdict(int)
wall_footprints=[]
for yard in plan['yard_walls']:
    for wall_index,(variant,x1,y1,x2,y2,top) in enumerate(yard['pieces']):
        native=yard.get('native_instances',[])
        original=native[wall_index] if native else None
        path=original['mesh'] if original else pack+'StaticMeshes/SM_H_StoneWall_00A_Piece'+variant
        if path not in wall_bounds:
            wall_bounds[path]=require(path).get_bounding_box()
        box=wall_bounds[path]
        dx,dy=x2-x1,y2-y1
        length=math.hypot(dx,dy)
        yaw=math.degrees(math.atan2(dy,dx))
        cx,cy=(x1+x2)*50,(y1+y2)*50
        if original:
            pitch,angle,roll=original['rot']
            transform=u.Transform(location=original['pos'],rotation=u.Rotator(pitch=pitch,yaw=angle,roll=roll),scale=original['scale'])
            half_width=original['half_width_m']*100
            materials=original['materials']
        else:
            scale=length*100/(box.max.x-box.min.x)
            ox,oy=rotate((box.max.x+box.min.x)*scale*.5,(box.max.y+box.min.y)*scale*.5,yaw)
            transform=u.Transform(location=[cx-ox,cy-oy,top*100-box.max.z*scale],rotation=u.Rotator(yaw=yaw),scale=[scale]*3)
            half_width=(box.max.y-box.min.y)*scale*.5
            materials=()
        group(path,transform,materials,profile='BlockAll')
        boundary_group_counts[(path,tuple(materials),'BlockAll')]+=1
        wall_footprints.append((cx,cy,dx/length,dy/length,length*50,half_width))

def inside_wall(transform):
    p=transform.translation
    for cx,cy,ux,uy,half_length,half_width in wall_footprints:
        dx,dy=p.x-cx,p.y-cy
        if abs(dx*ux+dy*uy)<=half_length and abs(dy*ux-dx*uy)<=half_width:
            return True
    return False

for j,(x,y) in enumerate(plan['rubble']):
    place('SM_H_RubblePile_0%dA'%(j%2),x,y,-.045,rng.uniform(-180,180),rng.uniform(.63,.88),'BlockAll')
for j,(x,y) in enumerate(plan['snags']):
    place('SM_DeadTree_0%dA'%(j%3),x,y,-.06,rng.uniform(-180,180),rng.uniform(.75,.93),'BlockAll')

# The same raster that draws the roads excludes grass from their wheel tracks and doorsteps.
pixels=(source/'PlantExclusion.raw').read_bytes()
mw,mh=460,320
if len(pixels)!=mw*mh:raise RuntimeError('Unexpected plant exclusion dimensions')
def can_plant(x,y):
    i,j=int((x+ex)*mw/(2*ex)),int((y+ey)*mh/(2*ey))
    if not (0<=i<mw and 0<=j<mh) or pixels[j*mw+i]>55:return False
    for hx,hy,angle,a,b in footprints:
        lx,ly=rotate(x-hx,y-hy,-angle)
        if abs(lx)<a and abs(ly)<b:return False
    for service in plan.get('service_clearings',[]):
        lx,ly=rotate(x-service['center'][0],y-service['center'][1],-service['yaw'])
        if abs(lx)<service['half'][0] and abs(ly)<service['half'][1]:return False
    return True
for cx,cy,rx,ry in plan['meadows']:
    for j in range(round(rx*ry*3.3)):
        rr=math.sqrt(rng.random()); a=rng.uniform(0,math.tau)
        x=cx+rx*rr*math.cos(a); y=cy+ry*rr*math.sin(a)
        if not can_plant(x,y):continue
        typ=rng.choices(['Grass','GrassTall','PlantTypeA','PlantTypeB','PlantTypeC'],[42,21,14,12,11])[0]
        place('SM_%s_0%dA'%(typ,rng.randrange(3)),x,y,-.018,rng.uniform(-180,180),rng.uniform(.62,.97))

for j,(cx,cy,rx,ry) in enumerate(plan['meadows']):
    flower='/Game/PN_FoliageCollection/Meshes/flowerMesh/'+('flower_01_01' if j%2 else 'flower_03_02')
    bounds=require(flower).get_bounding_box()
    for i in range(7):
        x=cx+rx*rng.uniform(-.44,.44)
        y=cy+ry*rng.uniform(-.44,.44)
        if not can_plant(x,y):continue
        s=rng.uniform(19,32)/max(1.,bounds.max.z-bounds.min.z)
        group(flower,u.Transform(location=[x*100,y*100,-bounds.min.z*s-1],
              rotation=u.Rotator(yaw=rng.uniform(-180,180)),scale=[s]*3))

# These strips share their clearance raster and reserved PCG beds with draw_plan.py.
clearance=array('f')
clearance.frombytes((source/'DressingClearance.raw').read_bytes())
if len(clearance)!=mw*mh:raise RuntimeError('Unexpected dressing clearance dimensions')
detail_rng=random.Random(dressing['seed'])
detail_bounds={}
detail_counts=defaultdict(int)
occupied=[]
grass_root='/Game/WorldGeneration/TemperateHills/WetForest/ScannedGrass/'

def dress_point(x,y,wall):
    is_grass=detail_rng.random()<(.42 if wall else .34)
    if is_grass:
        path=grass_root+detail_rng.choice(['SM_SoftWildGrassLow','SM_SoftWildGrassTuft'])
        size=detail_rng.uniform(*dressing['grass_height_m'])
        rotation=u.Rotator(yaw=detail_rng.uniform(-180,180))
    else:
        path=pack+'StaticMeshes/SM_Stone_0%dA'%detail_rng.randrange(5)
        sizes=dressing['fallen_stone_size_m'] if wall and detail_rng.random()<.12 else dressing['pebble_size_m']
        size=detail_rng.uniform(*sizes)
        rotation=u.Rotator(pitch=detail_rng.uniform(-18,18),yaw=detail_rng.uniform(-180,180),roll=detail_rng.uniform(-24,24))
    if path not in detail_bounds:
        detail_bounds[path]=require(path).get_bounding_box()
    box=detail_bounds[path]
    span=box.max-box.min
    scale=size*100/(span.z if is_grass else max(span.x,span.y,span.z))
    oriented=u.Transform(rotation=rotation,scale=[scale]*3)
    corners=[u.MathLibrary.transform_location(oriented,u.Vector(a,b,c))
             for a in (box.min.x,box.max.x) for b in (box.min.y,box.max.y) for c in (box.min.z,box.max.z)]
    ox=(max(p.x for p in corners)+min(p.x for p in corners))*.5
    oy=(max(p.y for p in corners)+min(p.y for p in corners))*.5
    radius=max(math.hypot(p.x-ox,p.y-oy) for p in corners)/100
    radius+=.04 if is_grass else .01
    i,j=int((x+ex)*mw/(2*ex)),int((y+ey)*mh/(2*ey))
    if not (0<=i<mw and 0<=j<mh) or clearance[j*mw+i]<radius:return
    for cx,cy,ux,uy,half_length,half_width in wall_footprints:
        dx,dy=x-cx/100,y-cy/100
        along=abs(dx*ux+dy*uy)-half_length/100
        across=abs(dy*ux-dx*uy)-half_width/100
        if math.hypot(max(along,0),max(across,0))<radius+.025:return
    if any(math.hypot(x-px,y-py)<radius+pr for px,py,pr,grass in occupied if grass==is_grass):return
    if any(math.hypot(x-rx,y-ry)<radius+.85 for rx,ry in plan['rubble']):return
    bottom=min(p.z for p in corners)
    height=max(p.z for p in corners)-bottom
    burial=.7 if is_grass else height*detail_rng.uniform(.23,.42)
    transform=u.Transform(location=[x*100-ox,y*100-oy,-bottom-burial],rotation=rotation,scale=[scale]*3)
    group(path,transform)
    occupied.append((x,y,radius,is_grass))
    detail_counts['grass' if is_grass else 'stone']+=1

def dress_band(a,b,inner,outer,per_m,wall):
    dx,dy=b[0]-a[0],b[1]-a[1]
    length=math.hypot(dx,dy)
    ux,uy=dx/length,dy/length
    count=round(length*per_m)
    for side in (-1,1):
        phase=detail_rng.uniform(0,math.tau)
        for index in range(count):
            t=(index+detail_rng.uniform(.1,.9))/count
            along=length*t
            density=.56+.22*math.sin(along*.85+phase)+.15*math.sin(along*2+phase*.4)
            if detail_rng.random()>density:continue
            distance=inner+(outer-inner)*detail_rng.random()**1.4
            x=a[0]+dx*t-uy*side*distance
            y=a[1]+dy*t+ux*side*distance
            dress_point(x,y,wall)

for cx,cy,ux,uy,half_length,half_width in wall_footprints:
    # Keep scattered stones inside each surviving wall span, leaving breaches open.
    inset=12.
    a=((cx-ux*(half_length-inset))/100,(cy-uy*(half_length-inset))/100)
    b=((cx+ux*(half_length-inset))/100,(cy+uy*(half_length-inset))/100)
    dress_band(a,b,half_width/100+.04,half_width/100+dressing['wall_skirt_m'],
               dressing['wall_samples_per_m'],True)
main=plan['roads'][0]
for a,b in zip(main['points'],main['points'][1:]):
    dress_band(a,b,main['width']*.5+dressing['road_buffer_m'],main['width']*.5+dressing['road_verge_m'],
               dressing['road_samples_per_m'],False)

import runpy
ground_cache=runpy.run_path(str(root/'Tools/WorldGeneration/temperate_ground_cache.py'))
near_plants=runpy.run_path(str(root/'Tools/WorldGeneration/temperate_render_budget.py'))
village_receivers={}
yard_materials=house_materials()
# Instance per mesh, material overrides and collision profile, preserving the original house assembly.
for index,((path,mats,profile),instances) in enumerate(sorted(groups.items(),key=lambda e:str(e[0]))):
    # Cull only after distributing plants so additions never reshuffle the rest of a meadow.
    if path.rsplit('/',1)[-1].startswith(('SM_Grass','SM_Plant','flower_')):
        instances=[t for t in instances if not inside_wall(t)]
        if not instances:continue
    actor=actors.spawn_actor_from_class(u.Actor,u.Vector())
    actor.set_actor_label('Village_%03d_%s'%(index,path.rsplit('/',1)[1].split('.')[0]))
    parent=sub.k2_gather_subobject_data_for_instance(actor)[0]
    handle,reason=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.HierarchicalInstancedStaticMeshComponent))
    comp=handles.get_associated_object(handles.get_data(handle))
    if not comp:raise RuntimeError(str(reason))
    comp.set_mobility(u.ComponentMobility.STATIC)
    comp.set_static_mesh(require(path))
    for i,m in enumerate(mats):
        if m:comp.set_material(i,require(m))
    comp.set_collision_profile_name(profile)
    comp.set_editor_property('receives_decals',False)
    if profile=='NoCollision':
        comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        comp.set_cull_distances(6000,10500)
    ground_cache["dress_component"](comp,near_plants["leaf_instance"],village_receivers)
    if (path,mats,profile) in boundary_group_counts:
        if boundary_group_counts[(path,mats,profile)]!=len(instances):
            raise RuntimeError('Boundary walls must be grouped separately from house masonry')
        dress_wall(comp,village_receivers)
        bind_yard_wall(comp,yard_materials)
    comp.add_instances(instances,False,True,False)

for num,label,transform,geometry,model in vision_rooms:
    room=actors.spawn_actor_from_class(u.BuildingDaylight,transform.translation,transform.rotation.rotator())
    if num==plan.get('tavern',{}).get('house'):
        set_tavern_vision(room, next(h for h in plan['houses'] if h[0]==num),geometry,plan)
        continue
    if num==plan.get('carpenter',{}).get('house'):
        carpenter_vision_room(room,next(h for h in plan['houses'] if h[0]==num))
        continue
    room.set_actor_label('Village_InteriorVision_'+num+'_'+label)
    room.set_actor_transform(transform,False,False)
    room.set_editor_property('room_minimum',u.Vector(*geometry['room_min']))
    room.set_editor_property('room_maximum',u.Vector(*geometry['room_max']))
    if num==plan.get('herbalist',{}).get('house'):
        set_herbalist_daylight(room)
    elif model=='SL_Blacksmith_LoftR3':
        apply_daylight(room, SHOP_DAYLIGHT['01'])
    elif num in RESIDENTIAL_PLOTS:
        apply_daylight(room, RESIDENTIAL_DAYLIGHT)
    else:
        ruined='RuinedHouse' in model
        room.set_editor_property('additional_dark_adaptation_stops',1.0 if ruined else 2.25)
        room.set_editor_property('exposure_compensation',.2 if ruined else .6)
        room.set_editor_property('entrance_transition_cm',120.)

from village_yard_dressing import build_yard_dressing
yard_dressing = build_yard_dressing(world,source,plan,kit)
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageWindmill'))
from install_windmill import install_windmill
install_windmill(actors,plan,kit)
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageBakery'))
from install_bakery import install_bakery
install_bakery(actors,plan,kit)
sys.path.insert(0, str(root/'Tools/WorldGeneration/VillageGunshop'))
from install_gunshop import install_gunshop
install_gunshop(actors,plan,kit)
from village_chimney import install_village_hearths
install_village_hearths(actors,plan,kit)
sys.path.insert(0,str(root/'Tools/WorldGeneration/VillageStable'))
from install_stable import install_stable
install_stable(actors)
if plan.get('tavern',{}).get('inn'):
    from fit_inn import clear_inn_scatter
    village_actors=actors.get_all_level_actors()
    inn=next(a for a in village_actors if 'VillageTavern.Site' in map(str,a.tags))
    clear_inn_scatter(village_actors,inn)
    if plan['tavern']['inn'].get('hall_road'):
        from save_hall_refit import clear_verge
        clear_verge(village_actors,plan['tavern']['inn']['hall_road'])
if not u.EditorLoadingAndSavingUtils.save_map(world,level):
    raise RuntimeError('Could not save '+level)
u.log('VILLAGE_SAVED %s wall_groups=%d wall_instances=%d' % (level,len(wall_bounds),len(wall_footprints)))
u.log('VILLAGE_GROUND_DRESSING_SAVED '+json.dumps(dict(detail_counts)))
u.log('VILLAGE_YARDS_SAVED '+json.dumps(yard_dressing))
(source/os.environ.get('VILLAGE_RECEIPT_DIRECTORY','DemoRevision20261114')/'author-saved.json').write_text(json.dumps(dict(level=level,house_scale=house_scale,
    houses=len(vision_rooms),interior_vision_rooms=len(vision_rooms),window_fill_lights=0,
    wall_instances=len(wall_footprints),wall_reference=plan.get('wall_reference'),
    ground_dressing=dict(detail_counts),interiors=interior_receipt,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
