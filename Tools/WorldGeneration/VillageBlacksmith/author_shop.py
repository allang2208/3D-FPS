"""Assemble first-house repair states and furnish village homes in their local floor frame."""
import math,json
from collections import defaultdict
from pathlib import Path
import unreal as u

KIT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Meshes/SM_Village'
CRATE='/Game/UndergroundTunnel/Meshes/Props/SM_WoodCrate01a'
BARREL='/Game/Props/CastingStation20260926/SM_CoolingBarrel'

def require(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing village furnishing '+path)
    return obj

def pose(house,x,y,z=0,yaw=0,scale=1):
    flat=u.Transform(location=[house[3]*100,house[4]*100,4],rotation=u.Rotator(yaw=house[5]))
    local=u.Transform(location=[x,y,z],rotation=u.Rotator(yaw=yaw),scale=[scale]*3)
    return u.MathLibrary.compose_transforms(local,flat)

def standing(house,path,x,y,floor=0,yaw=0,scale=1):
    """Asset pivots vary; place the actual base on the floor, with XY bounds centred."""
    mesh=require(path);b=mesh.get_bounding_box()
    a=math.radians(yaw);cx=(b.min.x+b.max.x)*.5*scale;cy=(b.min.y+b.max.y)*.5*scale
    return pose(house,x-cx*math.cos(a)+cy*math.sin(a),y-cx*math.sin(a)-cy*math.cos(a),
                floor-b.min.z*scale,yaw,scale)

def shell_transform(part,base):
    pitch,yaw,roll=part['rot']
    if 'SM_Window_Shutter_00A' in part['mesh']:yaw+=55
    elif 'SM_Window_Shutter_01A' in part['mesh']:yaw-=55
    t=u.Transform(location=part['pos'],rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=part['scale'])
    return u.MathLibrary.compose_transforms(t,base)

def build_shop(house,pieces,base,geometry):
    if house[2]=='SL_Blacksmith_LoftR3':
        from LoftR3.assemble import build_shop as build_loft
        from forge_weapon_display import install_forge_display
        report=build_loft(house,pieces,base,geometry)
        report["weapon_display"]=install_forge_display(house)
        return report
    return _build_shop_legacy(house,pieces,base,geometry)


def _build_shop_legacy(house,pieces,base,geometry):
    actors=u.get_editor_subsystem(u.EditorActorSubsystem)
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem);handles=u.SubobjectDataBlueprintFunctionLibrary
    groups=defaultdict(list)
    def add(state,path,t,mats=(),profile='BlockAll'):
        groups[(state,path,tuple(mats),profile)].append(t)
    for p in pieces:
        if p['mesh'].endswith('.SM_Door_00A'):continue
        broken=any(s in p['mesh'] for s in ('_Piece','Chunk','SM_Brick'))
        add('Ruined' if broken else 'Common',p['mesh'],shell_transform(p,base),p['materials'],p['profile'])
    donor=next(p for p in pieces if p['mesh'].endswith('.SM_H_OldWall_00A'))
    # The west upper rear bay already survives; fill only the four missing wall bays.
    for pos,yaw in [([-288.5354,-150.,-297.4087],-90),([-288.5354,150.,-297.4087],-90),
                    ([-288.5354,-150.,2.5913],-90),([-148.5354,-290.,2.5913],0)]:
        repaired=dict(donor,pos=pos,rot=[0,yaw,0],scale=[1,1,1])
        add('Repaired',repaired['mesh'],shell_transform(repaired,base),repaired['materials'])
    # Physical furnishings use their real dimensions, independent of the 1.2x house kit.
    for path,x,y,z,yaw,scale in [
        (KIT+'HearthPad',0,144,0,0,1),
        (KIT+'OakShelf',277,135,0,90,1),
        (KIT+'OakTable',230,-220,0,90,.85),
        (KIT+'OakStool',140,-220,0,12,1),
        (CRATE,-250,280,0,-4,.58),
        (BARREL,280,-310,0,0,1)]:
        add('Common',path,standing(house,path,x,y,z,yaw,scale))
    for state,path,x,y,z,yaw,scale in [
        ('Ruined',KIT+'AbandonedTimber',-230,-165,0,18,1),
        ('Ruined',KIT+'IronStock',265,270,0,35,1),
        ('Repaired',KIT+'IronStock',277,140,66,0,1),
        ('Repaired',KIT+'IronStock',277,140,118,0,.78),
        ('Repaired',CRATE,278,260,0,0,.5)]:
        add(state,path,standing(house,path,x,y,z,yaw,scale),profile='NoCollision' if 'IronStock' in path else 'BlockAll')
    door=next(p for p in pieces if 'OldWall_Door' in p['mesh'])
    doorx=door['pos'][0]*1.2
    add('Common',KIT+'BlacksmithSign',pose(house,doorx,-370,310),profile='NoCollision')
    add('Ruined',KIT+'ClosedPlaque',pose(house,doorx-98,-360,145),profile='NoCollision')

    state_actors={}
    for (state,path,mats,profile),transforms in groups.items():
        actor=state_actors.get(state)
        if not actor:
            actor=actors.spawn_actor_from_class(u.Actor,u.Vector())
            actor.set_actor_label('Village_Blacksmith_'+state)
            state_actors[state]=actor
        parent=sub.k2_gather_subobject_data_for_instance(actor)[0]
        handle,reason=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.HierarchicalInstancedStaticMeshComponent))
        comp=handles.get_associated_object(handles.get_data(handle))
        if not comp:raise RuntimeError(str(reason))
        comp.set_mobility(u.ComponentMobility.STATIC);comp.set_static_mesh(require(path))
        for index,material in enumerate(mats):
            if material:comp.set_material(index,require(material))
        comp.set_collision_profile_name(profile)
        comp.set_editor_property('receives_decals',False)
        tags=[] if state=='Common' else ['VillageShop.'+state]
        if profile=='NoCollision':tags.append('VillageShop.NoCollision')
        comp.set_editor_property('component_tags',tags)
        if state=='Repaired':
            comp.set_visibility(False);comp.set_hidden_in_game(True)
            comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        comp.add_instances(transforms,False,True,False)
    station=actors.spawn_actor_from_class(u.HillsBlacksmith,u.Vector())
    station.set_actor_label('Village_01_Blacksmith_Forge')
    station.set_actor_transform(pose(house,0,144,6),False,False)
    palette=require('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    definition=next(p for p in palette.get_editor_property('components') if str(p.get_editor_property('id'))=='casting_station')
    mesh=definition.get_editor_property('mesh')
    station.set_editor_property('station_mesh',mesh)
    body=station.get_component_by_class(u.StaticMeshComponent)
    body.set_static_mesh(mesh);body.set_editor_property('receives_decals',False)
    station.set_editor_property('shop_assemblies',list(state_actors.values()))
    station.set_editor_property('repair_area_center',u.Vector(0,-144,470))
    station.set_editor_property('repair_area_half_extent',u.Vector(380,380,500))
    return dict(actor_label=station.get_actor_label(),default='ruined',state_groups=len(groups),
                station_mesh=mesh.get_path_name(),operating_clearance_cm=160,door_sign='铁匠铺')

def furnish_home(house,pieces,geometry,scale,group):
    """Corner-based furnishing, leaving the doorway-to-centre path and room centre clear."""
    lo=[v*scale+34 for v in geometry['room_min'][:2]]
    hi=[v*scale-34 for v in geometry['room_max'][:2]]
    center=[(a+b)*.5 for a,b in zip(lo,hi)]
    door=next(p for p in pieces if 'OldWall_Door' in p['mesh'])
    entry=[door['pos'][i]*scale for i in (0,1)]
    occupied=[];placed=[]
    def dist_segment(p):
        dx,dy=center[0]-entry[0],center[1]-entry[1]
        t=min(1,max(0,((p[0]-entry[0])*dx+(p[1]-entry[1])*dy)/max(1,dx*dx+dy*dy)))
        return math.hypot(p[0]-entry[0]-t*dx,p[1]-entry[1]-t*dy)
    for path,scale_factor in [(KIT+'TimberBed',1),(KIT+'OakTable',1),(KIT+'OakShelf',.8),(CRATE,.55)]:
        b=require(path).get_bounding_box();span=b.max-b.min
        sx,sy=span.x*scale_factor,span.y*scale_factor
        candidates=[]
        for yaw in (0,90):
            hx,hy=(sx/2,sy/2) if yaw==0 else (sy/2,sx/2)
            for x in (lo[0]+hx,hi[0]-hx):
                for y in (lo[1]+hy,hi[1]-hy):candidates.append((x,y,hx,hy,yaw))
        candidates.sort(key=lambda c:math.dist(c[:2],entry),reverse=True)
        for x,y,hx,hy,yaw in candidates:
            if hx*2>hi[0]-lo[0] or hy*2>hi[1]-lo[1]:continue
            if dist_segment((x,y))<math.hypot(hx,hy)+70:continue
            if any(abs(x-px)<hx+phx+22 and abs(y-py)<hy+phy+22 for px,py,phx,phy in occupied):continue
            group(path,standing(house,path,x,y,0,yaw,scale_factor),profile='BlockAll')
            occupied.append((x,y,hx,hy));placed.append(path.rsplit('/',1)[-1]);break
    return dict(house=house[0],furnishings=placed,door_clearance_cm=140)
