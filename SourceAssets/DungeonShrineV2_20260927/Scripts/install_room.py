"""Import and save shrine V2 into the production start area; no gameplay or renders."""
import hashlib, json, math, re, runpy, sys
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
BASE='/Game/Dungeons/ShrineV2_20260927';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if Path(u.Paths.project_dir()).resolve()!=PROJECT:raise RuntimeError('Wrong project')
if UE.get_game_world():raise RuntimeError('Preserve active play; shrine V2 save pending')
initial_dirty={p.get_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())}
if any('/gamemaps/l_dungeon_randomized' in p.lower() or p.startswith(BASE) for p in initial_dirty):
    raise RuntimeError('Preserve unsaved shrine or dungeon edits')
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!=TARGET:
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve current unsaved map')
    world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
if not world:raise RuntimeError('Cannot load shrine map')
actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
generator=next(a for a in actors.values() if isinstance(a,u.AuthoredDungeonGenerator))
statue=actors['DGN_Start_ShrineStatue']
cfg=json.loads((ROOT/'Config/room.json').read_text())
manifest=json.loads((ROOT/'Authored/manifest.json').read_text())
for folder in ('Receipts','Before'):(ROOT/folder).mkdir(exist_ok=True)
prior_receipt=ROOT/'Receipts/install.json'
prior_sources=json.loads(prior_receipt.read_text(encoding='utf-8')).get('mesh_sources',{}) if prior_receipt.exists() else {}
report={'stage':'preparing','meshes':[],'mesh_sources':{},'materials':[],'actors':[],'hidden':[],'tests_run':False,'revision':cfg['revision']}
def record():
    (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())

# Keep the approved instance-space mineral projection and scanned stone maps.
stone_master=u.load_asset('/Game/Dungeons/Shrine20260927/Materials/M_ShrineStone')
if not stone_master:raise RuntimeError('Missing stone master')
materials={}
styles={
 'Stone0':(100,.73,.35,.83,(.76,.78,.77)),
 'Stone1':(100,.72,.32,.88,(.82,.80,.75)),
 'Stone2':(100,.77,.39,.79,(.71,.75,.75)),
 'FloorStone0':(110,.66,.32,.86,(.79,.80,.78)),
 'FloorStone1':(110,.67,.36,.81,(.77,.78,.76)),
 'FloorStone2':(110,.64,.30,.89,(.83,.81,.76)),
 'StoneCut':(65,.88,.53,.91,(.80,.80,.75)),
}
for name,(tile,normal,grain,brightness,tint) in styles.items():
    path=BASE+'/Materials/MI_'+name
    mi=u.load_asset(path) if E.does_asset_exist(path) else AT.create_asset('MI_'+name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    mi.modify();L.set_material_instance_parent(mi,stone_master)
    for pin,value in {'TileCm':tile,'DepthCm':0,'NormalStrength':normal,'GrainStrength':grain,'Brightness':brightness,'RoughnessScale':1.04,'GrainTileCm':21}.items():
        L.set_material_instance_scalar_parameter_value(mi,pin,value)
    L.set_material_instance_vector_parameter_value(mi,'Tint',u.LinearColor(*tint,1))
    L.update_material_instance(mi);save(mi);materials[name]=mi;report['materials'].append(path)
refs={
 'Concrete':'/Game/Dungeons/AtmosphereV2/Materials/M_Concrete',
 'FractureConcrete':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_BrokenConcrete',
 'Mortar':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_BondingMortar',
 'Earth':'/Game/Dungeons/AtmosphereV2/RoomInteriors/Earthwork/Materials/MI_Earth_Soil',
 'ServicePaint':'/Game/Dungeons/AtmosphereV2/Services/Materials/M_Service_Paint',
 'ServiceHardware':'/Game/Dungeons/CombatExpansion20260922/Materials/M_PipeCutSteel',
 'PipeCutSteel':'/Game/Dungeons/CombatExpansion20260922/Materials/M_PipeCutSteel',
 'WarmGlass':'/Game/Dungeons/AtmosphereV2/Materials/M_WarmGlass'}
for name,path in refs.items():
    materials[name]=u.load_asset(path)
    if not materials[name]:raise RuntimeError('Missing material '+path)
sys.path.insert(0,str(PROJECT/'Tools/AssetPipeline'))
from dungeon_material_usage import ensure_mesh_material_usage
meshes={}
for entry in manifest['objects']:
    path=BASE+'/Meshes/'+entry['name']
    source_hash=hashlib.sha256(Path(entry['fbx']).read_bytes()).hexdigest()
    mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if not mesh or prior_sources.get(path)!=source_hash:
        task=u.AssetImportTask();task.filename=entry['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=entry['name']
        task.automated=True;task.save=False;task.replace_existing=True
        options=u.FbxImportUI();options.import_mesh=True;options.import_materials=False;options.import_textures=False;options.import_as_skeletal=False
        options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=options.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
        task.options=options;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+path)
    mesh.modify()
    for index,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        mesh.set_material(index,materials[name])
    body=mesh.get_editor_property('body_setup');body.set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    # Match the project's authored rigid geometry policy, including RT/collision fallback.
    settings=mesh.get_editor_property('nanite_settings').copy()
    settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED
    settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.0;settings.fallback_relative_error=0.0
    mesh.set_editor_property('nanite_settings',settings)
    ensure_mesh_material_usage(mesh)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
    save(mesh);meshes[entry['kind']]=mesh;report['meshes'].append(path);report['mesh_sources'][path]=source_hash;record()

# Snapshot only this room's previous actors before altering their transforms/visibility.
def old_room(label):
    return label.startswith(('DGN_A_Room_RU_','DGN_A_RuinEarth_')) or label in (
       'DGN_A_AV2_Breach_Structural','DGN_A_AV2_Breach_Rebar','DGN_A_AV2_Breach_Shoring',
       'DGN_A_AV2_RuinNiche_Floor','DGN_A_AV2_RuinNiche_Ceiling','DGN_A_AV2_AncientArch','DGN_A_AV2_AncientPlinth')
previous=[]
for label,a in actors.items():
    if not old_room(label) and label not in ('DGN_Start_ShrineStatue','DGN_A_AV2_Light_Breach'):continue
    components=[]
    for c in a.get_components_by_class(u.StaticMeshComponent):
        components.append({'name':c.get_name(),'mesh':c.static_mesh.get_path_name() if c.static_mesh else None,
            'visible':c.get_editor_property('visible'),'collision':str(c.get_collision_profile_name())})
    previous.append({'label':label,'hidden':a.get_editor_property('hidden'),'collision':a.get_actor_enable_collision(),
        'position':list(a.get_actor_location().to_tuple()),'yaw':a.get_actor_rotation().yaw,'parts':components})
backup=ROOT/'Before/actors.json'
if not backup.exists():backup.write_text(json.dumps(previous,indent=2),encoding='utf-8')
backup=ROOT/'Before/catalog.json'
if not backup.exists():backup.write_text(generator.get_editor_property('module_catalog_json'),encoding='utf-8')

for label,a in actors.items():
    if not old_room(label):continue
    a.modify();a.set_actor_hidden_in_game(True);a.set_is_temporarily_hidden_in_editor(True);a.set_actor_enable_collision(False)
    for c in a.get_components_by_class(u.PrimitiveComponent):
        c.modify();c.set_visibility(False);c.set_collision_profile_name('NoCollision')
    for c in a.get_components_by_class(u.LightComponent):
        c.modify();c.set_visibility(False)
    report['hidden'].append(label)

for entry in manifest['objects']:
    label='DGN_A_ShrineV2_'+entry['kind'];a=actors.get(label)
    if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(*cfg['origin_ue_cm']))
    if not a:raise RuntimeError('Spawn failed '+label)
    a.modify();a.set_actor_label(label);a.set_folder_path('DungeonStart/ShrineV2')
    a.set_editor_property('tags',[u.Name('DungeonStart.ShrineRoom'),u.Name(cfg['revision'])])
    a.set_actor_location_and_rotation(u.Vector(*cfg['origin_ue_cm']),u.Rotator(pitch=0,yaw=0,roll=0),False,True)
    a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    c=a.get_component_by_class(u.StaticMeshComponent);c.modify();c.set_mobility(u.ComponentMobility.STATIC)
    c.set_static_mesh(meshes[entry['kind']]);c.set_editor_property('override_materials',[]);c.set_visibility(True)
    c.set_collision_profile_name('BlockAll' if entry['collision'] else 'NoCollision');a.set_actor_enable_collision(entry['collision'])
    report['actors'].append(label)

# The two fixed local lights are adopted by StartRoomLighting's reserved-start scan.
for entry in cfg['lights']:
    a=actors.get(entry['label']) or AA.spawn_actor_from_class(u.PointLight,u.Vector(*entry['position_cm']))
    a.modify();a.set_actor_label(entry['label']);a.set_folder_path('DungeonStart/ShrineV2')
    a.set_editor_property('tags',[u.Name('DungeonStart.ShrineRoom'),u.Name('DungeonLight.Accent')])
    a.set_actor_location(u.Vector(*entry['position_cm']),False,True);a.set_actor_hidden_in_game(False);a.set_is_temporarily_hidden_in_editor(False)
    c=a.get_component_by_class(u.PointLightComponent);c.modify();c.set_mobility(u.ComponentMobility.MOVABLE)
    c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(entry['intensity']);c.set_attenuation_radius(entry['radius_cm'])
    c.set_editor_property('use_temperature',True);c.set_temperature(entry['temperature']);c.set_cast_shadows(True)
    c.set_editor_property('source_radius',7.0);c.set_editor_property('max_draw_distance',2200.0);c.set_editor_property('max_distance_fade_range',500.0);c.set_visibility(True)
    report['actors'].append(entry['label'])

# Temper the previous yellow entrance wash without changing the rest of the passage.
entrance_light=actors.get('DGN_A_AV2_Light_Breach')
if entrance_light:
    c=entrance_light.get_component_by_class(u.PointLightComponent)
    if c:
        entrance_light.modify();c.modify();c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        c.set_intensity(450);c.set_editor_property('use_temperature',True);c.set_temperature(4400)
        c.set_attenuation_radius(500);c.set_editor_property('max_draw_distance',2200.0)
        c.set_editor_property('max_distance_fade_range',500.0)
        report['actors'].append(entrance_light.get_actor_label())

catalog=json.loads(generator.get_editor_property('module_catalog_json'))
catalog=runpy.run_path(str(PROJECT/'SourceAssets/DungeonShrine20260927/Scripts/extend_catalog.py'))['extend'](catalog)
catalog['start_shrine']['room_revision']=cfg['revision']
catalog['start_shrine']['exit_target_cm']=cfg['exit_target_cm']
assets={a.get_path_name():a for a in generator.get_editor_property('module_assets') if a}
for entry in catalog['start_shrine']['statues']:
    mesh=u.load_asset(entry['mesh'])
    if not mesh:raise RuntimeError('Missing statue '+entry['id'])
    assets[mesh.get_path_name()]=mesh
generator.modify();generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
generator.set_editor_property('module_assets',list(assets.values()))

# Individual calibrated front vectors are retained in the six catalog records.
# Set the current saved instance immediately; runtime also applies the chosen record.
statue.modify();statue.set_actor_location(u.Vector(*cfg['statue_position_cm']),False,True)
component=statue.get_component_by_class(u.StaticMeshComponent);component.modify()
current=component.static_mesh.get_path_name() if component.static_mesh else ''
choice=next((s for s in catalog['start_shrine']['statues'] if s['mesh']==current),catalog['start_shrine']['statues'][0])
delta=[cfg['exit_target_cm'][i]-cfg['statue_position_cm'][i] for i in range(3)]
yaw=math.degrees(math.atan2(delta[1],delta[0]))-choice['front_local_yaw_deg']
statue.set_actor_rotation(u.Rotator(pitch=0,yaw=yaw,roll=0),False)
statue.set_actor_hidden_in_game(False);statue.set_is_temporarily_hidden_in_editor(False);statue.set_actor_enable_collision(True)
component.set_visibility(True);component.set_collision_profile_name('BlockAll')
tags=list(statue.tags)
if u.Name('DungeonStart.ShrineStatue') not in tags:tags.append(u.Name('DungeonStart.ShrineStatue'))
statue.set_editor_property('tags',tags)

dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned=[p for p in dirty if p.get_name() not in initial_dirty and ('/gamemaps/l_dungeon_randomized' in p.get_name().lower() or p.get_name().startswith(BASE))]
if not owned or not u.EditorLoadingAndSavingUtils.save_packages(owned,False):raise RuntimeError('Shrine V2 save failed')
(PROJECT/'SourceAssets/DungeonRoutes20260922/Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
report.update(stage='saved',saved_packages=[p.get_name() for p in owned],statue_yaw=yaw,
    statue_position_cm=cfg['statue_position_cm'],facing=[{'id':s['id'],'front_local_yaw_deg':s['front_local_yaw_deg']} for s in catalog['start_shrine']['statues']])
record();print('SHRINE_V2_SAVED',json.dumps({'meshes':len(report['meshes']),'actors':len(report['actors']),'hidden':len(report['hidden']),'saved_packages':len(owned),'statue_yaw':yaw}))
