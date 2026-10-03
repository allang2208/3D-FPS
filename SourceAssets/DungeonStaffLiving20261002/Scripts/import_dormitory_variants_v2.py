"""Install authored furniture, two sample maps and one event-driven layout selector."""
import json,hashlib,re,shutil
from pathlib import Path
from datetime import datetime
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'DormitoryVariantsV2'
CFG=json.loads((ROOT/'Config/room.json').read_text('utf8'))
if CFG.get('container_open_parts_revision',0)>=3:
    current=ROOT/'Scripts/import_container_open_parts_v3.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'));BASE=CFG['ue_base']+'/DormitoryVariantsV2'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ML=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},backups=[],materials=[])
report.update(tests_run=False,game_run=False,rendered=False,editor_opened=False,rewards_deferred=True)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')

for name,color,roughness in [('BookPaper',(.70,.66,.49),.91),('BookGreen',(.09,.16,.115),.76),
    ('BookBlue',(.055,.10,.17),.70),('BookRed',(.23,.067,.04),.73)]:
    path=BASE+'/Materials/M_Dorm_'+name;mat=u.load_asset(path)
    if not mat:
        folder,asset_name=path.rsplit('/',1);E.make_directory(folder)
        mat=AT.create_asset(asset_name,folder,u.Material,u.MaterialFactoryNew())
        mat.set_editor_property('used_with_nanite',True)
        node=ML.create_material_expression(mat,u.MaterialExpressionConstant3Vector,-300,0)
        node.set_editor_property('constant',u.LinearColor(*color,1.));ML.connect_material_property(node,'',u.MaterialProperty.MP_BASE_COLOR)
        node=ML.create_material_expression(mat,u.MaterialExpressionConstant,-300,140)
        node.set_editor_property('r',roughness);ML.connect_material_property(node,'',u.MaterialProperty.MP_ROUGHNESS)
        errors=ML.recompile_material(mat)
        if errors:raise RuntimeError('Book material build failed '+str(errors))
        ML.get_statistics(mat)
        if not E.save_loaded_asset(mat,False):raise RuntimeError('Book material save failed '+path)
    if path not in report['materials']:report['materials'].append(path)
record()

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
meshes={}
for item in MAN['objects']:
    path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest();mesh=u.load_asset(path)
    if mesh and report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:
        raise RuntimeError('Preserve different existing furniture asset '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Furniture mesh import failed '+path)
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
            if not material:raise RuntimeError('Missing furniture finish '+item['materials'][key])
            mesh.set_material(index,material)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True
        nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',nanite)
        if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Furniture production build failed '+path)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Furniture mesh save failed '+path)
    meshes[path]=mesh;report['meshes'][item['name']]=dict(path=path,source_sha256=digest,triangles=item['triangles']);record()
report['stage']='assets_saved';record()

container_class=u.load_class(None,'/Script/FPSGAME.ColdSteelSceneContainer')
layout_class=u.load_class(None,'/Script/FPSGAME.StaffDormitoryLayout')
if not container_class or not layout_class:raise RuntimeError('Native furniture build required')
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
specs={c['id']:c for c in MAN['containers']};poses=MAN['preview_placements']
def load_mesh(path):
    if path not in meshes:meshes[path]=u.load_asset(path)
    if not meshes[path]:raise RuntimeError('Missing shared furniture '+path)
    return meshes[path]
def movable(actor):
    actor.get_editor_property('root_component').set_mobility(u.ComponentMobility.MOVABLE)
    if isinstance(actor,u.ColdSteelSceneContainer):actor.body.set_mobility(u.ComponentMobility.MOVABLE)
    elif isinstance(actor,u.StaticMeshActor):actor.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
def owned(actor,label,slot):
    actor.set_actor_label(label)
    tags=[str(t) for t in actor.tags if not str(t).startswith('StaffDormitory.LayoutSlot.')]
    for t in ['StaffLiving.Subject','StaffDormitory','StaffDormitory.LayoutSlot.'+slot]:
        if t not in tags:tags.append(t)
    actor.set_editor_property('tags',[u.Name(t) for t in tags]);actor.set_folder_path('StaffLiving/StaffDormitory/VariableFurniture')

for target in (CFG['maps']['StaffDormitory'],CFG['sample_map']):
    if report['maps'].get(target,{}).get('stage')=='map_saved':continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst)));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load staff sample '+target)
    actors={a.get_actor_label():a for a in AA.get_all_level_actors() if 'StaffLiving.Subject' in [str(t) for t in a.tags]}
    for prototype in ('Desk','Chair'):
        name='StaffSubject_StaffDormitory_'+prototype+'_Instances'
        if name in actors:AA.destroy_actor(actors.pop(name))
    layout_actors=[];container_records=[]
    for p in poses:
        label='StaffSubject_StaffDormitory_'+p['id'];kind=p['prototype']
        a=actors.get(label)
        loc=u.Vector(*p['position_cm']);rot=u.Rotator(pitch=0,yaw=p['yaw_ue'],roll=0)
        if kind in ('Desk','Chair'):
            if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,loc,rot)
            movable(a);a.static_mesh_component.set_static_mesh(load_mesh(CFG['ue_base']+'/Meshes/SM_Staff_'+kind))
            a.static_mesh_component.set_collision_profile_name('BlockAllDynamic')
        else:
            if not a:a=AA.spawn_actor_from_class(container_class,loc,rot)
            movable(a)
            if kind!='Locker':
                spec=specs[p['id']]
                a.body.set_static_mesh(load_mesh(spec['body']))
                a.door.set_static_mesh(load_mesh(spec['door']) if spec['door'] else None)
                a.door_hinge.set_relative_location(u.Vector(*spec['hinge_cm']),False,False)
                a.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,dict(Swing='SWING',Drawer='DRAWER',OpenShelf='OPEN_SHELF')[spec['motion']]))
                a.set_editor_property('caption',spec['caption']);a.set_editor_property('container_id',spec['container_id'])
                a.set_editor_property('storage_pages',1)
                if not spec['door']:a.door.set_collision_profile_name('NoCollision')
            for component in (a.body,a.door):component.set_render_custom_depth(True);component.set_custom_depth_stencil_value(201)
            container_records.append(p['id'])
        owned(a,label,p['id']);a.set_actor_location_and_rotation(loc,rot,False,True);layout_actors.append(a)
    manager_label='StaffSubject_StaffDormitory_LayoutVariantsV2'
    manager=actors.get(manager_label) or AA.spawn_actor_from_class(layout_class,u.Vector())
    manager.set_actor_label(manager_label);manager.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name('StaffDormitory.LayoutController')])
    manager.set_folder_path('StaffLiving/StaffDormitory/VariableFurniture')
    manager.set_editor_property('layout_actors',layout_actors)
    manager.set_editor_property('layout_json',json.dumps(MAN['layouts'],ensure_ascii=False,separators=(',',':')))
    manager.set_editor_property('random_seed',-1)
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Dormitory map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',layout_actor=manager_label,layout_furniture=len(layout_actors),
        dormitory_containers=container_records,bed_positions_changed=False);record()
    u.log('STAFF_DORM_VARIANTS_MAP_SAVED '+target)

for file in ('room.json','modules-draft.json'):shutil.copy2(ROOT/'Config'/file,backup/file)
dorm=next(r for r in CFG['rooms'] if r['id']=='StaffDormitory')
by_id={p['id']:p for p in dorm['furniture']}
for p in poses:
    if p['id'] in by_id:
        by_id[p['id']].update(position=p['position'],yaw_blender_deg=p['yaw_blender_deg'])
    else:dorm['furniture'].append({k:p[k] for k in ('id','prototype','position','yaw_blender_deg')})
CFG.update(dormitory_layout_revision=2,current_authored_source='DormitoryVariantsV2/Authored/StaffLivingTheme_DormitoryVariantsV2.blend')
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
draft_path=ROOT/'Config/modules-draft.json';draft=json.loads(draft_path.read_text('utf8'))
module=next(m for m in draft['modules'] if m['id']=='StaffDormitory')
module['parts']=[p for p in module['parts'] if p.get('mesh','').rsplit('/',1)[-1] not in ('SM_Staff_Desk','SM_Staff_Chair')]
existing={c['container_id']:c for c in module.get('scene_containers',[])}
for p in poses:
    if p['prototype']=='Locker':
        c=existing['StaffDormitory.'+p['id']];c.update(position=p['position_cm'],yaw=p['yaw_ue'])
for c in MAN['containers']:
    p=next(p for p in poses if p['id']==c['id'])
    existing[c['container_id']]=dict(actor_class='/Script/FPSGAME.ColdSteelSceneContainer',container_id=c['container_id'],
        caption=c['caption'],body=c['body'],door=c['door'],hinge=c['hinge_cm'],opening_motion=c['motion'],
        position=p['position_cm'],yaw=p['yaw_ue'],storage_pages=1,layout_slot=c['id'])
module['scene_containers']=list(existing.values())
module['layout_variants']=MAN['layouts'];module['layout_actor_class']='/Script/FPSGAME.StaffDormitoryLayout'
module['variable_static_furniture']=[dict(mesh=CFG['ue_base']+'/Meshes/SM_Staff_'+p['prototype'],layout_slot=p['id'],position=p['position_cm'],yaw=p['yaw_ue']) for p in poses if p['prototype'] in ('Desk','Chair')]
draft['dormitory_layout_revision']=2;draft_path.write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',new_container_count=24,container_types=['Bookcase','Bookshelf','Bedside'],
    rooms=6,variants_per_room=4,beds_fixed=True,random_pool_registered=False,open_command='open '+CFG['sample_map']);record()
u.log('STAFF_DORM_VARIANTS_DELIVERY_SAVED')
