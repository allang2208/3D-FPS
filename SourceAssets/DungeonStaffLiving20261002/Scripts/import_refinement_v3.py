"""Import compiled V3 assets and replace only their authored sample-map parts."""
import hashlib,json,re,shutil,sys
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'RefinementV3'
BASE='/Game/Dungeons/StaffLiving20261002/RefinementV3'
CFG=json.loads((OUT/'Authored/room-refined.json').read_text('utf8'))
current=json.loads((ROOT/'Config/room.json').read_text('utf8'))
if current.get('layout_revision',0)>=4:
    intact=ROOT/'Scripts/import_intact_tiles_v4.py'
    exec(compile(intact.read_text('utf8'),str(intact),'exec'))
    raise SystemExit(0)
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'))
ORIGINAL=json.loads((ROOT/'Config/room.json').read_text('utf8'))
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ML=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},saved_assets=[],stage='started')
report.update(revision=CFG['revision'],tests_run=False,rendered=False,game_run=False,editor_opened=False,random_pool_registered=False)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    if not asset.get_path_name().startswith(BASE+'/'):raise RuntimeError('Save outside owned refinement namespace')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved_assets']:report['saved_assets'].append(asset.get_path_name())
    record()

sys.path.insert(0,str(ROOT/'Scripts'))
from build_refinement_materials_v3 import build_materials
build_materials(report,record);report['stage']='materials_saved';record()
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
meshes={};prototypes={};structures={}
for item in MAN['objects']:
    name=item['name'];path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    mesh=u.load_asset(path)
    previous=report['meshes'].get(name)
    if mesh and previous and previous.get('source_sha256')!=digest:
        raise RuntimeError('Preserve already-saved different refinement source '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.one_convex_hull_per_ucx=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+path)
        slots=list(mesh.get_editor_property('static_materials'))
        for index,slot in enumerate(slots):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
            material=u.load_asset(item['materials'][key])
            if not material:raise RuntimeError('Missing material '+item['materials'][key])
            mesh.set_material(index,material)
        # Edit supported fields in the struct reference; UVChannelData itself
        # is read-only in this engine. Re-read slots after all material binding.
        slots=list(mesh.get_editor_property('static_materials'))
        for slot in slots:
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
            density=90. if key=='RS_Carpet' else 160. if key=='RS_Notices' else 42. if key in ('RS_Linen','RS_Terry','RS_Hem') else None
            if density:
                info=slot.get_editor_property('uv_channel_data');info.set_editor_property('override_densities',True)
                info.set_editor_property('local_uv_densities',[density]*4)
        mesh.set_editor_property('static_materials',slots)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
            u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if item['simple_collision_hulls'] else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True
        n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        n.fallback_percent_triangles=1.;n.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',n)
        if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
        save(mesh)
    report['meshes'][name]=dict(path=path,source_sha256=digest,source_triangles=item['triangles'],
        collision=item['collision'],nanite=item['nanite'],simple_collision_hulls=item['simple_collision_hulls'])
    meshes[name]=mesh
    if item['prototype']:prototypes[item['prototype']]=(mesh,item)
    else:structures.setdefault(item['room_id'],[]).append((mesh,item))
    record();u.log('STAFF_REFINEMENT_MESH_SAVED '+name)
report['stage']='assets_saved';record()

AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def loc(p,offset):return u.Vector((p[0]+offset[0])*100,-(p[1]+offset[1])*100,(p[2]+offset[2])*100)
def owned(a,label,rid):
    a.set_actor_label('StaffSubject_'+label);a.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(rid)])
    a.set_folder_path('StaffLiving/'+rid);return a
def static(mesh,item,p,offset,label,rid,yaw=0):
    a=owned(AA.spawn_actor_from_class(u.StaticMeshActor,loc(p,offset),u.Rotator(pitch=0,yaw=-yaw,roll=0)),label,rid)
    c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
    c.set_editor_property('cast_shadow',item['kind']!='WetGrout')
    return a

backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True,exist_ok=True);report.setdefault('backups',[])
def replace_room(room,offset):
    rid=room['id'];oldroom=next(r for r in ORIGINAL['rooms'] if r['id']==rid)
    affected=[p for p in oldroom['furniture'] if p['prototype'] in prototypes or p['prototype']=='BunkBed']
    labels={'StaffSubject_'+rid+'_'+p['id'] for p in affected}
    labels.update('StaffSubject_'+rid+'_'+p['prototype']+'_Instances' for p in affected)
    labels.update('StaffSubject_'+rid+'_'+p['prototype']+'_Instances' for p in room['furniture'] if p['prototype'] in prototypes)
    for mesh,item in structures.get(rid,[]):labels.add('StaffSubject_'+rid+'_'+item['kind'])
    for actor in list(AA.get_all_level_actors()):
        if actor.get_actor_label() in labels and 'StaffLiving.Subject' in [str(t) for t in actor.tags]:AA.destroy_actor(actor)
    for mesh,item in structures.get(rid,[]):static(mesh,item,[0,0,0],offset,rid+'_'+item['kind'],rid)
    groups={}
    for p in room['furniture']:
        if p['prototype'] not in prototypes:continue
        mesh,item=prototypes[p['prototype']]
        a=static(mesh,item,p['position'],offset,rid+'_'+p['id'],rid,p['yaw_blender_deg'])
        if item['nanite']:groups.setdefault(p['prototype'],[]).append(a)
    for key,actors in groups.items():
        if len(actors)<2:continue
        # The shared construction helper admits explicitly owned authoring
        # actors. This temporary tag is removed from the saved staff cluster.
        for a in actors:a.set_editor_property('tags',list(a.tags)+[u.Name('ColdSteel.MainPlaza.Generated')])
        cluster=u.PlazaInstanceTools.create_plaza_cluster(actors,'StaffSubject_'+rid+'_'+key+'_Instances')
        if not cluster:
            # Loaded meshes may still be waiting for their derived data. Finish
            # that production build before the helper copies the components.
            if not u.PlazaInstanceTools.build_nanite_data(prototypes[key][0]):raise RuntimeError('Instance mesh build failed '+key)
            cluster=u.PlazaInstanceTools.create_plaza_cluster(actors,'StaffSubject_'+rid+'_'+key+'_Instances')
        if not cluster:raise RuntimeError('Cannot save furniture cluster '+key)
        owned(cluster,rid+'_'+key+'_Instances',rid)
        for a in actors:AA.destroy_actor(a)

targets=[(CFG['maps'][r['id']],[r],[[0,0,0]],False) for r in CFG['rooms']]
targets.append((CFG['sample_map'],CFG['rooms'],CFG['preview_placements_m'],True))
for target,rooms,offsets,combined in targets:
    if report['maps'].get(target,{}).get('layout_revision')==3:continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap')
    dst=backup/(disk.name)
    if not disk.exists():raise RuntimeError('Original sample missing '+target)
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst),sha256=hashlib.sha256(dst.read_bytes()).hexdigest()));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load sample '+target)
    for room,offset in zip(rooms,offsets):replace_room(room,offset)
    if combined:
        for offset in ([16,0,0],[48,0,0]):
            label='Link_'+str(offset[0])+'_CarpetV3'
            for a in list(AA.get_all_level_actors()):
                if a.get_actor_label()=='StaffSubject_'+label:AA.destroy_actor(a)
            for mesh,item in structures['Link']:static(mesh,item,[0,0,0],offset,label,'Links')
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Cannot save sample '+target)
    report['maps'][target]=dict(stage='map_saved',layout_revision=3,sequence=[r['id'] for r in rooms]);record()
    u.log('STAFF_REFINEMENT_MAP_SAVED '+target)

# Carry the same asset choices and authored transforms into the draft modules.
draft=json.loads((ROOT/'Config/modules-draft.json').read_text('utf8'))
oldmesh_to_new={name.rsplit('/',1)[-1]:item['asset'] for item in MAN['objects']
    for name in [item['name'].removesuffix('_V3')] if not item['prototype']}
for module in draft['modules']:
    room=next(r for r in CFG['rooms'] if r['id']==module['id'])
    byid={p['id']:p for p in room['furniture']}
    for part in module['parts']:
        if part.get('id') in byid and byid[part['id']]['prototype'] in prototypes:
            p=byid[part['id']];item=prototypes[p['prototype']][1]
            part['mesh']=item['asset'];x,y,z=p['position'];part['position']=[x*100,-y*100,z*100]
            part['yaw']=-p['yaw_blender_deg'];part['collision']=item['collision']
        elif part['mesh'].rsplit('/',1)[-1] in oldmesh_to_new:
            part['mesh']=oldmesh_to_new[part['mesh'].rsplit('/',1)[-1]]
    services=next((item for mesh,item in structures.get(module['id'],[]) if item['kind']=='WaterServices'),None)
    if services and not any(p['mesh']==services['asset'] for p in module['parts']):
        module['parts'].append(dict(mesh=services['asset'],position=[0,0,0],yaw=0,collision=False,materials=[]))
    module['refinement_revision']=3
(OUT/'modules-refined.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
# Install the authoring configuration only after all four maps are saved.
for src,dst in [(OUT/'Authored/room-refined.json',ROOT/'Config/room.json'),(OUT/'modules-refined.json',ROOT/'Config/modules-draft.json')]:
    shutil.copy2(dst,backup/dst.name);shutil.copy2(src,dst)
report.update(stage='samples_saved',furniture_variants=4,drain_wells=6,console_command='open '+CFG['sample_map'])
record();u.log('STAFF_REFINEMENT_V3_DELIVERY_SAVED')
