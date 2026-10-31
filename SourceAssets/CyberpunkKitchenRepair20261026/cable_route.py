"""One physical routing contract for source geometry and the saved apartment."""
import math
EDGE_ORIGIN=[1511.,-2003.8,94.7]
EDGE_ENTRY=[1511.,-2003.8,95.07]
EDGE_EXIT=[1516.,-2003.8,93.0]
COFFEE_PORT=[1489.,-1996.8,97.7]
PARAMETERS=dict(cable_width=.62,num_sides=12,solver_iterations=12,substep_time=1/120.,
    use_substepping=True,enable_collision=True,collision_friction=.18,cable_gravity_scale=1.,
    enable_stiffness=False,skip_cable_update_when_not_visible=True,
    skip_cable_update_when_not_owner_recently_rendered=False)

def add_edge_geometry(g):
    # A short, settled bend routes over the actual right counter edge. The two
    # adjoining spans remain live cables. This avoids point-only cable collision
    # cutting a chord through a sharp corner, without oversized invisible colliders.
    path=[]
    for i in range(21):
        t=i/20.;path.append((.02*t,0,.0037+.0093*(3*t*t-2*t*t*t)))
    for i in range(1,49):
        a=i*math.pi/96;path.append((.02+.03*math.sin(a),0,-.017+.03*math.cos(a)))
    g.tube('CoffeeEdgeBend',path,.0031,'Rubber',24)

def annotate(manifest):
    manifest['cable_revision']='edge_contact_v2'
    manifest['cable_route']=dict(origin=EDGE_ORIGIN,entry=EDGE_ENTRY,exit=EDGE_EXIT,coffee_port=COFFEE_PORT,
        live_spans={'Coffee':dict(length_cm=127,segments=64),'CoffeeCounter':dict(length_cm=30.5,segments=32),'Kettle':dict(length_cm=82,segments=48)},parameters=PARAMETERS)
    for row in manifest['cables']:
        if row['name']=='Coffee':row['end']=COFFEE_PORT;row['length_cm']=157.5

def apply(world,actors,helpers):
    import unreal as u
    from pathlib import Path
    import json
    R=Path(__file__).resolve().parent
    load=helpers['load'];save=helpers['save'];boxes=helpers['boxes'];BASE=helpers['BASE'];OLD=helpers['OLD']
    E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem)
    # Full visible slab extents, 0.4 mm contact margin, correctly positioned sink
    # opening. The old inset boxes ended 5 mm before the visible desk edge.
    counter=actors['KP_Counter'];c=counter.static_mesh_component
    path=BASE+'/Meshes/SM_KR_CounterContact'
    m=load(path) if E.does_asset_exist(path) else E.duplicate_asset(c.static_mesh.get_path_name(),path)
    x0,x1=-180.04,180.04;y0,y1=-32.54,32.54
    ax0,ax1=-178.65,-101.35;ay0,ay1=-26.15,26.15;z0,z1=90.7,94.74
    def slab(a,b,d,e):return (((a+b)/2,(d+e)/2,(z0+z1)/2),(b-a,e-d,z1-z0))
    specs=[slab(x0,ax0,y0,y1),slab(ax1,x1,y0,y1),slab(ax0,ax1,y0,ay0),slab(ax0,ax1,ay1,y1)]
    boxes(m,specs);counter.modify();c.set_static_mesh(m);c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
    edge=actors.get('KR_CoffeeEdgeBend')
    if not edge:edge=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*EDGE_ORIGIN));edge.set_actor_label('KR_CoffeeEdgeBend');actors[edge.get_actor_label()]=edge
    edge.modify();edge.static_mesh_component.set_static_mesh(load(BASE+'/Meshes/SM_KR_CoffeeEdgeBend'))
    edge.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    edge.set_actor_transform(u.Transform(location=u.Vector(*EDGE_ORIGIN),rotation=u.Rotator(),scale=u.Vector(1,1,1)),False,False)
    edge.attach_to_actor(counter,'',u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
    edge.tags=['KitchenRepair20261026','KitchenCableContactV2']
    report=dict(revision='edge_contact_v2',counter_mesh=m.get_path_name(),counter_contact_margin_mm=.4,edge_bend_radius_cm=3.,edge_origin=EDGE_ORIGIN,cables=[],runtime_tested=False)
    config=[('Coffee',[1578.,-2036.2,167.3],EDGE_EXIT,127.,64,actors['KR_PowerHardware'],edge),
            ('CoffeeCounter',COFFEE_PORT,EDGE_ENTRY,30.5,32,actors['AP_Kitchen_Coffee'],edge),
            ('Kettle',[1339.5,-2015.7,139.3],[1323.,-1990.5,96.2],82.,48,actors['KR_PowerHardware'],actors['AP_Kitchen_Kettle'])]
    for name,start,end,length,segments,parent,target in config:
        label='KR_Cable_'+name;a=actors.get(label)
        if not a:a=AA.spawn_actor_from_class(u.CableActor,u.Vector(*start));a.set_actor_label(label);actors[label]=a
        a.modify();a.set_actor_location(u.Vector(*start),False,False)
        a.attach_to_actor(parent,'',u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
        # Coffee actor has a 0.75 author scale; cable cross-section remains 6.2 mm.
        a.set_actor_scale3d(u.Vector(1,1,1));c=a.cable_component;c.modify()
        for k,v in dict(PARAMETERS,attach_start=True,attach_end=True,cable_length=length,num_segments=segments).items():c.set_editor_property(k,v)
        c.set_attach_end_to(target,'StaticMeshComponent')
        c.set_editor_property('end_location',target.static_mesh_component.get_world_transform().inverse_transform_location(u.Vector(*end)))
        c.set_collision_profile_name('BlockAllDynamic');c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
        c.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_IGNORE)
        c.set_material(0,load(OLD+'/Materials/M_KP_Rubber'));c.set_cull_distance(3000)
        a.tags=['KitchenRepair20261026','KitchenCableContactV2']
        report['cables'].append(dict(actor=label,start=start,end=end,length_cm=length,segments=segments,friction=.18,substep_seconds=1/120.,end_target=target.get_actor_label(),start_target=parent.get_actor_label()))
    (R/'cable_v2_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report
