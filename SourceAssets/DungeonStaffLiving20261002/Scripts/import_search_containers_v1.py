"""Save the searchable lockers into the existing staff sample maps.
Only owned locker placements and one dedicated outline volume per map change.
"""
import hashlib,json,re,shutil,sys
from pathlib import Path
from datetime import datetime
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'SearchContainersV1'
CFG=json.loads((ROOT/'Config/room.json').read_text('utf8'))
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'))
BASE=CFG['ue_base']+'/SearchContainersV1'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},backups=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False,rewards_deferred=True)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
meshes={}
for item in MAN['objects']:
    path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    mesh=u.load_asset(path)
    if mesh and report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:
        raise RuntimeError('Preserve different existing cabinet asset '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Cabinet mesh import failed '+path)
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
            if not material:raise RuntimeError('Missing existing cabinet finish '+item['materials'][key])
            mesh.set_material(index,material)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True
        nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',nanite)
        if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Cabinet production build failed '+path)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cabinet mesh save failed '+path)
    report['meshes'][item['name']]=dict(path=path,source_sha256=digest,triangles=item['triangles'],hulls=item['simple_collision_hulls'])
    meshes[item['name']]=mesh;record()
sys.path.insert(0,str(ROOT/'Scripts'))
from build_container_outline_v1 import build_outline
outline=build_outline(ROOT,BASE)
report.update(stage='assets_saved',outline=outline.get_path_name(),native_class=MAN['actor_class']);record()
actor_class=u.load_class(None,MAN['actor_class'])
if not actor_class:raise RuntimeError('Native scene-container build must finish before map integration')
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
rooms={r['id']:r for r in CFG['rooms']}
offsets=dict(zip(rooms,CFG['preview_placements_m']))
locker_rooms=list(dict.fromkeys(p['room_id'] for p in MAN['containers']))
targets=[(CFG['maps'][rid],[rid],False) for rid in locker_rooms]
targets.append((CFG['sample_map'],locker_rooms,True))
for target,rids,combined in targets:
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load staff sample '+target)
    placements=[p for p in MAN['containers'] if p['room_id'] in rids]
    labels={'StaffSubject_'+p['room_id']+'_'+p['part_id'] for p in placements}
    cluster_labels={'StaffSubject_'+rid+'_'+prototype+'_Instances' for rid in rids for prototype in ('Locker','LockerOpen')}
    existing={}
    for actor in AA.get_all_level_actors():
        label=actor.get_actor_label()
        if 'StaffLiving.Subject' not in [str(t) for t in actor.tags]:continue
        if label in labels and isinstance(actor,u.ColdSteelSceneContainer):existing[label]=actor;continue
        if label in labels or label in cluster_labels:
            # Targeted migration of V1 static placements, including any original ISM clusters.
            AA.destroy_actor(actor)
    created=[]
    for p in placements:
        rid=p['room_id'];off=offsets[rid] if combined else [0,0,0];loc=p['position']
        label='StaffSubject_'+rid+'_'+p['part_id']
        actor=existing.get(label)
        if not actor:actor=AA.spawn_actor_from_class(actor_class,u.Vector((loc[0]+off[0])*100,-(loc[1]+off[1])*100,(loc[2]+off[2])*100),
            u.Rotator(pitch=0,yaw=-p['yaw_blender_deg'],roll=0))
        if not actor:raise RuntimeError('Container placement failed '+label)
        actor.set_actor_label(label);actor.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(rid),u.Name('ColdSteel.SceneContainer')])
        actor.set_folder_path('StaffLiving/'+rid+'/SearchContainers')
        actor.set_editor_property('container_id',p['container_id']);actor.set_editor_property('caption','员工储物柜')
        actor.set_editor_property('storage_pages',1);actor.set_editor_property('opened_yaw',100.)
        actor.body.set_static_mesh(meshes['SM_Staff_SearchLockerBody_V1'])
        actor.door.set_static_mesh(meshes['SM_Staff_SearchLockerDoor_V1'])
        actor.door_hinge.set_relative_location(u.Vector(-29,28.4,0),False,False)
        for component in (actor.body,actor.door):
            component.set_render_custom_depth(True);component.set_custom_depth_stencil_value(201)
        created.append(dict(label=label,container_id=p['container_id']))
    pp_label='StaffSubject_ContainerOutline_V1'
    pp=next((a for a in AA.get_all_level_actors() if a.get_actor_label()==pp_label and 'StaffLiving.Subject' in [str(t) for t in a.tags]),None)
    if not pp:pp=AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
    pp.set_actor_label(pp_label);pp.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name('ColdSteel.SceneContainer.Outline')])
    pp.set_folder_path('StaffLiving/Environment');pp.set_editor_property('unbound',True)
    pp.set_editor_property('priority',1.);settings=pp.get_editor_property('settings')
    blend=u.WeightedBlendable();blend.set_editor_property('weight',1.);blend.set_editor_property('object',outline)
    blends=u.WeightedBlendables();blends.set_editor_property('array',[blend]);settings.set_editor_property('weighted_blendables',blends)
    pp.set_editor_property('settings',settings)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Container map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',containers=created,outline_volume=pp_label);record()
    u.log('STAFF_SEARCH_CONTAINER_MAP_SAVED '+target+' '+str(len(created)))

# Draft modules keep actor descriptors separately from static parts. They are not
# registered in the production dungeon pool by this sample-scene author.
draft_path=ROOT/'Config/modules-draft.json'
draft=json.loads(draft_path.read_text('utf8'))
shutil.copy2(draft_path,backup/'modules-draft.json')
for module in draft['modules']:
    module['parts']=[p for p in module['parts'] if p.get('mesh','').rsplit('/',1)[-1] not in ('SM_Staff_Locker','SM_Staff_LockerOpen')]
    containers=[]
    for p in MAN['containers']:
        if p['room_id']!=module['id']:continue
        containers.append(dict(actor_class=MAN['actor_class'],container_id=p['container_id'],body=p['body'],door=p['door'],
            position=[p['position'][0]*100,-p['position'][1]*100,p['position'][2]*100],yaw=-p['yaw_blender_deg'],
            hinge=p['hinge_cm'],opened_yaw=100,storage_pages=1))
    module['scene_containers']=containers
draft['container_interaction_revision']=1
draft['container_outline']=outline.get_path_name()
draft_path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
shutil.copy2(ROOT/'Config/room.json',backup/'room.json')
CFG['container_interaction_revision']=1
CFG['container_actor_class']=MAN['actor_class']
CFG['current_authored_source']='SearchContainersV1/Authored/StaffLivingTheme_SearchContainersV1.blend'
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',unique_containers=36,random_pool_registered=False,
    open_command='open '+CFG['sample_map']);record()
u.log('STAFF_SEARCH_CONTAINERS_DELIVERY_SAVED')
