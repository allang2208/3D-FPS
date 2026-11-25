"""Reuse the ground-floor taproom's Normandy modules at the existing upper-storey openings."""
from collections import namedtuple
from fit_inn import u, require, group, PKG, COMMON, REPAIRED
from inn_geometry import WEST, EAST, FRONT, BACK, GUEST, OWNER, upper_wall_runs
from hall_plan import GUEST_ROWS, WEST_ROOM
from suite_geometry import SUITE_X, SUITE_Y, SUITE_DOOR
from shop_house_modules import bays

TAG='VillageTavern.NativeDiningWallsR5'
KIT='/Game/UnrealNormandy/StaticMeshes/'
SOLID='SM_H_OldWall_00A'
WINDOW='SM_H_OldWall_Window_00A'
DOOR='SM_H_OldWall_Door_00A'
CORNER='SM_H_WallCorner_00A'
FACADE=PKG+'Facade_NativeDiningWallsR5'
ROOMS=PKG+'Partitions_NativeDiningWallsR5'
OLD_FACADE=PKG+'Facade_StoneCourt'
OLD_ROOMS=PKG+'Partitions_JoineryR4'
Bay=namedtuple('Bay','outside yaw line left right floor top opening slope')

def materials(comp):
    return [comp.get_material(i) for i in range(comp.get_num_materials())]

def source_walls(site):
    found={}
    for c in site.get_components_by_class(u.InstancedStaticMeshComponent):
        mesh=c.static_mesh
        if not mesh or not c.get_instance_count() or COMMON not in map(str,c.component_tags):continue
        name=mesh.get_name()
        if name in (SOLID,WINDOW,DOOR,CORNER) and mesh.get_path_name().split('.')[0]==KIT+name:
            found[name]=c
    if set(found)!={SOLID,WINDOW,DOOR,CORNER}:raise RuntimeError('Missing taproom source walls: '+str(found.keys()))
    return found

def wall_bays():
    def run(exterior,axis,line,start,end,floor,top,holes,slope=False):
        yaw=(180 if exterior and line==BACK else 0) if axis=='X' else (-90 if exterior and line==WEST else 90)
        sign=1 if yaw in (0,90) else -1
        for a,b,hole in bays(start,end,holes):
            left,right=sorted([sign*a,sign*b])
            if hole:
                x,y=sorted([sign*hole[0],sign*hole[1]])
                hole=(x,y,*hole[2:])
            yield Bay(exterior,yaw,line,left,right,floor,top,hole,slope)
    for axis,line,a,b,z,top,windows in upper_wall_runs():
        openings=[(x-54,x+54,z+92,z+218) for x in windows]
        slope=axis=='Y' and z==OWNER and a==423
        yield from run(True,axis,line,a,b,z,969 if slope else top,openings,slope)
    for y,yaw,split,doors in GUEST_ROWS:
        ends=[(WEST_ROOM,548),(614,EAST-23)] if yaw<0 else [(WEST_ROOM,EAST-23)]
        for a,b in ends:
            holes=[(x-55,x+55,GUEST,GUEST+221) for x in doors if a<x<b]
            yield from run(False,'X',y,a,b,GUEST,OWNER-13,holes)
        near,far=(FRONT+25,y-7) if yaw<0 else (y+7,BACK-25)
        for x in (WEST_ROOM,split):
            yield from run(False,'Y',x,near,far,GUEST,OWNER-13,[])
    yield from run(False,'X',SUITE_Y,SUITE_X,EAST-16,OWNER,872,[(SUITE_DOOR-55,SUITE_DOOR+55,OWNER,OWNER+221)])
    yield from run(False,'Y',SUITE_X,SUITE_Y+6.2,BACK-18,OWNER,872,[])

def frame(bay):
    # Native -Y is the dressed outer face. Set it slightly outboard of the window frame.
    offset=(6 if bay.line in (BACK,EAST) else -6) if bay.outside else 0
    line=bay.line+offset
    pos=(0,line,0) if bay.yaw in (0,180) else (line,0,0)
    return u.Transform(location=pos,rotation=u.Rotator(yaw=bay.yaw))

def depth_scale(bay):
    return 1.0 if bay.outside else .16

def whole_stones(bay):
    width=bay.right-bay.left
    if bay.opening or bay.slope or width<225:return []
    count=max(1,round(width/405.))
    step=width/count
    return [u.MathLibrary.compose_transforms(u.Transform(location=(bay.left+(i+.5)*step,0,(bay.floor+bay.top)*.5),
                scale=(step/300,depth_scale(bay),(bay.top-bay.floor)/300)),frame(bay)) for i in range(count)]

def install(site):
    if TAG in map(str,site.tags):return {}
    if 'VillageTavern.JoineryR4' not in map(str,site.tags):raise RuntimeError('Expected fitted suite and working inn doors')
    donors=source_walls(site)
    replacements={OLD_FACADE:require(FACADE),OLD_ROOMS:require(ROOMS)}
    components={c.static_mesh.get_path_name().split('.')[0]:c for c in site.get_components_by_class(u.InstancedStaticMeshComponent)
                if c.static_mesh and c.get_instance_count() and c.static_mesh.get_path_name().split('.')[0] in replacements}
    if set(components)!=set(replacements):raise RuntimeError('Missing fitted facade or partitions')
    site.modify()
    for path,comp in components.items():
        comp.modify()
        comp.set_editor_property('override_materials',[])
        comp.set_static_mesh(replacements[path])
    walls=list(wall_bays())
    counts={}
    for outside in (True,False):
        poses=[t for bay in walls if bay.outside==outside for t in whole_stones(bay)]
        if not poses:continue
        donor=donors[SOLID]
        if outside:
            # Batch with the ground floor's repaired stone wall in the distant proxy.
            candidates=[c for c in site.get_components_by_class(u.InstancedStaticMeshComponent)
                        if c.static_mesh==donor.static_mesh and REPAIRED in map(str,c.component_tags)
                        and c.get_instance_count() and materials(c)==materials(donor)]
            c,=candidates
            c.modify()
            owner=site.get_actor_transform()
            c.add_instances([u.MathLibrary.compose_transforms(t,owner) for t in poses],False,True,False)
        else:
            group(site,donor.static_mesh,poses,[REPAIRED,'VillageTavern.NoCollision','VillageTavern.NativeRoomWall'],False,materials(donor),distance=5800)
        counts['exterior' if outside else 'interior']=len(poses)
    corner=donors[CORNER]
    poses=[]
    for x,y,yaw in [(EAST,FRONT,-90),(WEST,FRONT,180),(EAST,BACK,0),(WEST,BACK,90)]:
        for lo,hi in [(GUEST,OWNER),(OWNER,872 if y==BACK else 958)]:
            poses.append(u.Transform(location=(x+(7 if x==WEST else -7),y+(-7 if y==BACK else 7),(hi+lo)/2),
                         rotation=u.Rotator(yaw=yaw),scale=(1.61,1.61,(hi-lo+3)/302.7)))
    group(site,corner.static_mesh,poses,[REPAIRED,'HillsStaticSupport'],True,materials(corner))
    counts['native_corners']=len(poses)
    site.tags=[*site.tags,TAG]
    return dict(whole_native_wall_instances=counts,windows=sum(1 for b in walls if b.outside and b.opening),
                room_doors=sum(1 for b in walls if not b.outside and b.opening))
