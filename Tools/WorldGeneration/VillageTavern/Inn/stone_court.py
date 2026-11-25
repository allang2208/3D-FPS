"""Extend the repaired taproom rear wall into a service range and fit its new horse yard."""
import unreal as u
from fit_inn import REPAIRED, RUIN, COMMON, PKG, STABLE, MILL, TAVERN, KIT, require, group

TAG='VillageTavern.StoneCourt'
def install(site):
    if TAG in map(str,site.tags):return
    site.modify()
    frame=site.get_actor_transform()
    roof=None
    for c in list(site.get_components_by_class(u.InstancedStaticMeshComponent)):
        m=c.static_mesh
        if not m:continue
        name=m.get_name()
        tags=list(map(str,c.component_tags))
        if name.startswith('SM_Inn') and not name.endswith('_StoneCourt'):
            replacement=require(PKG+name[6:]+'_StoneCourt')
            c.modify();c.set_static_mesh(replacement)
            continue
        if REPAIRED in tags and (m.get_path_name().startswith(STABLE) or
                name in ('SM_MillHayB','SM_MillChaff')):
            c.modify();c.clear_instances()
            continue
        if name=='SM_Roof_00A' and REPAIRED in tags:
            roof=m
        if not (name.startswith(('SM_H_OldWall','SM_Window_','SM_H_WallCorner')) and
                'Triangle' not in name and (REPAIRED in tags or COMMON in tags)):continue
        retained=[];removed=[]
        for i in range(c.get_instance_count()):
            t=u.MathLibrary.make_relative_transform(c.get_instance_transform(i,True),frame)
            (removed if 366<t.translation.y<495 and t.translation.z<320 else retained).append(t)
        if not removed:continue
        c.modify();c.clear_instances();c.add_instances(retained,False,False,False)
        if COMMON in tags:
            materials=[c.get_material(i) for i in range(c.get_num_materials())]
            group(site,m,removed,[RUIN if k==COMMON else k for k in tags],'VillageTavern.NoCollision' not in tags,materials)
    if not roof:raise RuntimeError('Missing repaired roof tile')
    def add(mesh,poses,solid=True,dist=0):
        return group(site,mesh,poses,[REPAIRED,'HillsStaticSupport' if solid else 'VillageTavern.NoCollision'],solid,distance=dist)
    # Reuse the south-facing tile courses, flattened in pitch to clear the private rear gallery.
    add(roof,[u.Transform(location=(x,626,920),scale=(sx,1.43,.32)) for x,sx in
        [(-496,1.56),(-40,1.50),(415,1.56)]])
    def fitted(path,items,solid=True,dist=4800):
        m=require(path);bb=m.get_bounding_box();mid=(bb.max+bb.min)*.5;poses=[]
        for x,y,z,sx,sy,sz,yaw in items:
            f=u.Transform(location=(x,y,z),rotation=u.Rotator(yaw=yaw),scale=u.Vector(sx,sy,sz)/(bb.max-bb.min))
            poses.append(u.MathLibrary.compose_transforms(u.Transform(location=(-mid.x,-mid.y,-bb.min.z)),f))
        add(m,poses,solid,dist)
    # Three tie spaces on a west-side rail. The feed faces the horses; the public approach stays east.
    fitted(STABLE+'A08',[(-511,-831,-3,328,29,112,0),(-174,-831,-3,328,29,112,0)])
    stations=[-557,-350,-143]
    fitted(STABLE+'HayCrib',[(x,-787,-3,128,52,83,0) for x in stations])
    fitted(MILL+'HayB',[(x,-787,52,103,35,22,3-i*2) for i,x in enumerate(stations)],False,3600)
    fitted(MILL+'Chaff',[(x,-919,-2,143,176,2,9-i*10) for i,x in enumerate(stations)],False,3000)
    # A second dining table in the corner of the rear service range doubles as a preparation bench.
    fitted(KIT+'OakTable',[(377,708,-2,192,84,81,0)])
    fitted(TAVERN+'Service/SM_TavernPitcher',[(419,715,79,19,19,26,12)],False,2800)
    fitted(KIT+'OakShelf',[(548,563,-2,159,49,168,90)])
    # Keep the positions of the original windows/doors on all upper modules.
    site.tags=[*site.tags,TAG]
