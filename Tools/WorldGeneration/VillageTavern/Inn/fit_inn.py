"""Refit the saved House 02 without replacing its repaired masonry, sign or restaurant."""
from collections import defaultdict
from pathlib import Path
import math
import sys
import unreal as u

ROOT=Path(__file__).resolve().parents[4]
sys.path[:0]=[str(ROOT/'SourceAssets/HillsVillageTavern/Inn'),
              str(ROOT/'Tools/WorldGeneration/AbandonedVillage'),str(ROOT/'Tools/WorldGeneration/VillageBlacksmith')]
from inn_geometry import DOORS, GUEST, OWNER
from shop_pendants import component,hang,Pendant
from author_shop import KIT,require

TAG='VillageTavern.ThreeStoreyInn'
PKG='/Game/WorldGeneration/VillageTavern/Inn/SM_Inn'
STABLE='/Game/WorldGeneration/TemperateHills/VillageStable/Meshes/SM_Stable_'
MILL='/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Meshes/SM_Mill'
TAVERN='/Game/WorldGeneration/VillageTavern/'
CARP='/Game/WorldGeneration/TemperateHills/VillageCarpenter/InteriorR1/SM_Carpenter'
RUIN='VillageTavern.Ruined'
REPAIRED='VillageTavern.Repaired'
COMMON='VillageTavern.Common'

def state(c,mode,solid):
    c.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
    visible=mode!=REPAIRED
    c.set_visibility(visible)
    c.set_hidden_in_game(not visible)
    c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if visible and solid else u.CollisionEnabled.NO_COLLISION)

def group(site,mesh,poses,tags,solid,materials=(),distance=0):
    obj=component(site,u.HierarchicalInstancedStaticMeshComponent)
    obj.set_mobility(u.ComponentMobility.STATIC)
    obj.set_relative_transform(u.Transform(),False,True)
    obj.set_static_mesh(mesh)
    for index,mat in enumerate(materials):
        if mat:obj.set_material(index,mat)
    obj.component_tags=tags
    obj.set_editor_property('receives_decals',False)
    obj.add_instances(poses,False,False,False)
    if distance:obj.set_cull_distances(distance-400,distance)
    state(obj,REPAIRED if REPAIRED in tags else '',solid)
    return obj

def raised(t,dz):
    return u.Transform(location=t.translation+u.Vector(0,0,dz),rotation=t.rotation.rotator(),scale=t.scale3d)

def extend(t,name,extra):
    # Only stretch the outside west bay. East hearth, threshold and furniture retain their datum.
    x=t.translation.x
    if x>=-219.6:return t
    gable=abs(x+644)<35 or (name.startswith('SM_Window_') and abs(t.translation.y)<340)
    dx=-extra if gable else -extra*min(1.15,(-219.6-x)/439.2)
    width=t.scale3d
    if not gable and not name.startswith('SM_Window_'):
        a=math.radians(t.rotation.rotator().yaw)
        width=u.Vector(width.x*(1+extra/439.2*math.cos(a)**2),
                       width.y*(1+extra/439.2*math.sin(a)**2),width.z)
    return u.Transform(location=t.translation+u.Vector(dx,0,0),rotation=t.rotation.rotator(),scale=width)

def refit_roof(site,extra):
    frame=site.get_actor_transform()
    for c in list(site.get_components_by_class(u.StaticMeshComponent)):
        m=c.static_mesh
        if not m:continue
        tags=list(map(str,c.component_tags)); n=m.get_name()
        if not any(k in tags for k in (RUIN,REPAIRED,COMMON)):continue
        if any('CounterPendant' in k for k in tags):continue
        ins=isinstance(c,u.InstancedStaticMeshComponent)
        ts=([u.MathLibrary.make_relative_transform(c.get_instance_transform(i,True),frame) for i in range(c.get_instance_count())]
            if ins else [u.MathLibrary.make_relative_transform(c.get_world_transform(),frame)])
        ts=[extend(t,n,extra) for t in ts]
        solid='VillageTavern.NoCollision' not in tags
        upper=('Roof' in n or 'Triangle' in n or 'Chimney' in n or n=='Cube' or
               (n=='SM_HW_Plank_01A' and ts and min(t.translation.z for t in ts)>200))
        c.modify()
        if upper and COMMON in tags:
            c.component_tags=[RUIN if k==COMMON else k for k in tags]
            copytags=[REPAIRED if k==COMMON else k for k in tags if '.Chimney.' not in k]
            mats=[c.get_material(i) for i in range(c.get_num_materials())]
            group(site,m,[raised(t,OWNER) for t in ts],copytags,solid,mats)
            if n=='SM_HW_Plank_01A':
                ties=[t for t in ts if abs(t.translation.z-316)<2]
                if ties:group(site,m,ties,copytags,solid,mats)
        elif upper and REPAIRED in tags:
            ts=[raised(t,OWNER) for t in ts]
        if ins:
            c.clear_instances()
            c.add_instances(ts,False,False,False)
        else:c.set_world_transform(u.MathLibrary.compose_transforms(ts[0],frame),False,True)
    for c in site.get_components_by_class(u.NiagaraComponent):
        if 'VillageShop.FlueSmoke' in map(str,c.component_tags):
            c.modify();c.set_relative_location(u.Vector(581,79,753.9+OWNER),False,True)

def furniture(site,original_hitch):
    groups=defaultdict(list); meshes={}
    def fitted(path,x,y,z,size,yaw=0,solid=True,dist=5200):
        if path not in meshes:meshes[path]=require(path)
        bounds=meshes[path].get_bounding_box()
        mid=(bounds.min+bounds.max)*.5
        frame=u.Transform(location=(x,y,z),rotation=u.Rotator(yaw=yaw),scale=u.Vector(*size)/(bounds.max-bounds.min))
        groups[path,solid,dist].append(u.MathLibrary.compose_transforms(u.Transform(location=(-mid.x,-mid.y,-bounds.min.z)),frame))
    bed=KIT+'TimberBed';table=KIT+'OakTable';stool=KIT+'OakStool';shelf=KIT+'OakShelf'
    chest=CARP+'JoinersChest';lid=CARP+'JoinersChestLid'
    def trunk(x,y,z,yaw):
        fitted(chest,x,y,z,(91,49,42),yaw)
        fitted(lid,x,y,z+41,(93,51,6),yaw)
    # Bed lengths run along local Y. Door sweeps are kept in the central third of each bay.
    for i,(x,y,hand) in enumerate([(-251,-271,-1),(504,-277,1),(-256,278,1),(496,280,-1)]):
        fitted(bed,x,y,GUEST,(113,209,92),180 if y>0 else 0)
        tx=(x+228 if x<0 else x-265)
        fitted(table,tx,y+31*hand,GUEST,(82,57,70),i*2)
        fitted(stool,tx+33,y-40*hand,GUEST,(34,32,42),8+i*9)
        fitted(TAVERN+'Service/SM_TavernPitcher',tx-7,y+31*hand,GUEST+70,(18,16,24),i*52,False,3000)
        trunk(x+136*(1 if x<0 else -1),y+(82 if y>0 else -90),GUEST,0)
    fitted(bed,-249,-278,OWNER,(126,210,92),0)
    trunk(-35,-351,OWNER,0)
    fitted(table,297,319,OWNER,(155,72,78),0)
    fitted(stool,298,232,OWNER,(41,37,45),12)
    fitted(shelf,554,290,OWNER,(112,44,170),90)
    fitted(table,316,-222,OWNER,(145,78,77),-6)
    fitted(stool,324,-132,OWNER,(40,37,45),-12)
    fitted(TAVERN+'Service/SM_TavernPitcher',325,-210,OWNER+77,(19,17,25),24,False,3000)
    fitted(CARP+'WashBarrel',-207,322,OWNER,(65,65,72),-9)
    # Horse heads face the rail; hay is below the mouth of each crib. The approach is through the wall gap.
    if original_hitch:
        fitted(STABLE+'A08',-452,-518,-4,(376,29,112),0)
        for x,angle in [(-547,-3),(-354,2)]:
            fitted(STABLE+'HayCrib',x,-481,-4,(117,49,80),angle)
            fitted(MILL+'HayB',x,-482,50,(98,33,22),angle+3,False,3600)
            fitted(MILL+'Chaff',x,-580,-3.6,(115,165,2.0),angle+11,False,2600)
    for (path,solid,dist),ts in groups.items():
        group(site,meshes[path],ts,[REPAIRED,'HillsStaticSupport' if solid else 'VillageTavern.NoCollision'],solid,distance=dist)
    return sum(len(p) for p in groups.values())

def clear_inn_scatter(actors,site):
    """Remove only small inherited verge dressing inside the floor and tether bays."""
    removed=0
    frame=site.get_actor_transform()
    for a in actors:
        if a==site or not a.get_actor_label().startswith('Village_'):continue
        for c in a.get_components_by_class(u.InstancedStaticMeshComponent):
            m=c.static_mesh
            if not m or not m.get_name().lower().startswith(('sm_grass','flower_','sm_planttype','sm_stone_','sm_softwildgrass','sm_foresttwig')):continue
            box=m.get_bounding_box()
            court='VillageTavern.StoneCourt' in map(str,site.tags)
            touched=False
            for i in reversed(range(c.get_instance_count())):
                t=c.get_instance_transform(i,True)
                p=u.MathLibrary.inverse_transform_location(frame,u.MathLibrary.transform_location(t,(box.min+box.max)*.5))
                if p.z<115 and ((-758<p.x<677 and -455<p.y<(858 if court else 438)) or
                        ((-731<p.x<180 and -1130<p.y<-435) if court else (-654<p.x<-252 and -740<p.y<-439))):
                    if not touched:
                        a.modify();c.modify();touched=True
                    if not c.remove_instance(i):raise RuntimeError('Cannot clear verge from inn')
                    removed+=1
    return removed

def upgrade(site,plan):
    if TAG in map(str,site.tags):return
    site.modify()
    refit_roof(site,plan['tavern']['inn']['west_extension_m']*100)
    suffix='_StoneCourt' if plan['tavern']['inn'].get('rear_range_m') else ''
    for name in ('Facade','TimberFrame','Floors','Stairs','Partitions','Rails','FlueShaft'):
        group(site,require(PKG+name+suffix),[u.Transform()],[REPAIRED,'HillsStaticSupport'],True)
    count=furniture(site,original_hitch=not suffix)
    for y,x,z,yaw in DOORS:
        sock=component(site,u.StaticMeshComponent)
        sock.set_mobility(u.ComponentMobility.STATIC)
        sock.set_relative_transform(u.Transform(location=(x,y,z+.9),rotation=u.Rotator(yaw=yaw)),False,True)
        sock.set_static_mesh(require(PKG+'RoomDoor'+suffix));sock.component_tags=['VillageTavern.RoomDoor','VillageTavern.NoCollision']
        sock.set_collision_profile_name('NoCollision');sock.set_visibility(False);sock.set_hidden_in_game(True)
    # Corridor lamp below the third floor; upstairs lamp hangs from an existing roof tie beam.
    for label,x,y,top,bottom in [('Guest',10,0,OWNER-13,571),('Owner',0,0,OWNER+304.5,883)]:
        name='VillageTavern.'+label+'Pendant'
        hang(site,site.get_actor_transform(),Pendant(name,REPAIRED,(x,y,top),bottom,29,12))
        light=next(c for c in site.get_components_by_class(u.PointLightComponent) if name in map(str,c.component_tags))
        light.component_tags=[*light.component_tags,'VillageTavern.InnLight']
        light.set_cast_shadows(False)
    site.tags=[*site.tags,TAG]
    return dict(furnishings=count,room_doors=len(DOORS),guest_floor=GUEST,owner_floor=OWNER)
