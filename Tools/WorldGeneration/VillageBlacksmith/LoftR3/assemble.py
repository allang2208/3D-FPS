"""Two-storey shop assembly; input pieces already carry the 25% footprint enlargement."""
from collections import defaultdict
import math
import unreal as u
from LoftR3.design import *

def move_ruined_timber(house):
    """Move the single stair-side HISM instance in the loaded village. Caller saves the map."""
    from author_shop import standing
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    path = FURNITURE + 'AbandonedTimber'
    previous = standing(house, path, -270, -80, 0, 18, 1)
    target = standing(house, path, *RUINED_TIMBER)
    found = []
    for actor in actors.get_all_level_actors():
        if actor.get_actor_label() != 'Village_Blacksmith_Ruined':
            continue
        for comp in actor.get_components_by_class(u.HierarchicalInstancedStaticMeshComponent):
            if 'VillageShop.Ruined' not in map(str, comp.component_tags):
                continue
            if not comp.static_mesh or comp.static_mesh.get_path_name().split('.')[0] != path:
                continue
            for index in range(comp.get_instance_count()):
                pos = comp.get_instance_transform(index, True).translation
                already_moved = (pos - target.translation).length() < 0.5
                if already_moved or (pos - previous.translation).length() < 0.5:
                    found.append((actor, comp, index, already_moved))
    if len(found) != 1:
        raise RuntimeError('Expected one blacksmith ruin timber at the stair or crate bay; found ' + str(len(found)))
    actor, comp, index, already_moved = found[0]
    if not already_moved:
        actor.modify()
        comp.modify()
        if not comp.update_instance_transform(index, target, True, True, True):
            raise RuntimeError('Could not move blacksmith ruined timber to the crate bay')
    return {'instance': index, 'center_cm': RUINED_TIMBER[:3], 'moved': not already_moved}

def build_shop(house,pieces,base,geometry):
    from author_shop import pose,standing,require
    actors=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    sub=u.get_engine_subsystem(u.SubobjectDataSubsystem);handles=u.SubobjectDataBlueprintFunctionLibrary
    groups=defaultdict(list);windows=[]
    def add(state,path,t,mats=(),profile='BlockAll',extra=()):groups[(state,path,tuple(mats),profile,tuple(extra))].append(t)
    def native(state,p):
        pitch,yaw,roll=p['rot']
        if state!='Repaired':
            if 'SM_Window_Shutter_00A' in p['mesh']:yaw+=55
            elif 'SM_Window_Shutter_01A' in p['mesh']:yaw-=55
        t=u.Transform(location=p['pos'],rotation=u.Rotator(pitch=pitch,yaw=yaw,roll=roll),scale=p['scale'])
        add(state,p['mesh'],u.MathLibrary.compose_transforms(t,base),p['materials'],p['profile'])
    detail='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/DetailR6'
    # Both states share the same open arcade, footprint and circulation; no legacy closed shell.
    for p in pieces:
        n=p['mesh'].split('.')[-1]
        if n=='SM_Door_00A':continue
        common=n.startswith(('SM_WoodenFloor_','SM_Roof')) or n=='SM_H_OldWall_Triangle_00A'
        if common:native('Common',p)
    solid=next(p for p in pieces if p['mesh'].split('.')[-1]=='SM_H_OldWall_00A')
    window=next(p for p in pieces if p['mesh'].split('.')[-1]=='SM_H_OldWall_Window_00A')
    original_scale=XY_FACTOR
    def wall(x,y,z,yaw,kind='solid',fitted=False,state='Common'):
        donor=window if kind=='window' else solid
        p=dict(donor,pos=[x*original_scale,y*original_scale,z],rot=[0,yaw,0])
        if fitted:p['mesh']='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Meshes/SM_SmithWindowWall_R7'
        native(state,p)
        if fitted:
            # Exact physical interface in final cm; independent hinges and material slots.
            angle=math.radians(yaw)
            # The actual jamb face is -15..-18 cm, unlike the full wall's -37 cm bound.
            # Recessed oak stops fill the reveal; allow the rear ledges to clear rough stone through the full swing.
            px=x+2.6952*math.cos(angle)+26*math.sin(angle)
            py=y+2.6952*math.sin(angle)-26*math.cos(angle)
            placement=u.Transform(location=[px*original_scale,py*original_scale,z+30.2665],rotation=u.Rotator(yaw=yaw-90))
            t=u.MathLibrary.compose_transforms(placement,base)
            t.scale3d=u.Vector(1,1,1)
            window_actor=actors.spawn_actor_from_class(u.ColdSteelWindow,u.Vector())
            window_actor.set_actor_label('Village_Blacksmith_Window_'+str(len(windows)+1))
            window_actor.set_actor_transform(t,False,False)
            window_actor.tags=['VillageShop.WindowR7']
            window_actor.set_editor_property('use_authored_hinges',True)
            window_actor.set_editor_property('authored_left_hinge',u.Vector(0,-74.,0))
            window_actor.set_editor_property('authored_right_hinge',u.Vector(0,74.,0))
            window_actor.set_editor_property('fixed_swing_direction',1)
            window_actor.set_editor_property('open_angle_degrees',105.)
            window_actor.set_editor_property('open_seconds',.85)
            for comp_name,role in [('WindowFrame','WindowMount'),('WindowLeafLeft','WindowLeft'),('WindowLeafRight','WindowRight')]:
                comp=next(c for c in window_actor.get_components_by_class(u.StaticMeshComponent) if c.get_name()==comp_name)
                comp.set_static_mesh(require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/WindowR7/Meshes/SM_SmithLoft_'+role+'_R7b'))
                comp.set_editor_property('receives_decals',False)
            window_actor.call_method('RefreshAuthoredGeometry')
            windows.append(window_actor)
    lower=-297.4087;upper=2.5913
    # First floor: rear and right sheltered; front arcade and west-front bay open.
    wall(-148.5354,290,lower,0)
    wall(151.4646,290,lower,180,'window') # existing window hole becomes the sealed smoke-duct service penetration
    for yy in (-150,150):wall(291.4646,yy,lower,-90)
    wall(-288.5354,150,lower,-90)
    # Upstairs uses actual window walls and their existing frame/shutter offsets.
    for xx in (-148.5354,151.4646):wall(xx,-290,upper,0,'window',True)
    for xx in (-148.5354,151.4646):wall(xx,290,upper,0)
    wall(291.4646,-150,upper,90)
    wall(291.4646,150,upper,90,'window',True)
    wall(-288.5354,150,upper,-90)
    wall(-288.5354,-150,upper,-90,state='Repaired')
    # Reuse the native fractured western upper bay, at its original stone-to-stone placement.
    for p in pieces:
        n=p['mesh'].split('.')[-1]
        if n.startswith('SM_H_OldWall_00A_Piece') and p['pos'][0]<-300 and p['pos'][1]<0 and p['pos'][2]>-100:
            native('Ruined',p)
    for p in pieces:
        if p['mesh'].split('.')[-1]!='SM_H_WallCorner_00A':continue
        if p['pos'][2]>-100 or p['pos'][1]>0:native('Common',p)
    # The reused rough-edged wall modules have small holes at their mating edges.
    # Repaired joints receive mortar within the wall core, clear of all openings.
    mortar='/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A'
    def joint(x,y,z,sx,sy,sz):
        t=u.MathLibrary.compose_transforms(u.Transform(scale=[sx/100,sy/100,sz/100]),pose(house,x,y,z))
        add('Common','/Engine/BasicShapes/Cube',t,(mortar,))
    xy=XY_FACTOR*SOURCE_SCALE
    upper_center=(upper-geometry['floor'])*SOURCE_SCALE
    lower_center=(lower-geometry['floor'])*SOURCE_SCALE
    for y in (-290,290):joint(1.4646*xy,y*xy,upper_center,42,14,360)
    for x in (-288.5354,291.4646):joint(x*xy,0,upper_center,14,42,360)
    joint(1.4646*xy,290*xy,lower_center,42,14,368)
    joint(291.4646*xy,0,lower_center,14,42,368)
    for x in (-322.5923841575464,314.6869894298937):joint(x*SOURCE_SCALE,0,846,14,20,348)
    for role in ('ArcadeFrame','UpperFloor','Stair','Guardrails','Apron'):
        tags=('Traversal.GuardrailDrop',) if role=='Guardrails' else ()
        transform=pose(house,0,0,0)
        if role=='Apron':
            # House floor datum is +4 cm. Bury the footings 2 cm into the village soil;
            # the 6 cm chimney pad then meets the shaft, while the entrance lip is only 3 cm.
            transform=u.MathLibrary.compose_transforms(u.Transform(location=[0,0,-6],scale=[1,1,1.5]),transform)
        mesh_name='SM_SmithLoft_'+role+('_R4' if role=='ArcadeFrame' else '_R5' if role=='Apron' else '_R6' if role=='Guardrails' else '')
        root=detail if role=='Guardrails' else ASSET_ROOT
        add('Common',root+'/Meshes/'+mesh_name,transform,extra=tags)
    for role,xyz in [('ForgeHearth',HEARTH),('SmokeDuct',HEARTH),('Chimney',CHIMNEY)]:
        root='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR8' if role=='Chimney' else ASSET_ROOT
        suffix='_R8' if role=='Chimney' else '_R5' if role=='SmokeDuct' else ''
        add('Common',root+'/Meshes/SM_SmithLoft_'+role+suffix,pose(house,*xyz))
    # The rear window frame's original offset is rotated with the wall; infill overlaps its rough perimeter.
    rear_x=(151.4646-(154.1598-151.4646))*XY_FACTOR*SOURCE_SCALE
    rear_y=290*XY_FACTOR*SOURCE_SCALE
    add('Common',ASSET_ROOT+'/Meshes/SM_SmithLoft_FlueInfill',pose(house,rear_x,rear_y,0),(mortar,))
    for state,name,x,y,z,yaw,scale in [
        ('Common','HearthPad',STATION[0],STATION[1],0,0,1),
        ('Repaired','OakShelf',315,180,0,90,1),
        ('Repaired','OakTable',-15,-270,0,0,1),
        ('Repaired','OakStool',10,-190,0,0,1),
        ('Ruined','AbandonedTimber',*RUINED_TIMBER),
        ('Ruined','IronStock',270,265,0,35,1),
        ('Repaired','IronStock',315,180,65.5,0,1),
        ('Repaired','IronStock',315,180,117.5,0,.78),
        ('Repaired','TimberBed',*BED,0,1),
        ('Repaired','OakTable',0,250,LOFT_Z,0,1),
        ('Repaired','OakStool',0,160,LOFT_Z,0,1)]:
        path=FURNITURE+name
        add(state,path,standing(house,path,x,y,z,yaw,scale),profile='NoCollision' if name=='IronStock' else 'BlockAll')
    crate='/Game/UndergroundTunnel/Meshes/Props/SM_WoodCrate01a'
    barrel='/Game/Props/CastingStation20260926/SM_CoolingBarrel'
    for state,path,x,y,z,scale in [('Repaired',barrel,300,-210,0,1),('Repaired',crate,240,-300,LOFT_Z,.65)]:
        add(state,path,standing(house,path,x,y,z,0,scale))
    from TradeSign.layout import placements as trade_fittings
    for state,path,transform,profile in trade_fittings(house):
        add(state,path,transform,profile=profile)
    add('Ruined',detail+'/Meshes/SM_SmithLoft_RuinDebris_R6',pose(house,0,0,0),profile='NoCollision')
    add('Ruined',FURNITURE+'ClosedPlaque',pose(house,-365,-410,145),profile='NoCollision')
    state_actors={}
    for (state,path,mats,profile,extra),transforms in groups.items():
        actor=state_actors.get(state)
        if not actor:
            actor=actors.spawn_actor_from_class(u.Actor,u.Vector());actor.set_actor_label('Village_Blacksmith_'+state);state_actors[state]=actor
        parent=sub.k2_gather_subobject_data_for_instance(actor)[0]
        handle,reason=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.HierarchicalInstancedStaticMeshComponent))
        comp=handles.get_associated_object(handles.get_data(handle))
        if not comp:raise RuntimeError(str(reason))
        comp.set_mobility(u.ComponentMobility.STATIC);comp.set_static_mesh(require(path))
        for i,m in enumerate(mats):
            if m:comp.set_material(i,require(m))
        comp.set_collision_profile_name(profile);comp.set_editor_property('receives_decals',False)
        tags=list(extra)+([] if state=='Common' else ['VillageShop.'+state])
        if profile=='NoCollision':tags.append('VillageShop.NoCollision')
        comp.component_tags=tags
        if state=='Repaired':comp.set_visibility(False);comp.set_hidden_in_game(True);comp.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
        comp.add_instances(transforms,False,True,False)
    station=actors.spawn_actor_from_class(u.HillsBlacksmith,u.Vector());station.set_actor_label('Village_01_Blacksmith_Forge')
    station.set_actor_transform(pose(house,*STATION),False,False)
    palette=require('/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette')
    definition=next(p for p in palette.get_editor_property('components') if str(p.get_editor_property('id'))=='casting_station')
    station_mesh=definition.get_editor_property('mesh');station.set_editor_property('station_mesh',station_mesh)
    body=station.get_component_by_class(u.StaticMeshComponent);body.set_static_mesh(station_mesh);body.set_editor_property('receives_decals',False)
    station.set_editor_property('shop_assemblies',list(state_actors.values()))
    station.set_editor_property('repair_area_center',u.Vector(-STATION[0],50-STATION[1],540-STATION[2]))
    station.set_editor_property('repair_area_half_extent',u.Vector(460,565,590))
    from Workfloor.dressing import apply as dress_workfloor
    from ForgeR2.refit import apply_to as fit_forge
    from BenchWork.layout import fit as fit_shoeing_work
    fit_shoeing_work(house,state_actors['Repaired'])
    return {'actor_label':station.get_actor_label(),'revision':7,'window_revision':'7b','chimney_revision':8,'workfloor':dress_workfloor(house,station),'side_blast':fit_forge(house,station),'interactive_windows':len(windows),'default':'ruined','state_groups':len(groups),'floor_z_cm':LOFT_Z,
            'nominal_footprint_cm':[720*XY_FACTOR]*2,'station_mesh':station_mesh.get_path_name(),'chimney_top_cm':1150,'gameplay_tested':False}
