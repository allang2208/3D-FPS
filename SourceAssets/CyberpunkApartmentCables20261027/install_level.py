"""Import and save the apartment-wide cable assembly in the existing map only."""
from pathlib import Path
from datetime import datetime
import json,runpy,hashlib,shutil,re
import unreal as u
R=Path(__file__).resolve().parent;P=R.parents[1]
BASE='/Game/Props/CyberpunkApartmentCables20261027';MAP='/Game/GameMaps/L_CyberpunkApartment'
KITCHEN='/Game/Props/CyberpunkApartmentKitchen20261024'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
G=json.loads((R/'geometry.json').read_text());SOURCE=json.loads((R/'scene_inputs.json').read_text())
INPUTS={a['actor']:a for a in SOURCE['actors']};ROUTING=runpy.run_path(str(R/'layout.py'))
TAG='ApartmentCables20261027'

def load(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Required asset missing: '+path)
    return a

def save(a):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Asset save failed: '+a.get_path_name())

def slotname(n):return re.sub(r'[._]\d{3}$','',str(n))

def box(center,size):
    q=u.KBoxElem();q.set_editor_property('center',u.Vector(*center))
    for axis,v in zip(['x','y','z'],size):q.set_editor_property(axis,v)
    return q

def import_assets():
    report=json.loads((R/'assets_saved.json').read_text()) if (R/'assets_saved.json').exists() else dict(meshes={})
    for row in G['meshes']:
        key=row['key'];dest=BASE+'/Meshes/SM_AC_'+key;digest=hashlib.sha256(Path(row['fbx']).read_bytes()).hexdigest()
        if report['meshes'].get(key,{}).get('hash')==digest and E.does_asset_exist(dest):continue
        source=load(INPUTS[row['source_actor']]['components'][0]['mesh']) if row['source_actor'] else None
        lookup={slotname(s.material_slot_name):s.material_interface for s in source.get_editor_property('static_materials')} if source else {}
        t=u.AssetImportTask();t.filename=row['fbx'];t.destination_path=BASE+'/Meshes';t.destination_name='SM_AC_'+key
        t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=False;t.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.import_as_skeletal=False
        d=opt.static_mesh_import_data
        for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=True,import_uniform_scale=1.).items():d.set_editor_property(k,v)
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;t.options=opt;AT.import_asset_tasks([t])
        if not t.imported_object_paths:raise RuntimeError('No imported mesh: '+key)
        mesh=load(dest)
        bs=SM.get_lod_build_settings(mesh,0)
        for k,v in dict(use_full_precision_u_vs=True,use_high_precision_tangent_basis=True,recompute_tangents=True,recompute_normals=False).items():bs.set_editor_property(k,v)
        SM.set_lod_build_settings(mesh,0,bs)
        for i,s in enumerate(mesh.get_editor_property('static_materials')):
            name=slotname(s.material_slot_name)
            if source:
                mat=lookup.get(name)
                if not mat:raise RuntimeError('Source material slot missing: '+key+' / '+name+' / '+str(list(lookup)))
            else:mat=load(KITCHEN+'/Materials/M_KP_'+name.removeprefix('KP_'))
            mesh.set_material(i,mat)
        body=mesh.get_editor_property('body_setup');body.modify()
        if source:
            src_body=source.get_editor_property('body_setup')
            if src_body:
                body.set_editor_property('agg_geom',src_body.get_editor_property('agg_geom'))
                body.set_editor_property('collision_trace_flag',src_body.get_editor_property('collision_trace_flag'))
        agg=body.get_editor_property('agg_geom');b=list(agg.get_editor_property('box_elems'))
        if key in ('WritingDesk','CyberWorkstation'):
            # A 0.4 mm margin supports the actual tabletop, without filling the
            # free space below the desk or changing drawer collision.
            width,depth=(165.,68.) if key=='WritingDesk' else (230.,80.)
            b.append(box((0,0,77.0),(width+.08,depth+.08,4.58)))
        elif key.endswith('DeskRouting'):
            half=40. if key.startswith('Office') else 34.
            b.extend([box((-25,-half-1.3,69),(38,4.4,3.8)),box((-25,-half-1.8,65),(42,5.4,2.0))])
        elif key=='DeskCableTray':b.append(box((-25,-27,65),(78,8,2.5)))
        if b:
            agg.set_editor_property('box_elems',b);body.set_editor_property('agg_geom',agg)
            body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX)
        save(mesh)
        report['meshes'][key]=dict(path=dest,hash=digest,removed_cable_faces=row['removed_cable_faces'],triangles=row['triangles'])
        report['stage']='assets_saving';(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
        print('APARTMENT_CABLE_ASSET_SAVED',key,flush=True)
    report['stage']='assets_saved';(R/'assets_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    return report

def comp(actor,name=None):
    if name:return next(c for c in actor.get_components_by_class(u.StaticMeshComponent) if c.get_name()==name)
    return actor.static_mesh_component

def apply_upgrade(world):
    actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
    replaced=[];hardware=[];cables=[]
    # Keep actor identities, material overrides, transforms, native drawers and
    # controls. Only swap the six source meshes that contain retired wire islands.
    for label,key in G['replacements']:
        a=actors[label];c=a.static_mesh_component;old=c.static_mesh
        mats={slotname(s.material_slot_name):c.get_material(i) for i,s in enumerate(old.get_editor_property('static_materials'))}
        new=load(BASE+'/Meshes/SM_AC_'+key);a.modify();c.modify();c.set_static_mesh(new)
        c.set_editor_property('override_materials',[])
        for i,s in enumerate(new.get_editor_property('static_materials')):
            mat=mats.get(slotname(s.material_slot_name))
            if mat:c.set_material(i,mat)
        if key in ('WritingDesk','CyberWorkstation','DeskCableTray'):
            c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS)
        replaced.append(dict(actor=label,mesh=new.get_path_name()))
    for row in G['hardware']:
        label='AC_Hardware_'+row['key']+('_'+row['parent'] if row['parent'] else '')
        a=actors.get(label)
        if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label);actors[label]=a
        a.modify();c=a.static_mesh_component;c.set_static_mesh(load(BASE+'/Meshes/SM_AC_'+row['key']))
        if row['parent']:
            parent=actors[row['parent']];t=comp(parent,row.get('component')).get_world_transform()
            a.set_actor_transform(t,False,False)
            a.attach_to_actor(parent,'',u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
        else:a.set_actor_transform(u.Transform(location=u.Vector(),rotation=u.Rotator(),scale=u.Vector(1,1,1)),False,False)
        c.set_collision_profile_name('BlockAll')
        c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY if row['key'].endswith('DeskRouting') else u.CollisionEnabled.NO_COLLISION)
        a.set_folder_path('Apartment/Cables');a.tags=[TAG];hardware.append(label)
    world_anchor=actors['AC_Hardware_WorldTerminals']
    def anchor(spec):
        if not spec['actor']:return u.Vector(*spec['p']),world_anchor,world_anchor.static_mesh_component,'StaticMeshComponent'
        a=actors[spec['actor']];c=comp(a,spec.get('component'));p=spec['p']
        pt=c.get_world_transform().transform_location(u.Vector(p[0]*100,-p[1]*100,p[2]*100))
        return pt,a,c,('Body' if spec.get('component')=='Body' else 'StaticMeshComponent')
    for row in G['routes']:
        label='AC_Cable_'+row['name'];start,parent,_,_=anchor(row['start']);end,target,tc,property_name=anchor(row['end'])
        a=actors.get(label)
        if not a:a=AA.spawn_actor_from_class(u.CableActor,start);a.set_actor_label(label);actors[label]=a
        a.modify();a.set_actor_transform(u.Transform(location=start,rotation=u.Rotator(),scale=u.Vector(1,1,1)),False,False)
        a.attach_to_actor(parent,'',u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
        a.set_actor_scale3d(u.Vector(1,1,1));c=a.cable_component;c.modify()
        for k,v in dict(ROUTING['PARAMETERS'],attach_start=True,attach_end=True,cable_length=row['length_cm'],num_segments=row['segments'],cable_width=row['width_cm']).items():c.set_editor_property(k,v)
        c.set_attach_end_to(target,property_name)
        c.set_editor_property('end_location',tc.get_world_transform().inverse_transform_location(end))
        c.set_collision_profile_name('BlockAllDynamic');c.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
        c.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_IGNORE)
        c.set_material(0,load(KITCHEN+'/Materials/M_KP_Rubber'));c.set_cull_distance(2400)
        a.set_folder_path('Apartment/Cables');a.tags=[TAG]
        cables.append(dict(actor=label,start=list(start.to_tuple()),end=list(end.to_tuple()),length_cm=row['length_cm'],segments=row['segments'],width_cm=row['width_cm'],start_parent=parent.get_actor_label(),end_parent=target.get_actor_label()))
    return dict(replaced=replaced,hardware=hardware,cables=cables,kitchen_spans_preserved=['KR_Cable_Coffee','KR_Cable_CoffeeCounter','KR_Cable_Kettle'],runtime_tested=False)

def main():
    assets=import_assets()
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
    if not world:raise RuntimeError('Cannot load formal apartment')
    backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
    path=P/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(path,backup/path.name)
    result=apply_upgrade(world)
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Apartment save failed')
    result.update(stage='map_saved',map=MAP,backup=str(backup/path.name),saved_at=datetime.now().astimezone().isoformat(),game_run=False,interactive_editor_started=False)
    (R/'installed.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print('APARTMENT_PHYSICAL_CABLES_SAVED',len(result['cables']),len(result['replaced']),flush=True)

if __name__=='__main__':main()
