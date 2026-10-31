"""Install the scoped kitchen into the current saved apartment, never rebuild it.
Reversible map backup plus a serialized record of changed kitchen actors.
"""
from pathlib import Path
from datetime import datetime
import json,shutil,traceback,hashlib
from spec import source_to_ue_cm, SOURCE_CONTAINER_ANCHORS, PBR
import unreal as u
R=Path(__file__).resolve().parent;PROJECT=R.parents[2]
BASE='/Game/Props/CyberpunkApartmentKitchen20261024';MAP='/Game/GameMaps/L_CyberpunkApartment'
E=u.EditorAssetLibrary;AA=u.get_editor_subsystem(u.EditorActorSubsystem);L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
report=dict(stage='preparing',map=MAP,asset_base=BASE,updated=[],added=[],preserved={},normal_bound_slots=0,tests_run=False,game_run=False,visual_acceptance=False)
def record():(R/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def load(path):
    o=u.load_asset(path)
    if not o:raise RuntimeError('Missing '+path)
    return o
def mesh(key):return load(BASE+'/Meshes/SM_KP_'+key)
def collision_boxes(asset,specs):
    # Four slabs support the worktop while preserving the real sink aperture.
    # This is asset preparation inside the single background map-write batch.
    body=asset.get_editor_property('body_setup');body.modify()
    geom=body.get_editor_property('agg_geom');elems=[]
    for center,size in specs:
        box=u.KBoxElem();box.set_editor_property('center',u.Vector(*[v*100 for v in center]))
        for axis,value in zip(('x','y','z'),size):box.set_editor_property(axis,value*100)
        elems.append(box)
    geom.set_editor_property('box_elems',elems);body.set_editor_property('agg_geom',geom)
    body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
    # Python property setters mark the object modified; UE does not expose
    # Object/Package.mark_package_dirty() to Python. Save through the editor API.
    if not E.save_loaded_asset(asset,False):
        if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False):raise RuntimeError('Save worktop collision')
    report['counter_collision']=dict(simple_boxes=len(body.get_editor_property('agg_geom').get_editor_property('box_elems')),sink_aperture='open')
def fridge_slot_role(slotname):
    # Exterior-only recolour. Interior and gasket materials are immutable here.
    return {'RS_Ceramic':'Enamel','RS_BareSteel':'Steel'}.get(str(slotname))

def role_from_name(name):
    if name.startswith(('MI_AP7_MI_AP4_','MI_AP4_')):
        tail=name.replace('MI_AP7_MI_AP4_','').replace('MI_AP4_','').split('_UV')[0]
        return {'Teal':'Enamel','Oak':'Wood','BareSteel':'Steel','Brass':'Steel','Ceramic':'Porcelain','Plastic':'Graphite','Armor':'Enamel','EdgeSteel':'Steel','CabinetInside':'Inside','Stone':'Stone','Linen':'Linen','Terry':'Linen','Fabric':'Linen','Rubber':'Rubber'}.get(tail,tail)
    return None
def recolor(component,force=False):
    original=[m.get_path_name() if m else None for m in component.get_materials()]
    changed=[]
    for i,material in enumerate(component.get_materials()):
        if not material:continue
        name=material.get_name();role=role_from_name(name)
        if not role and 'Ceramic' in name:role='Enamel'
        if not role and any(s in name for s in ['BareSteel','Stainless','Steel','Metal']):role='Steel'
        if not role and ('Wood' in name or 'Oak' in name):role='Wood'
        if not role and 'Rubber' in name:role='Rubber'
        if not role and 'Coffee_V5' in name:role='Coffee'
        if not role and 'Crema' in name:role='Porcelain'
        if not role and 'MachineCoat' in name:role='Enamel'
        if not role:continue
        mat=load(BASE+'/Materials/M_KP_'+role)
        component.set_material(i,mat);changed.append(dict(slot=i,source=material.get_path_name(),target=mat.get_path_name(),normal_connected='M_KP_'+role in ['M_KP_Enamel','M_KP_Stone','M_KP_Tile','M_KP_Steel','M_KP_Wood','M_KP_Linen','M_KP_Porcelain']))
        report['normal_bound_slots']+=int(changed[-1]['normal_connected'])
    return dict(before=original,changes=changed)
def new_actor(actors,label,key,pos,folder='KitchenDetail20261024'):
    old=actors.get(label)
    if old:return old
    a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*pos),u.Rotator())
    a.set_actor_label(label);a.set_folder_path('Apartment20261022/'+folder)
    a.tags.append('KitchenDetail20261024');a.static_mesh_component.set_static_mesh(mesh(key))
    a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if key=='Counter' else u.CollisionEnabled.NO_COLLISION)
    a.static_mesh_component.set_cull_distance(2300.)
    a.static_mesh_component.set_editor_property('cast_shadow',key not in ['Dishes','Prep','DiningDressing'])
    return a

def scale_tuple(c):
    # UE returns a Vector here in some builds; normalise to a 3-tuple.
    s=c.relative_scale3d
    return (s.x,s.y,s.z) if hasattr(s,'x') else tuple(s)

def component_snapshot(c):
    return dict(mesh=c.static_mesh.get_path_name() if c.static_mesh else None,
                materials=[m.get_path_name() if m else None for m in c.get_materials()],
                collision_enabled=str(c.get_collision_enabled()),
                collision_profile=str(c.get_collision_profile_name()),
                location=list(c.relative_location.to_tuple()),
                rotation=dict(pitch=c.relative_rotation.pitch,yaw=c.relative_rotation.yaw,roll=c.relative_rotation.roll),
                scale=list(scale_tuple(c)))

def fridge_detail(row,suffix,parent):
    # Reuse V1 native instance components; V2 must never stack a second kitchen.
    name='KPDetail_'+suffix
    for component in row.get_components_by_class(u.StaticMeshComponent):
        if component.get_name()==name:
            if component.get_attach_parent()!=parent:raise RuntimeError('Existing detail has wrong parent '+name)
            component.set_static_mesh(mesh('Fridge'+suffix))
            component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            component.set_relative_transform(u.Transform(),False,False)
            _sc=component.relative_scale3d
            _scale=(_sc.x,_sc.y,_sc.z) if hasattr(_sc,'x') else tuple(_sc)
            if list(component.relative_location.to_tuple())!=[0.,0.,0.] or any(abs(v)>.00001 for v in [component.relative_rotation.pitch,component.relative_rotation.yaw,component.relative_rotation.roll]) or any(abs(v-1)>.00001 for v in _scale):
                raise RuntimeError('Existing detail local transform is not identity '+name)
            report['updated'].append(dict(actor=row.get_actor_label()+':'+name,action='reuse existing native detail; update asset'))
            report['preserved'].setdefault('fridge_details',{})[name]=dict(parent=parent.get_path_name(),component=component.get_path_name(),location=list(component.relative_location.to_tuple()),scale=list(scale_tuple(component)),mobility=str(component.mobility),reused=True)
            return component
    # Native editor subsystem performs AddInstanceComponent/RegisterComponent,
    # neither of which is exposed as a Python method on Actor/ActorComponent.
    ss=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    lib=u.SubobjectDataBlueprintFunctionLibrary
    handles=ss.k2_gather_subobject_data_for_instance(row)
    root=next((h for h in handles if lib.get_associated_object(ss.k2_find_subobject_data_from_handle(h))==row),None)
    if root is None:raise RuntimeError('Missing actor subobject context '+name)
    ph=ss.find_handle_for_object(root,parent)
    if not lib.is_handle_valid(ph):raise RuntimeError('Missing native hinge/root handle '+name)
    params=u.AddNewSubobjectParams()
    params.new_class=u.StaticMeshComponent
    params.parent_handle=ph
    params.blueprint_context=None
    params.conform_transform_to_parent=False
    nh,reason=ss.add_new_subobject(params)
    if not lib.is_handle_valid(nh):raise RuntimeError('Cannot add refrigerator detail '+name+': '+str(reason))
    nd=ss.k2_find_subobject_data_from_handle(nh)
    c=lib.get_associated_object(nd)
    if not c:raise RuntimeError('Missing newly added detail component '+name)
    c.rename(name)
    c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_static_mesh(mesh('Fridge'+suffix))
    c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    c.set_cull_distance(2200.)
    c.set_editor_property('cast_shadow',True)
    if not ss.attach_subobject(ph,nh):raise RuntimeError('Cannot attach detail to native hierarchy '+name)
    c.set_relative_transform(u.Transform(),False,False)
    if c.get_attach_parent()!=parent:raise RuntimeError('Refrigerator detail not parented to native hierarchy '+name)
    if list(c.relative_location.to_tuple())!=[0.,0.,0.] or any(abs(v)>.00001 for v in [c.relative_rotation.pitch,c.relative_rotation.yaw,c.relative_rotation.roll]) or list(scale_tuple(c))!=[1.,1.,1.]:
        raise RuntimeError('Refrigerator detail local transform is not identity '+name)
    report['added'].append(row.get_actor_label()+':'+name)
    report['preserved'].setdefault('fridge_details',{})[name]=dict(parent=parent.get_path_name(),component=c.get_path_name(),location=list(c.relative_location.to_tuple()),scale=list(scale_tuple(c)),mobility=str(c.mobility))
    return c

def validate_assets():
    source=json.loads((R/'assembly.json').read_text())
    receipt=json.loads((R/'assets_saved.json').read_text())
    required={row['key'].removeprefix('KIT_') for row in source['meshes'] if not row.get('reused')}
    if receipt.get('stage')!='assets_saved' or not required.issubset(receipt['meshes']):raise RuntimeError('Final kitchen asset receipt is incomplete')
    for row in source['meshes']:
        key=row['key'].removeprefix('KIT_')
        if row.get('local_audit_only') and not row.get('fbx'):
            continue  # Native mesh reuse is measured locally, never re-exported.
        entry=receipt['meshes'].get(key,{})
        if entry.get('fbx_sha256')!=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest():raise RuntimeError('Stale imported component '+key)
        if not row.get('reused'):load(BASE+'/Meshes/SM_KP_'+key)
    # UE reports mesh bounds in centimetres. The trim must sit on the door front
    # (-Y), span the door width and start at the measured vertical anchor.
    for key,upper in [('FridgeLowerDoor',False),('FridgeUpperDoor',True)]:
        b=mesh(key).get_bounding_box()
        if b.min.x<5.0 or b.max.x>71.1:raise RuntimeError('Fridge trim axes changed '+key)
        if b.min.y>-3.24 or b.max.y<-3.74:raise RuntimeError('Fridge trim front changed '+key)
        expected_z=110.0 if upper else 13.0
        if abs(b.min.z-expected_z)>.2:raise RuntimeError('Fridge trim vertical anchor '+key)
    if len(receipt.get('normal_bindings',{}))!=7:raise RuntimeError('Seven connected PBR normal bindings are required')
    for role,entry in receipt['normal_bindings'].items():
        # Role keys already carry the KP_ prefix (KP_Enamel), so only add the
        # material prefix when the key does not already start with it.
        fallback=BASE+'/Materials/M_'+role if role.startswith('KP_') else BASE+'/Materials/M_KP_'+role
        mat=load(entry['path'] if 'path' in entry else fallback)
        normal=load(entry['texture'])
        if normal.get_editor_property('compression_settings')!=u.TextureCompressionSettings.TC_NORMALMAP:raise RuntimeError('Normal compression '+role)
        if normal.get_editor_property('flip_green_channel'):raise RuntimeError('Normal green-channel policy '+role)
        if not L.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL):raise RuntimeError('Disconnected normal input '+role)
        samples=[n for n in L.get_material_expressions(mat) if isinstance(n,u.MaterialExpressionTextureSample) and n.get_editor_property('texture')==normal]
        if not samples or any(n.get_editor_property('sampler_type')!=u.MaterialSamplerType.SAMPLERTYPE_NORMAL for n in samples):raise RuntimeError('Normal sampler '+role)
        for pin in ['BASE_COLOR','ROUGHNESS','METALLIC','AMBIENT_OCCLUSION']:
            if not L.get_material_property_input_node(mat,getattr(u.MaterialProperty,'MP_'+pin)):raise RuntimeError('Disconnected PBR property '+role+' '+pin)
        # normal_bindings keys are KP_<Role>; PBR is keyed by the bare role.
        expected=PBR[role[3:] if role.startswith('KP_') else role]
        for node in L.get_material_expressions(mat):
            if isinstance(node,u.MaterialExpressionConstant3Vector):
                color=node.get_editor_property('constant')
                # Neutral family tints avoid the V1 double-green multiplication.
                if max(color.r,color.g,color.b)-min(color.r,color.g,color.b)>.06:raise RuntimeError('Colored PBR multiplier remains '+role)
        receipt_entry=receipt['materials'][role]
        if receipt_entry.get('period_m')!=expected['period'] or receipt_entry.get('source_sha256')!=receipt['source_sha256']:raise RuntimeError('Stale PBR source '+role)
    report['source_sha256']=receipt['source_sha256']
    report['asset_gate']=dict(meshes=len(required),normal_bindings=7,fbx_hashes_current=True,neutral_tints=True,texture_directory=receipt.get('texture_directory'),texture_source_sha256=receipt.get('texture_source_sha256'))

def install(world):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    source=json.loads((R/'assembly.json').read_text())
    scope=json.loads((R/'current-interfaces-v2.json').read_text())
    if scope.get('stage')!='read_complete':raise RuntimeError('Measured current interface read is incomplete')
    targets=[a for a in actors.values() if isinstance(a,u.ColdSteelSceneContainer) and (str(a.get_editor_property('container_id')).startswith('Apartment.Kitchen_') or str(a.get_editor_property('container_id')).startswith('Apartment.Fridge_'))]
    if len(targets)!=12:raise RuntimeError('Kitchen container contract changed; expected 12, found '+str(len(targets)))
    report['container_contract']=dict(expected=12,found=len(targets),ids=[str(a.get_editor_property('container_id')) for a in targets])
    report['coordinate_contract']=dict(source_units='m',ue_units='cm',ue_kitchen_origin_cm=[445.,-673.,0.],rotation='identity')
    for row in targets:
        cid=str(row.get_editor_property('container_id'))
        suffix=cid.removeprefix('Apartment.')
        if suffix not in SOURCE_CONTAINER_ANCHORS:raise RuntimeError('Unmapped native container anchor '+cid)
        actual=list(row.get_actor_location().to_tuple())
        expected=source_to_ue_cm(SOURCE_CONTAINER_ANCHORS[suffix])
        if any(abs(a-b)>.02 for a,b in zip(actual,expected)):
            raise RuntimeError('Native kitchen anchor differs from authoritative scope '+cid+': '+str(actual)+' != '+str(expected))
        rotation=row.get_actor_rotation()
        if any(abs(v)>.01 for v in [rotation.pitch,rotation.yaw,rotation.roll]):
            raise RuntimeError('Kitchen coordinate transform does not authorize rotated container '+cid)
    # Reconcile the authoring support anchors with the actual mesh receipt before
    # any map mutation. Cooking is merged into OvenFront in build_kitchen.py:
    # induction glass/rings share that mesh's z=0 support datum. Coffee/kettle
    # remain existing actors; fridge trim belongs to native component hierarchies.
    supported_anchors={
        'Counter':'new_mesh','BackSplash':'new_mesh','OvenFront':'new_mesh',
        'Sink':'new_mesh','UtilityRail':'new_mesh','Prep':'new_mesh',
        'Dishes':'new_mesh','DiningDressing':'new_mesh',
        'Cooking':'merged_into_OvenFront',
        'FridgeLowerBody':'native_root_component','FridgeUpperBody':'native_root_component',
        'FridgeLowerDoor':'native_door_hinge','FridgeUpperDoor':'native_door_hinge',
        'Coffee':'existing_AP_Kitchen_Coffee','Kettle':'existing_AP_Kitchen_Kettle',
    }
    actual_anchors=set(source['placements'])
    if actual_anchors!=set(supported_anchors):
        raise RuntimeError('Reconcile every kitchen placement before installation: '+str(sorted(actual_anchors^set(supported_anchors))))
    if 'OvenFront' not in source['meshes'] and not any(row.get('key')=='OvenFront' for row in source['meshes']):
        raise RuntimeError('OvenFront mesh is required for the merged cooking assembly')
    for key,disposition in supported_anchors.items():
        if disposition=='new_mesh' and not any(row.get('key')==key for row in source['meshes']):
            raise RuntimeError('Missing installed component mesh '+key)
    report['placement_contract']=dict(
        anchors=len(supported_anchors),dispositions=supported_anchors,
        cooking='installed once as part of OvenFront; no placeholder SM_KP_Cooking',
        note='Authoring placement coordinates share the measured kitchen translation; this is not a separate local-axis proof.')
    report['coordinate_contract']['verified_native_anchors']=12
    report['initial_actors']={label:dict(path=a.get_path_name(),location=list(a.get_actor_location().to_tuple()),rotation=dict(pitch=a.get_actor_rotation().pitch,yaw=a.get_actor_rotation().yaw,roll=a.get_actor_rotation().roll),scale=list(a.get_actor_scale3d().to_tuple()),materials={} if not isinstance(a,u.StaticMeshActor) else [m.get_path_name() if m else None for m in a.static_mesh_component.get_materials()]) for label,a in actors.items() if label in ['AP_Kitchen_Run','AP_Kitchen_Coffee','AP_Kitchen_Kettle','AP_Kitchen_Dining','AP_Dining_Chair0','AP_Dining_Chair1','AP_Dining_Chair2','AP_Dining_Chair3']}
    for row in targets:
        cid=str(row.get_editor_property('container_id'))
        expected=scope['targets'].get(row.get_actor_label())
        if not expected or expected.get('container_id')!=cid:raise RuntimeError('Unexpected target identity '+row.get_actor_label())
        if row.door.get_attach_parent()!=row.door_hinge:raise RuntimeError('Door hierarchy changed '+cid)
        report['preserved'].setdefault('containers',{})[cid]=dict(
            actor=row.get_path_name(),caption=str(row.get_editor_property('caption')),
            storage_pages=row.get_editor_property('storage_pages'),
            opening_duration=row.get_editor_property('opening_duration'),
            drawer_travel=list(row.get_editor_property('drawer_travel').to_tuple()),
            hinge_parent=row.door_hinge.get_attach_parent().get_path_name() if row.door_hinge.get_attach_parent() else None,
            opening_motion=str(row.get_editor_property('opening_motion')),
            opened_yaw=row.get_editor_property('opened_yaw'),
            initial_open_fraction=row.get_editor_property('initial_open_fraction'),
            hinge_location=list(row.door_hinge.relative_location.to_tuple()),
            hinge_rotation=dict(pitch=row.door_hinge.relative_rotation.pitch,yaw=row.door_hinge.relative_rotation.yaw,roll=row.door_hinge.relative_rotation.roll),
            body=component_snapshot(row.body),door=component_snapshot(row.door))
    report['preserved']['original_container_contract']=report['preserved']['containers']
    report['preserved']['hinge_parents']={str(row.get_editor_property('container_id')):row.door.get_attach_parent().get_path_name() for row in targets}
    counter=mesh('Counter')
    # Final aperture-aware collision. The worktop spans local X [-1.8,1.8],
    # Y [-.325,.325], Z [.907,.947]; the basin aperture is the rounded
    # 0.771 x 0.521 rect at X=7.50 m, i.e. local X -1.4..-.629, Y -.2605..+.2605.
    # Four convex slabs surround that opening and never seal it.
    slab_z=(.907+.947)/2;slab_h=.040
    apron=.010;x0,x1=-1.795,1.795;y0,y1=-.320,.320
    ax0,ax1=-1.412,-.617;ay0,ay1=-.272,.272
    boxes=[
        (((x0+ax0)/2,(y0+y1)/2,slab_z),(ax0-x0,y1-y0,slab_h)),      # left of aperture
        (((ax1+x1)/2,(y0+y1)/2,slab_z),(x1-ax1,y1-y0,slab_h)),      # right of aperture
        (((ax0+ax1)/2,(y0+ay0)/2,slab_z),(ax1-ax0,ay0-y0,slab_h)),  # rear of aperture
        (((ax0+ax1)/2,(ay1+y1)/2,slab_z),(ax1-ax0,y1-ay1,slab_h)),  # front of aperture
    ]
    collision_boxes(counter,[((cx,cy,cz),(sx,sy,sz)) for (cx,cy,cz),(sx,sy,sz) in boxes])
    report['counter_collision']['boxes']=[dict(center=[cx,cy,cz],size=[sx,sy,sz]) for (cx,cy,cz),(sx,sy,sz) in boxes]
    report['counter_collision']['aperture_local']=dict(x=[ax0,ax1],y=[ay0,ay1])
    report['counter_collision']['note']='four convex slabs surround the real rounded basin opening; no sealing slab'
    # The legacy flat cabinet run is retired only after all replacement assets exist.
    # Searchable actors stay exactly where they are; hinge and storage IDs untouched.
    if 'AP_Kitchen_Run' in actors:
        a=actors['AP_Kitchen_Run'];legacy_mesh=a.static_mesh_component.static_mesh
        report['retired_run']=dict(mesh=legacy_mesh.get_path_name() if legacy_mesh else None,collision=str(a.static_mesh_component.get_collision_enabled()),hidden=a.hidden,materials=[m.get_path_name() if m else None for m in a.static_mesh_component.get_materials()],already_retired=legacy_mesh is None)
        if not a.hidden:
            a.static_mesh_component.set_static_mesh(None)
            a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
            a.set_is_temporarily_hidden_in_editor(True);a.set_actor_hidden_in_game(True)
        report['updated'].append(dict(actor='AP_Kitchen_Run',action='retire flat visual only; interactive actors remain'))
    for label,row in actors.items():
        if not isinstance(row,u.ColdSteelSceneContainer):continue
        cid=row.get_editor_property('container_id')
        if not cid.startswith('Apartment.Kitchen_') and not cid.startswith('Apartment.Fridge_'):continue
        before=dict(id=cid,hinge=list(row.door_hinge.relative_location.to_tuple()),position=list(row.get_actor_location().to_tuple()),body=row.body.static_mesh.get_path_name(),front=row.door.static_mesh.get_path_name())
        if cid.startswith('Apartment.Kitchen_'):
            upper='Upper' in cid
            body=mesh('UpperBody' if upper else 'BaseBody');front=mesh('UpperFront' if upper else 'BaseFront')
            row.body.set_static_mesh(body);row.door.set_static_mesh(front)
            for c in [row.body,row.door]:c.set_editor_property('override_materials',[])
            # Existing collision channels and Pawn response are serialized gameplay
            # contracts. Mesh replacement alone must not rewrite them.
            report['preserved'].setdefault('collision',{})[cid]=dict(body=str(row.body.get_collision_profile_name()),front=str(row.door.get_collision_profile_name()),pawn=str(row.door.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)))
        else:
            part='Upper' if cid.endswith('Upper') else 'Lower'
            for part_type in ['Body','Door']:
                suffix=part+part_type
                c=row.body if part_type=='Body' else row.door
                original=c.static_mesh
                # Keep native collision/body setup and the shared asset untouched.
                # Only exterior enamel/steel instance slots use kitchen PBR; interior
                # PoolIvory and FreshPlastic slots are deliberately not recoloured.
                for i,slot in enumerate(original.get_editor_property('static_materials')):
                    role=fridge_slot_role(slot.material_slot_name)
                    if role:c.set_material(i,load(BASE+'/Materials/M_KP_'+role))
                report['preserved']['fridge_'+suffix]=dict(source=original.get_path_name(),interior_retained=True,instance_only=True,slots=[str(s.material_slot_name) for s in original.get_editor_property('static_materials')])
                if part_type=='Door':
                    fridge_detail(row,suffix,row.door_hinge)
                    report['preserved'].setdefault('collision',{})[cid+'_door']='unchanged native door collision'
                else:
                    fridge_detail(row,suffix,row.root_component)
            report['normal_bound_slots']+=2
        report['updated'].append(dict(actor=label,id=cid,before=before,hinge_after=list(row.door_hinge.relative_location.to_tuple()),position_after=list(row.get_actor_location().to_tuple())))
    dining=actors.get('AP_Kitchen_Dining')
    if not dining:raise RuntimeError('Formal dining support actor missing')
    table=dining.static_mesh_component
    table_box=table.static_mesh.get_bounding_box()
    if table.static_mesh.get_path_name()!='/Game/Dungeons/StaffLiving20261002/Meshes/SM_Staff_DiningTable.SM_Staff_DiningTable':raise RuntimeError('Formal dining support mesh changed')
    table_origin=table.get_world_transform().transform_location(u.Vector(0,0,0))
    support_world=table.get_world_transform().transform_location(u.Vector((table_box.min.x+table_box.max.x)/2,(table_box.min.y+table_box.max.y)/2,table_box.max.z))
    if abs(support_world.z-78.25)>.05:raise RuntimeError('Unexpected formal dining support height '+str(support_world.z))
    dining_anchor=(table_origin.x,table_origin.y,support_world.z)
    report['dining_support']=dict(actor=dining.get_path_name(),table_transform=component_snapshot(table),table_bounds_cm=[list(table_box.min.to_tuple()),list(table_box.max.to_tuple())],support_world_cm=list(support_world.to_tuple()),dressing_anchor_cm=list(dining_anchor),replaces_old_room_anchor=True)
    for key,p in source['placements'].items():
        disposition=supported_anchors[key]
        if disposition!='new_mesh':continue
        if key=='DiningDressing' and abs(p[2]-.7825)>.00001:raise RuntimeError('Dining local datum differs from measured table')
        pos=dining_anchor if key=='DiningDressing' else source_to_ue_cm(p)
        a=new_actor(actors,'KP_'+key,key,pos)
        a.static_mesh_component.set_static_mesh(mesh(key))
        a.set_actor_transform(u.Transform(location=u.Vector(*pos),rotation=u.Rotator(),scale=u.Vector(1,1,1)),False,False)
        a.static_mesh_component.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if key=='Counter' else u.CollisionEnabled.NO_COLLISION)
        a.static_mesh_component.set_cull_distance(2300.)
        report['updated'].append(dict(actor=a.get_actor_label(),mesh=mesh(key).get_path_name(),position_cm=list(pos)))
    report['added']=sorted(set(report['added']))
    for label in ['AP_Kitchen_Coffee','AP_Kitchen_Kettle']:
        if label in actors:
            a=actors[label];loc=a.get_actor_location()
            if abs(loc.z-94.0)<.02:
                a.set_actor_location(u.Vector(loc.x,loc.y,94.7),False,False)
                report['updated'].append(dict(actor=label,action='support on measured 94.7cm worktop; XY/scale/collision unchanged'))
    if 'AP_Kitchen_Coffee' in actors:
        c=actors['AP_Kitchen_Coffee'].static_mesh_component
        report['preserved']['coffee']=recolor(c)
        report['preserved']['coffee']['collision_unchanged']=str(c.get_collision_enabled())
    if 'AP_Kitchen_Kettle' in actors:report['preserved']['kettle']=recolor(actors['AP_Kitchen_Kettle'].static_mesh_component)
    if 'AP_Kitchen_Dining' in actors:report['preserved']['dining']=recolor(actors['AP_Kitchen_Dining'].static_mesh_component)
    for i in range(4):
        label='AP_Dining_Chair'+str(i)
        if label in actors:report['preserved']['chair_'+str(i)]=recolor(actors[label].static_mesh_component)
    atmosphere=actors.get('AP7_Atmosphere')
    if not atmosphere:raise RuntimeError('Expected atmosphere owner missing; refusing incomplete scope verification')
    report['preserved']['atmosphere']=dict(clock=atmosphere.get_editor_property('animation_clock').get_path_name() if atmosphere.get_editor_property('animation_clock') else None,lights=len(atmosphere.get_editor_property('lights')),kitchen_light='AP_Light_Kitchen')
    report['preserved']['bedroom']='not targeted; no geometry or lighting writes outside kitchen'
    report['preserved']['bay']='not targeted'
    for row in targets:
        cid=str(row.get_editor_property('container_id'));initial=report['preserved']['original_container_contract'][cid]
        current=component_snapshot(row.door)
        for field in ['actor','caption','storage_pages','opening_duration','drawer_travel','opening_motion','opened_yaw','initial_open_fraction','hinge_location','hinge_rotation','hinge_parent']:
            if initial[field]!=({'actor':row.get_path_name(),'caption':str(row.get_editor_property('caption')),'storage_pages':row.get_editor_property('storage_pages'),'opening_duration':row.get_editor_property('opening_duration'),'drawer_travel':list(row.get_editor_property('drawer_travel').to_tuple()),'opening_motion':str(row.get_editor_property('opening_motion')),'opened_yaw':row.get_editor_property('opened_yaw'),'initial_open_fraction':row.get_editor_property('initial_open_fraction'),'hinge_location':list(row.door_hinge.relative_location.to_tuple()),'hinge_rotation':dict(pitch=row.door_hinge.relative_rotation.pitch,yaw=row.door_hinge.relative_rotation.yaw,roll=row.door_hinge.relative_rotation.roll),'hinge_parent':row.door_hinge.get_attach_parent().get_path_name() if row.door_hinge.get_attach_parent() else None}[field]):raise RuntimeError('Container contract changed '+cid+' '+field)
        if row.door.get_attach_parent()!=row.door_hinge:raise RuntimeError('Door parent changed '+cid)
        for field in ['collision_enabled','collision_profile','location','rotation','scale']:
            if initial['door'][field]!=current[field]:raise RuntimeError('Door component contract changed '+cid+' '+field)
        if not cid.startswith('Apartment.Kitchen_'):
            for field in ['mesh','collision_enabled','collision_profile','location','rotation','scale']:
                if initial['body'][field]!=component_snapshot(row.body)[field]:raise RuntimeError('Native fridge shell changed '+cid+' '+field)
    report['preserved']['contract_comparison']='identity, captions, pages, hinges, door collision/parent and native fridge shells unchanged'
    return report

def main():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:raise RuntimeError('Preserve unsaved maps: '+str([p.get_path_name() for p in dirty]))
    validate_assets()
    audit_path=R/'geometry-repair-v2.json'
    audit=json.loads(audit_path.read_text(encoding='utf8'))
    if audit.get('stage')!='local_layout_checked' or not audit.get('source_matches'):raise RuntimeError('Current local repair audit is incomplete')
    current_hash=hashlib.sha256((R/'KitchenDetailV1.blend').read_bytes()).hexdigest()
    if audit.get('source_sha256')!=current_hash:raise RuntimeError('Local repair audit does not match current source')
    report['local_geometry_audit']=dict(path=str(audit_path),sha256=hashlib.sha256(audit_path.read_bytes()).hexdigest(),source_sha256=audit['source_sha256'],note='Local mesh/support checks; not user visual acceptance')
    path=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap'
    backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup/path.name)
    report['backup']=str(backup/path.name);report['pre_map_sha256']=hashlib.sha256(path.read_bytes()).hexdigest();record()
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world or world.get_path_name()!=MAP+'.'+MAP.rsplit('/',1)[-1]:raise RuntimeError('Wrong apartment world; refusing map save')
    if editor and editor.get_game_world():raise RuntimeError('Preserve game world; loaded map is not editor state')
    install(world)
    # Preserve the corrective sink, oven and physical wiring on kitchen reinstallation.
    repair=PROJECT/'SourceAssets/CyberpunkKitchenRepair20261026'
    if (repair/'installed.json').exists():
        import runpy
        report['repair_20261026']=runpy.run_path(str(repair/'install_level.py'))['apply_upgrade'](world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Kitchen map save failed')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if digest==report['pre_map_sha256']:raise RuntimeError('Map save returned true but formal map hash did not change')
    report['stage']='map_saved';report['saved_at']=datetime.now().astimezone().isoformat();report['map_sha256']=digest;record();(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('KITCHEN_SCOPED_INSTALL_SAVED',len(report['updated']),len(report['added']))
if __name__=='__main__' or globals().get('__name__')=='__builtin__':
    try:main()
    except Exception:
        report['stage']='failed';report['error']=traceback.format_exc();record();raise
