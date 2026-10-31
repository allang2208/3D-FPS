"""Publish kitchen repair to the existing formal map. No PIE, preview or new map."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,hashlib,shutil,traceback
R=Path(__file__).resolve().parent;P=R.parents[1]
BASE='/Game/Props/CyberpunkKitchenRepair20261026';OLD='/Game/Props/CyberpunkApartmentKitchen20261024'
MAP='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
G=json.loads((R/'geometry.json').read_text(encoding='utf8'))
report=dict(stage='preparing',meshes={},materials={},changed=[],game_run=False)
if (R/'assets_saved.json').exists():report.update(json.loads((R/'assets_saved.json').read_text(encoding='utf8')))
def record():(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing '+path)
    return a
def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
def node(m,cls,**props):
    n=L.create_material_expression(m,getattr(u,'MaterialExpression'+cls))
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def wire(a,b,pin):
    norm=lambda s:str(s).replace(' ','').replace('_','').lower()
    names=L.get_material_expression_input_names(b);actual=next((str(n) for n in names if norm(n)==norm(pin)),pin)
    if not L.connect_material_expressions(a,'',b,actual):raise RuntimeError('Material pin '+pin)
def material(name,color,rough,metal,normal_strength):
    path=BASE+'/Materials/M_KR_'+name
    if E.does_asset_exist(path):return load(path)
    m=A.create_asset('M_KR_'+name,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    slab=node(m,'SubstrateShadingModels')
    uv=node(m,'TextureCoordinate');scale=node(m,'Multiply');wire(uv,scale,'A');wire(node(m,'Constant',r=1/.36),scale,'B')
    tn=node(m,'TextureSample',texture=load(OLD+'/Textures/T_KP_BrushedSteel_N'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL);wire(scale,tn,'UVs')
    n=node(m,'Custom',code='return normalize(float3(N.xy*S,lerp(1.0,N.z,S)));',output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    pins=[]
    for p in ['N','S']:c=u.CustomInput();c.set_editor_property('input_name',p);pins.append(c)
    n.set_editor_property('inputs',pins);wire(tn,n,'N');wire(node(m,'Constant',r=normal_strength),n,'S')
    values=[(node(m,'Constant3Vector',constant=u.LinearColor(*color,1)),'BaseColor','BASE_COLOR'),(node(m,'Constant',r=rough),'Roughness','ROUGHNESS'),(node(m,'Constant',r=metal),'Metallic','METALLIC'),(n,'Normal','NORMAL')]
    for value,pin,prop in values:wire(value,slab,pin);L.connect_material_property(value,'',getattr(u.MaterialProperty,'MP_'+prop))
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    L.recompile_material(m);save(m);report['materials'][name]=path;record();return m
def boxes(m,specs):
    b=m.get_editor_property('body_setup');b.modify();g=b.get_editor_property('agg_geom');els=[]
    for center,size in specs:
        q=u.KBoxElem();q.set_editor_property('center',u.Vector(*center))
        for axis,v in zip(['x','y','z'],size):q.set_editor_property(axis,v)
        els.append(q)
    for field in ['sphere_elems','sphyl_elems','convex_elems']:g.set_editor_property(field,[])
    g.set_editor_property('box_elems',els);b.set_editor_property('agg_geom',g)
    b.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX);save(m)
def assets():
    stainless=material('Stainless',(.48,.51,.54),.29,1.,.16)
    smoke=material('Smoke',(.012,.016,.021),.18,.35,.035)
    for row in G['meshes']:
        key=row['key'];path=BASE+'/Meshes/SM_KR_'+key;digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
        prior=report['meshes'].get(key,{})
        if prior.get('hash')==digest and E.does_asset_exist(path):continue
        retained={}
        if key=='ResidentialDetails' and E.does_asset_exist(path):
            retained={str(s.material_slot_name):s.material_interface for s in load(path).get_editor_property('static_materials')}
        t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name='SM_KR_'+key
        t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.import_as_skeletal=False
        d=opt.static_mesh_import_data
        for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=True,import_uniform_scale=1.).items():d.set_editor_property(k,v)
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt
        A.import_asset_tasks([t])
        if not t.imported_object_paths:raise RuntimeError('FBX import did not produce '+key)
        m=load(path);bs=SM.get_lod_build_settings(m,0)
        for k,v in dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,recompute_tangents=True,recompute_normals=False).items():bs.set_editor_property(k,v)
        SM.set_lod_build_settings(m,0,bs)
        if key=='ResidentialDetails':
            for i,s in enumerate(m.get_editor_property('static_materials')):
                if str(s.material_slot_name) in retained:m.set_material(i,retained[str(s.material_slot_name)])
        else:
            for i,s in enumerate(m.get_editor_property('static_materials')):
                role=str(s.material_slot_name).removeprefix('KP_')
                mat=stainless if role=='Steel' else smoke if role=='Smoke' else load(OLD+'/Materials/M_KP_'+role)
                m.set_material(i,mat)
        if key=='Oven':boxes(m,[((-2,0,-46), (57.2,61.6,75.8))])
        elif key.startswith('SinkBody'):
            boxes(m,[((0,0,16),(59,64.5,2.2)),((-28.3,0,39),(2.4,64.5,46)),((28.3,0,39),(2.4,64.5,46)),((0,-31.6,51.6),(54.2,1.8,71))])
        else:save(m)
        report['meshes'][key]=dict(path=path,hash=digest,triangles=row['triangles'],bounds=str(m.get_bounding_box()))
        record();print('KITCHEN_MESH_SAVED',key,flush=True)
    report['stage']='assets_saved';record()
def mesh(k):return load(BASE+'/Meshes/SM_KR_'+k)
def static(actors,label,key,pos):
    a=actors.get(label)
    if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos));a.set_actor_label(label);actors[label]=a
    a.modify();a.static_mesh_component.set_static_mesh(mesh(key));a.static_mesh_component.set_editor_property('override_materials',[])
    a.set_actor_transform(u.Transform(location=u.Vector(*pos),rotation=u.Rotator(),scale=u.Vector(1,1,1)),False,False)
    a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    a.set_editor_property('tags',list(a.tags)+([] if 'KitchenRepair20261026' in [str(t) for t in a.tags] else ['KitchenRepair20261026']))
    return a
def apply_upgrade(world):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    for label in ['KP_Sink','KP_OvenFront','KP_Counter','AP_Kitchen_Coffee','AP_Kitchen_Kettle','AP_Container_Kitchen_Sink_0','AP_Container_Kitchen_Sink_1']:
        if label not in actors:raise RuntimeError('Kitchen dependency missing '+label)
    updates=[]
    for label,key,pos in [('KP_Sink','Sink',(1228,-1985,94.7)),('KP_OvenFront','Oven',(1427,-1985,94.7)),('KR_PowerHardware','PowerHardware',(0,0,0))]:
        a=static(actors,label,key,pos)
        if key=='Oven':a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        updates.append(label)
    for i in range(2):
        a=actors['AP_Container_Kitchen_Sink_'+str(i)];a.modify();a.body.set_static_mesh(mesh('SinkBody'+str(i)));a.body.set_editor_property('override_materials',[]);updates.append(a.get_actor_label())
    # Only the current ResidentialDetails instance changes; original source asset stays intact.
    residential=next((a for a in actors.values() if isinstance(a,u.StaticMeshActor) and a.static_mesh_component.static_mesh and a.static_mesh_component.static_mesh.get_name() in ['SM_AP_ResidentialDetails','SM_KR_ResidentialDetails']),None)
    if not residential:raise RuntimeError('ResidentialDetails instance missing')
    c=residential.static_mesh_component;source=c.static_mesh;new=mesh('ResidentialDetails')
    if source!=new:
        if '/RefinementV2/' not in source.get_path_name():raise RuntimeError('Residential source revision changed '+source.get_path_name())
        byslot={str(s.material_slot_name):c.get_material(i) for i,s in enumerate(source.get_editor_property('static_materials'))}
        for i,s in enumerate(new.get_editor_property('static_materials')):
            if str(s.material_slot_name) not in byslot:raise RuntimeError('Residential material slot mismatch '+str(s.material_slot_name))
            new.set_material(i,byslot[str(s.material_slot_name)])
        save(new);residential.modify();c.set_static_mesh(new);c.set_editor_property('override_materials',[])
    updates.append(residential.get_actor_label())
    # A legacy cabinet must not be recreated inside the dedicated oven module.
    duplicate=actors.get('AP_Container_Kitchen_Base_4')
    if duplicate:
        duplicate.modify();duplicate.body.set_static_mesh(None);duplicate.door.set_static_mesh(None);duplicate.set_actor_hidden_in_game(True)
    # Local collision copies provide appliance contact without changing shared library meshes.
    for name,specs in [('Coffee',[((0,-1,28),(42,41,56))]),('Kettle',[((0,0,1.2),(17.5,17.5,2.4)),((0,0,13),(16,16,22))])]:
        actor=actors['AP_Kitchen_'+name];c=actor.static_mesh_component;src=c.static_mesh;path=BASE+'/Meshes/SM_KR_'+name+'Collision'
        cp=load(path) if E.does_asset_exist(path) else E.duplicate_asset(src.get_path_name(),path)
        boxes(cp,specs);actor.modify();c.set_static_mesh(cp);c.set_collision_profile_name('BlockAll')
        c.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_IGNORE)
        c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY);updates.append(actor.get_actor_label())
    cables=[]
    for row in G['cables']:
        label='KR_Cable_'+row['name'];a=actors.get(label)
        if not a:a=AA.spawn_actor_from_class(u.CableActor,u.Vector(*row['start']));a.set_actor_label(label)
        a.modify();a.set_actor_location(u.Vector(*row['start']),False,False)
        a.attach_to_actor(actors['KR_PowerHardware'],'',u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
        c=a.get_editor_property('cable_component');c.modify()
        for k,v in dict(attach_start=True,attach_end=True,cable_length=row['length_cm'],num_segments=28,num_sides=10,cable_width=.62,solver_iterations=8,substep_time=.0125,use_substepping=True,enable_collision=True,collision_friction=.65,cable_gravity_scale=1.,enable_stiffness=False,skip_cable_update_when_not_visible=True,skip_cable_update_when_not_owner_recently_rendered=False).items():c.set_editor_property(k,v)
        target=actors['AP_Kitchen_'+row['name']];component=target.static_mesh_component
        c.set_attach_end_to(target,'StaticMeshComponent')
        if c.get_attached_component()!=component:raise RuntimeError('Cable attachment does not resolve '+label)
        endpoint=component.get_world_transform().inverse_transform_location(u.Vector(*row['end']))
        c.set_editor_property('end_location',endpoint)
        c.set_collision_profile_name('BlockAllDynamic');c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
        c.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_IGNORE)
        c.set_material(0,load(OLD+'/Materials/M_KP_Rubber'))
        c.set_editor_property('cast_shadow',True);c.set_cull_distance(3000)
        a.set_editor_property('tags',['KitchenRepair20261026'])
        cables.append(dict(actor=label,start=row['start'],end=row['end'],length_cm=row['length_cm'],attached_actor=target.get_actor_label(),attached_component=c.get_attached_component().get_path_name(),collision=c.get_editor_property('enable_collision'),gravity=c.get_editor_property('cable_gravity_scale')))
        updates.append(label)
    # Read the actual installed world bounds at the corrected oven/cabinet interfaces.
    ob=actors['KP_OvenFront'].static_mesh_component.static_mesh.get_bounding_box();ox=actors['KP_OvenFront'].get_actor_location().x
    left=actors['AP_Container_Kitchen_Base_3'];right=actors['AP_Container_Kitchen_Base_5']
    lb=left.body.static_mesh.get_bounding_box();rb=right.body.static_mesh.get_bounding_box()
    gaps=dict(left_cm=ox+ob.min.x-(left.get_actor_location().x+lb.max.x),right_cm=right.get_actor_location().x+rb.min.x-(ox+ob.max.x))
    if min(gaps.values())<.5:raise RuntimeError('Oven module still overlaps adjacent cabinet '+str(gaps))
    normal=L.get_material_property_input_node(load(BASE+'/Materials/M_KR_Stainless'),u.MaterialProperty.MP_NORMAL)
    if not normal:raise RuntimeError('Stainless normal is not connected')
    result=dict(updated=updates,cables=cables,oven_side_clearances=gaps,sink_depth_cm=25,stainless_normal_connected=True,old_power_faces_removed=G['old_power_faces_removed'],runtime_physics_tested=False)
    if G.get('cable_revision')=='edge_contact_v2':
        import runpy
        result['cable_refinement']=runpy.run_path(str(R/'cable_route.py'))['apply'](world,actors,globals())
        result['cables']=result['cable_refinement']['cables']
        result['updated']+=['KP_Counter','KR_CoffeeEdgeBend','KR_Cable_CoffeeCounter']
    wall=actors['AP_Wall_Back'].static_mesh_component;wb=wall.static_mesh.get_bounding_box()
    result['wall_support']=dict(mesh=wall.static_mesh.get_path_name(),envelope_front_y_cm=wall.get_world_transform().transform_location(u.Vector(wb.min.x,wb.max.y,wb.min.z)).y,flat_wall_face_y_cm=-2040.,coffee_outlet_back_y_cm=-2040.)
    (R/'kitchen_layout_check.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    return result
def main():
    assets()
    commandlet='-run=' in u.SystemLibrary.get_command_line().lower()
    level=u.get_editor_subsystem(u.LevelEditorSubsystem) if not commandlet else None
    if level and level.is_in_play_in_editor():raise RuntimeError('PIE must end before saving')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem) if not commandlet else None
    world=ed.get_editor_world() if ed else None
    if not world or world.get_path_name()!=MAP+'.L_CyberpunkApartment':world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    path=P/'Content/GameMaps/L_CyberpunkApartment.umap';backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/path.name)
    result=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Formal kitchen map save failed')
    result.update(stage='map_saved',map=MAP,backup=str(backup/path.name),saved_at=datetime.now().astimezone().isoformat(),map_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (R/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf8');print('KITCHEN_REPAIR_MAP_SAVED',len(result['updated']),flush=True)
    if (R/'failure.txt').exists():(R/'failure.txt').unlink()
if __name__=='__main__':
    try:main()
    except Exception:
        (R/'failure.txt').write_text(traceback.format_exc(),encoding='utf8');raise
