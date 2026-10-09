"""Import scoped props and save only reception-owned changes in three maps."""
import unreal as u
import json,runpy,shutil,re,traceback,itertools,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
P=runpy.run_path(str(ROOT/'layout.py'));BASE=P['BASE'];OWNER='Reception.UpperProps20261007'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
MAPS=['/Game/GameMaps/Design/L_ReceptionHall_Subject','/Game/GameMaps/Design/L_FacilityTransit_Subject','/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject']
commandlet='-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
report=dict(stage='preparing',saved_assets=[],maps=[],game_run=False,rendered=False,inspection_scope='Reception second-floor prop placement')
cfg=json.loads((PARENT/'Config/layout.json').read_text('utf8'));newcfg=P['revise'](cfg)
oldparts={p['id']:p for p in cfg['parts']};newparts={p['id']:p for p in newcfg['parts']}
geometry=json.loads((ROOT/'geometry.json').read_text('utf8'))
snapshot=ROOT/'Snapshots'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S');snapshot.mkdir(parents=True)
for rel in ['Config/layout.json','manifest.json','Config/module-draft.json']:
    source=PARENT/rel
    if source.exists():shutil.copy2(source,snapshot/source.name)

def record():
    (ROOT/'Receipts').mkdir(exist_ok=True)
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Missing required asset '+path)
    return a
def owned(path):
    if not E.does_asset_exist(path):return None
    a=asset(path)
    if E.get_metadata_tag(a,'Reception.Owner')!=OWNER:raise RuntimeError('Preserve unowned target '+path)
    return a
def save(a):
    E.set_metadata_tag(a,'Reception.Owner',OWNER)
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    report['saved_assets'].append(a.get_path_name());record();return a
def guard():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if not commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve running editor')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved map')
    if any(p.get_name().startswith(BASE+'/') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved prop assets')
def import_mesh(item):
    m=owned(item['mesh'])
    if m:
        if E.get_metadata_tag(m,'Reception.SourceSHA256')!=item['sha256']:raise RuntimeError('Saved mesh differs from source; use a fresh variant')
        return m
    t=u.AssetImportTask();t.filename=item['fbx'];t.destination_path,t.destination_name=item['mesh'].rsplit('/',1);t.automated=True;t.save=False;t.replace_existing=False;t.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False;opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.one_convex_hull_per_ucx=True
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    t.options=opt;A.import_asset_tasks([t]);m=asset(item['mesh'])
    for i,s in enumerate(m.get_editor_property('static_materials')):
        key=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));m.set_material(i,asset(item['materials'][key]))
    build=SM.get_lod_build_settings(m,0);build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True);SM.set_lod_build_settings(m,0,build)
    m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
    ns=m.get_editor_property('nanite_settings').copy();ns.enabled=True;ns.explicit_tangents=True;m.set_editor_property('nanite_settings',ns)
    if not u.PlazaInstanceTools.build_nanite_data(m):raise RuntimeError('Nanite build failed '+item['mesh'])
    E.set_metadata_tag(m,'Reception.SourceSHA256',item['sha256']);return save(m)
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
def transform(p):return u.Transform(location=vec(p['position_m']),rotation=u.Rotator(pitch=0,yaw=-p['yaw_deg'],roll=0),scale=u.Vector(*p['scale']) if isinstance(p['scale'],list) else u.Vector(p['scale'],p['scale'],p['scale']))
def close(a,b):return max(abs(getattr(a,k)-getattr(b,k)) for k in ('x','y','z'))<.5
def meshpath(c):return c.static_mesh.get_path_name().split('.')[0] if c.static_mesh else ''
def bounds(c,t):
    b=c.static_mesh.get_bounds()
    pts=[u.MathLibrary.transform_location(t,u.Vector(b.origin.x+sx*b.box_extent.x,b.origin.y+sy*b.box_extent.y,b.origin.z+sz*b.box_extent.z)) for sx,sy,sz in itertools.product((-1,1),repeat=3)]
    return [[round(f(getattr(p,k) for p in pts)/100,5) for k in ('x','y','z')] for f in (min,max)]

def patch(path):
    guard();disk=PROJECT/'Content'/(path.removeprefix('/Game/')+'.umap');shutil.copy2(disk,snapshot/disk.name)
    world=u.EditorLoadingAndSavingUtils.load_map(path)
    if not world:raise RuntimeError('Cannot load '+path)
    actors=[a for a in AA.get_all_level_actors() if a.get_actor_label().startswith('Reception_')];labels={a.get_actor_label():a for a in actors}
    comps=[(a,c) for a in actors for c in a.get_components_by_class(u.StaticMeshComponent) if c.static_mesh]
    oldbase='/Game/Dungeons/ReceptionHall20261006/Meshes/SM_Reception_'
    replacements={oldbase+i['kind']:i['mesh'] for i in geometry['meshes']}
    targets={i['mesh'] for i in geometry['meshes']};operations=[];removed=[]
    # Resolve every placement before modifying this map. Instance positions are
    # matched, so subsequent source edits cannot silently change an index.
    for i in range(6,10):
        id='PlanterPlant'+str(i);a=labels.get('Reception_'+id)
        if not a:raise RuntimeError('Missing '+id+' in '+path)
        operations.append(('actor',id,a,a.static_mesh_component,None))
    for id in ['UpperBench_-1_3','UpperBench_1_3','OfficePaper_-1_0','OfficePaper_-1_1','OfficePaper_1_0','OfficePaper_1_1']:
        old,new=oldparts[id],newparts[id];matches=[]
        for a,c in comps:
            if meshpath(c) not in (old['mesh'],new['mesh']) or not isinstance(c,u.InstancedStaticMeshComponent):continue
            for i in range(c.get_instance_count()):
                loc=c.get_instance_transform(i,True).translation
                if close(loc,vec(old['position_m'])) or close(loc,vec(new['position_m'])):matches.append((a,c,i))
        if len(matches)!=1:raise RuntimeError('Expected one instance for '+id+' got '+str(len(matches)))
        a,c,i=matches[0];operations.append(('instance',id,a,c,i))
    found={meshpath(c) for a,c in comps}
    for old,new in replacements.items():
        if old not in found and new not in found:raise RuntimeError('Missing source geometry '+old)
    changed=[]
    for a,c in comps:
        mp=meshpath(c)
        if mp==oldbase+'WasteBinTrim':
            if a not in removed:
                if not AA.destroy_actor(a):raise RuntimeError('Unable to remove obsolete waste-bin trim')
                removed.append(a)
            continue
        if mp in replacements:
            a.modify();c.modify();c.set_static_mesh(asset(replacements[mp]));c.set_editor_property('override_materials',[]);changed.append(a.get_actor_label())
    inspected=[]
    for kind,id,a,c,i in operations:
        a.modify();c.modify();p=newparts[id];t=transform(p)
        if kind=='actor':
            c.set_static_mesh(asset(p['mesh']));c.set_editor_property('override_materials',[]);a.set_actor_transform(t,False,True)
            actual=c.get_world_transform()
        else:
            if not c.update_instance_transform(i,t,world_space=True,mark_render_state_dirty=True,teleport=True):raise RuntimeError('Instance move failed '+id)
            actual=c.get_instance_transform(i,True)
        lo,hi=bounds(c,actual)
        if id.startswith('PlanterPlant') and (lo[1]<-16.48 or hi[1]>16.48):raise RuntimeError('Foliage beyond wall '+id+' '+str([lo,hi]))
        if id.startswith('OfficePaper') and abs(lo[2]-5.276)>.005:raise RuntimeError('Paper not on desktop '+id+' '+str([lo,hi])+' '+str(actual))
        inspected.append(dict(id=id,mesh=meshpath(c),bounds_m=[lo,hi],instance=i));changed.append(id)
    E.set_metadata_tag(world,OWNER,'saved')
    if not u.EditorLoadingAndSavingUtils.save_map(world,path):raise RuntimeError('Map save failed '+path)
    report['maps'].append(dict(map=path,saved=True,changed=changed,obsolete_trim_removed=len(removed),upper_placements=inspected));record()
    print('UPPER_PROPS_MAP_SAVED',path,len(changed),flush=True)

try:
    guard()
    report['materials']=runpy.run_path(str(ROOT/'materials.py'))['author'](BASE,owned,asset,save)
    for item in geometry['meshes']:import_mesh(item)
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);previous=editor.get_editor_world();previous=previous.get_path_name().split('.')[0] if previous else None
    for path in MAPS:patch(path)
    P['source_sync']();report['stage']='maps_saved';report['source_references_saved']=True;report['snapshot']=str(snapshot);record()
    if not commandlet and previous:u.EditorLoadingAndSavingUtils.load_map(previous)
    print('RECEPTION_UPPER_PROPS_SAVED',len(report['maps']),flush=True)
except Exception:
    report['error']=traceback.format_exc();record();raise
