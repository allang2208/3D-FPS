"""HallRoadR3 furnishings; local centimetres measured from finished floors."""
from collections import defaultdict
import math
from fit_inn import (u,KIT,CARP,TAVERN,PKG,REPAIRED,group,require,hang,Pendant,DOORS,GUEST,OWNER)
from hall_plan import sockets

TAG='VillageTavern.HallRoadR3'
QUX='/Game/Dungeons/TunnelStyleLiving20261112/Quixel/'
LINEN=QUX+'FoldedTowel_72036b54/Meshes/SM_FoldedTowel_72036b54'
BOOK=QUX+'Book_634f4e59/Meshes/SM_Book_634f4e59'
DRAWERS='/Game/WorldGeneration/TemperateHills/VillageGunshop/Fixtures/SM_Gunshop_MerchantDrawers'
WARE=TAVERN+'StonewareDetail/SM_Tavern'
BED,TABLE,STOOL,SHELF=[KIT+s for s in ('TimberBed','OakTable','OakStool','OakShelf')]
CHEST,LID=CARP+'JoinersChest',CARP+'JoinersChestLid'

def furnish(site):
    batches=defaultdict(list); meshes={}
    def put(path,x,y,z,size,yaw=0,solid=True):
        if path not in meshes:meshes[path]=require(path)
        b=meshes[path].get_bounding_box();mid=(b.min+b.max)*.5
        pose=u.Transform(location=(x,y,z),rotation=u.Rotator(yaw=yaw),scale=u.Vector(*size)/(b.max-b.min))
        batches[path,solid].append(u.MathLibrary.compose_transforms(u.Transform(location=(-mid.x,-mid.y,-b.min.z)),pose))
    def trunk(x,y,z,yaw):
        put(CHEST,x,y,z,(89,49,43),yaw)
        put(LID,x,y,z+42,(91,51,6),yaw)
    def mug(x,y,z,a):put(WARE+'Tankard',x,y,z,(12,10,15),a,False)
    def dish(x,y,z,a):put(WARE+'Dish',x,y,z,(23,21,4),a,False)
    def towel(x,y,z,a):put(LINEN,x,y,z,(30,23,7),a,False)
    def book(x,y,z,a):put(BOOK,x,y,z,(23,17,5),a,False)
    for i,(bx,by,tx,ty,cx,cy) in enumerate(((-251,-270,12,-323,-241,1),(494,-266,228,-308,528,-76),
            (-242,655,72,710,-225,432),(509,668,296,716,522,438))):
        z=GUEST
        put(BED,bx,by,z,(112,208,89),180 if by>0 else 0)
        put(TABLE,tx,ty,z,(88,55,70),0)
        put(STOOL,tx+(-8 if i%2 else 15),ty+(-74 if ty>0 else 76),z,(35,33,43),13*i+4)
        trunk(cx,cy,z,i*2-3)
        if i in (0,2):
            put(WARE+'Pitcher',tx-22,ty-2,z+70,(18,15,25),18+i*16,False)
            dish(tx+17,ty+3,z+70,12)
        else:
            mug(tx+22,ty+2,z+70,13)
            (book if i==1 else towel)(tx-13,ty-1,z+70,-8)
        if i==2:towel(cx-14,cy,z+48,8)
    z=OWNER
    put(BED,-227,661,z,(130,214,93),180)
    trunk(-212,461,z,4)
    put(DRAWERS,64,744,z,(123,46,91),0)
    towel(72,744,z+91,-4)
    put(TABLE,-174,-300,z,(141,67,77),2)
    put(STOOL,-163,-217,z,(37,36,45),-13)
    book(-194,-300,z+77,9);mug(-130,-307,z+77,42)
    put(TABLE,306,152,z,(152,75,78),-3)
    for x,y,a in ((291,66,9),(321,242,-7)):put(STOOL,x,y,z,(40,38,45),a)
    dish(279,145,z+78,10);dish(329,164,z+78,-7);mug(328,137,z+78,22)
    put(WARE+'Pitcher',263,167,z+78,(18,16,25),-12,False)
    put(DRAWERS,439,-350,z,(142,48,95),180)
    put(SHELF,237,734,z,(111,42,151),0)
    put(TABLE,522,680,z,(133,61,77),0)
    put(CARP+'WashBarrel',408,662,z,(58,58,65),8)
    put(CARP+'WashWater',408,662,z+60,(51,51,2),8,False)
    dish(499,681,z+77,-4);towel(550,685,z+77,6)
    put(WARE+'Pitcher',520,661,z+77,(17,16,23),48,False)
    for (path,solid),poses in batches.items():
        group(site,meshes[path],poses,[REPAIRED,'HillsStaticSupport' if solid else 'VillageTavern.NoCollision','VillageTavern.RefitFurniture'],solid,distance=5300 if solid else 3000)
    return sum(map(len,batches.values()))

def install(site):
    if TAG in map(str,site.tags):return {}
    if 'VillageTavern.StoneCourt' not in map(str,site.tags):raise RuntimeError('Expected R2 tavern')
    site.modify();frame=site.get_actor_transform()
    old={BED,TABLE,STOOL,SHELF,CHEST,LID,CARP+'WashBarrel',TAVERN+'Service/SM_TavernPitcher'}
    ground={TABLE:(377,708,38),SHELF:(548,563,82),TAVERN+'Service/SM_TavernPitcher':(419,715,92)}
    for c in site.get_components_by_class(u.InstancedStaticMeshComponent):
        m=c.static_mesh
        if not m or REPAIRED not in map(str,c.component_tags):continue
        path=m.get_path_name().split('.')[0]
        if path in (PKG+'Partitions_StoneCourt',PKG+'TimberFrame_StoneCourt'):
            c.modify();c.set_static_mesh(require(path.replace('StoneCourt','HallRoadR3')))
        if path not in old:continue
        b=m.get_bounding_box();mid=(b.min+b.max)*.5
        for i in reversed(range(c.get_instance_count())):
            pos=u.MathLibrary.inverse_transform_location(frame,u.MathLibrary.transform_location(c.get_instance_transform(i,True),mid))
            if pos.z>=GUEST or (path in ground and math.dist((pos.x,pos.y,pos.z),ground[path])<4):
                c.modify()
                if not c.remove_instance(i):raise RuntimeError(path)
    group(site,require(PKG+'KitchenPass_HallRoadR3'),[u.Transform()],[REPAIRED,'HillsStaticSupport'],True)
    doors=[c for c in site.get_components_by_class(u.StaticMeshComponent) if 'VillageTavern.RoomDoor' in map(str,c.component_tags)]
    for old,new in zip(DOORS,sockets(GUEST,OWNER)):
        y,x,z,yaw=old
        c,=[c for c in doors if (c.relative_location-u.Vector(x,y,z+.9)).length()<2]
        y,x,z,yaw=new;c.modify();c.set_relative_transform(u.Transform(location=(x,y,z+.9),rotation=u.Rotator(yaw=yaw)),False,True)
    for name,at,bottom,size,yaw in [('Counter',(0,478,312.5),249,32,-14),('Guest',(10,200,629),571,29,12)]:
        tag='VillageTavern.'+name+'Pendant'
        hang(site,frame,Pendant(tag,REPAIRED,at,bottom,size,yaw))
        if name=='Guest':
            light,=[c for c in site.get_components_by_class(u.PointLightComponent) if tag in map(str,c.component_tags)]
            light.component_tags=[*light.component_tags,'VillageTavern.InnLight'];light.set_cast_shadows(False)
    pieces=furnish(site)
    site.tags=[*site.tags,TAG]
    return dict(upstairs_instances=pieces,room_doors=len(doors))
