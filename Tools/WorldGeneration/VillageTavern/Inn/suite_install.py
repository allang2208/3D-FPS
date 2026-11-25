"""Migrate HallRoadR3 in place, preserving stairs, runtime dining, exterior masonry and guest doors."""
from collections import defaultdict
from hall_refit import (u,require,group,REPAIRED,PKG,OWNER,BED,TABLE,STOOL,SHELF,CHEST,LID,
                        DRAWERS,BOOK,LINEN,WARE,CARP)
from suite_geometry import SUITE_DOOR,SUITE_Y

TAG='VillageTavern.JoineryR4'
def asset(name):return PKG+name+'_JoineryR4'

def furniture(site):
    batches=defaultdict(list);meshes={}
    def put(path,x,y,z,size,yaw=0,solid=True):
        if path not in meshes:meshes[path]=require(path)
        b=meshes[path].get_bounding_box();mid=(b.min+b.max)*.5
        f=u.Transform(location=(x,y,OWNER+z),rotation=u.Rotator(yaw=yaw),scale=u.Vector(*size)/(b.max-b.min))
        batches[path,solid].append(u.MathLibrary.compose_transforms(u.Transform(location=(-mid.x,-mid.y,-b.min.z)),f))
    def chest(x,y,deg):
        put(CHEST,x,y,0,(98,48,44),deg);put(LID,x,y,43,(100,50,6),deg)
    def book(x,y,z,yaw=0):put(BOOK,x,y,z,(24,17,4.6),yaw,False)
    def towel(x,y,z,yaw=0):put(LINEN,x,y,z,(32,25,7),yaw,False)
    # Private chamber. The door opens into a clear 1.5 m turning space.
    put(BED,490,652,0,(136,212,94),180)
    chest(485,478,-2);towel(484,479,49,1)
    put(asset('Cupboard'),149,693,0,(124,51,171),90)
    put(TABLE,145,459,0,(94,47,80),90)
    put(asset('Mirror'),100.2,459,102,(46,4.6,66),90,False)
    put(WARE+'Pitcher',144,484,80,(16,16,24),18,False)
    put(WARE+'Dish',146,454,80,(23,20,4),12,False)
    towel(142,433,80,-7)
    put(STOOL,215,461,0,(36,33,42),5)
    # Hall. A low settle faces the table, tall furniture sits on solid wall bays.
    put(asset('Settle'),420,-69,0,(142,49,104),-90)
    put(TABLE,260,-67,0,(154,74,77),90)
    for x,y,deg in [(172,-100,-4),(172,-33,8)]:put(STOOL,x,y,0,(36,35,43),deg)
    for x,y in ((252,-102),(270,-38)):put(WARE+'Dish',x,y,77,(23,21,4),13,False)
    put(WARE+'Pitcher',258,-70,77,(19,15,24),-12,False)
    put(WARE+'Tankard',277,-110,77,(11,11,14),30,False)
    put(DRAWERS,379,-369,0,(130,45,84),180)
    put(WARE+'Dish',402,-365,84,(27,22,4),2,False)
    # Keep the west landing and its direct approach unobstructed.
    put(TABLE,-175,-352,0,(143,62,76),0);put(STOOL,-163,-269,0,(38,35,44),-12)
    book(-188,-347,76,12);put(WARE+'Tankard',-127,-355,76,(11,10,14),11,False)
    put(asset('Cupboard'),-314,778,0,(134,48,158),0)
    put(SHELF,-30,771,0,(111,44,148),0)
    chest(-202,615,4);book(-201,614,49,6)
    for (path,solid),poses in batches.items():
        group(site,meshes[path],poses,[REPAIRED,'HillsStaticSupport' if solid else 'VillageTavern.NoCollision','VillageTavern.SuiteFurniture'],
              solid,distance=5300 if solid else 3300)
    return sum(map(len,batches.values()))

def install(site):
    if TAG in map(str,site.tags):return {}
    if 'VillageTavern.HallRoadR3' not in map(str,site.tags):raise RuntimeError('Expected fitted three-storey inn')
    site.modify();frame=site.get_actor_transform()
    swap={PKG+'TimberFrame_HallRoadR3':'TimberFrame',
          PKG+'Partitions_HallRoadR3':'Partitions',PKG+'KitchenPass_HallRoadR3':'KitchenPass',
          '/Game/UnrealNormandy/StaticMeshes/SM_Window_Frame_00A':'WindowFrame'}
    changed=defaultdict(int);removed=0
    for c in site.get_components_by_class(u.InstancedStaticMeshComponent):
        m=c.static_mesh
        if not m:continue
        path=m.get_path_name().split('.')[0];n=c.get_instance_count()
        if path in swap:
            c.modify();c.set_editor_property('override_materials',[]);c.set_static_mesh(require(asset(swap[path])))
            changed[swap[path]]+=n
        elif 'VillageTavern.RefitFurniture' in map(str,c.component_tags):
            b=m.get_bounding_box();mid=(b.min+b.max)*.5
            for i in reversed(range(n)):
                pos=u.MathLibrary.inverse_transform_location(frame,u.MathLibrary.transform_location(c.get_instance_transform(i,True),mid))
                if pos.z>=OWNER:
                    c.modify()
                    if not c.remove_instance(i):raise RuntimeError(m.get_name())
                    removed+=1
    if set(changed)!=set(swap.values()):raise RuntimeError(str(changed))
    doors=[c for c in site.get_components_by_class(u.StaticMeshComponent) if 'VillageTavern.RoomDoor' in map(str,c.component_tags) and abs(c.relative_location.z-OWNER-.9)<2]
    door,=doors;door.modify();door.set_relative_transform(u.Transform(location=(SUITE_DOOR,SUITE_Y,OWNER+.9),rotation=u.Rotator(yaw=90)),False,True)
    placed=furniture(site);site.tags=[*site.tags,TAG]
    return dict(swapped=dict(changed),removed_owner_furnishings=removed,owner_furniture=placed,bedroom_door=[SUITE_DOOR,SUITE_Y,OWNER+.9])
