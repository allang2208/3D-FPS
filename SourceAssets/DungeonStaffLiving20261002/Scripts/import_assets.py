"""Import/save original living-room assets and four preview maps in a commandlet.

Only this batch's new namespace/maps are saved. No game, layout generation, tests,
screenshots, production-catalog writes or project-default changes are performed.
"""
import hashlib,json,math,re
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/room.json').read_text('utf-8'))
if CFG.get('production_revision',0)>=1:
    current=ROOT/'Production20261002/Scripts/install_production.py'
    exec(compile(current.read_text('utf8'),str(current),'exec'))
    raise SystemExit(0)
if CFG.get('coffee_polish_revision',0)>=7:
    refinement=ROOT/'Scripts/import_coffee_polish_v7.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('wall_inset_revision',0)>=6:
    refinement=ROOT/'Scripts/import_wall_inset_v6.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('room_details_revision',0)>=5:
    refinement=ROOT/'Scripts/import_room_details_v5.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('scene_polish_revision',0)>=4:
    refinement=ROOT/'Scripts/import_scene_polish_v4.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('container_open_parts_revision',0)>=3:
    refinement=ROOT/'Scripts/import_container_open_parts_v3.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('dormitory_layout_revision',0)>=2:
    refinement=ROOT/'Scripts/import_dormitory_variants_v2.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('container_interaction_revision',0)>=1:
    refinement=ROOT/'Scripts/import_search_containers_v1.py'
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
if CFG.get('layout_revision',0)>=3:
    refinement=ROOT/('Scripts/import_intact_tiles_v4.py' if CFG.get('layout_revision',0)>=4 else 'Scripts/import_refinement_v3.py')
    exec(compile(refinement.read_text('utf8'),str(refinement),'exec'))
    raise SystemExit(0)
MAN=json.loads((ROOT/'Authored/manifest.json').read_text('utf-8'))
SURFACE=json.loads((ROOT/'Authored/surface-manifest.json').read_text('utf-8'))
BASE=CFG['ue_base'];E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ML=u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():raise RuntimeError('Background commandlet required')
RP=ROOT/'Receipts/install.json'
report=json.loads(RP.read_text('utf-8')) if RP.exists() else dict(meshes={},textures={},materials=[],maps={},saved_assets=[])
report.update(revision=CFG['revision'],tests_run=False,rendered=False,game_run=False,random_pool_registered=False,editor_opened=False)

def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def save(asset):
    if not asset.get_path_name().startswith(BASE+'/'):raise RuntimeError('Save outside owned namespace')
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Asset save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved_assets']:report['saved_assets'].append(asset.get_path_name())
    record()

def scalar(material,value):
    node=ML.create_material_expression(material,u.MaterialExpressionConstant);node.set_editor_property('r',value);return node

def vector(material,color):
    node=ML.create_material_expression(material,u.MaterialExpressionConstant3Vector)
    node.set_editor_property('constant',u.LinearColor(*color,1));return node

def texture_node(material,texture,kind):
    node=ML.create_material_expression(material,u.MaterialExpressionTextureSampleParameter2D)
    node.set_editor_property('parameter_name',kind);node.set_editor_property('texture',texture)
    node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else
                             u.MaterialSamplerType.SAMPLERTYPE_MASKS if kind=='ORM' else u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    return node

textures={}
for file in sorted((ROOT/'Authored').glob('T_Staff_*.png')):
    name=file.stem;path=BASE+'/Textures/'+name;digest=hashlib.sha256(file.read_bytes()).hexdigest()
    texture=u.load_asset(path) if E.does_asset_exist(path) else None
    if texture:
        if report['textures'].get(name,{}).get('source_sha256')!=digest:raise RuntimeError('Preserve differing texture '+path)
    else:
        task=u.AssetImportTask();task.filename=str(file);task.destination_path=BASE+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False;AT.import_asset_tasks([task]);texture=u.load_asset(path)
        if not texture:raise RuntimeError('Texture import failed '+name)
        normal=name.endswith('_Normal');orm=name.endswith('_ORM')
        texture.set_editor_property('srgb',not (normal or orm))
        texture.set_editor_property('never_stream',False)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if normal else
                                     u.TextureCompressionSettings.TC_MASKS if orm else u.TextureCompressionSettings.TC_BC7)
        report['textures'][name]=dict(path=path,source_sha256=digest);save(texture)
    textures[name]=texture

for key,desc in SURFACE['materials'].items():
    path=BASE+'/Materials/M_Staff_'+key
    if E.does_asset_exist(path):
        if path not in report['materials']:raise RuntimeError('Preserve pre-existing material '+path)
        continue
    material=AT.create_asset('M_Staff_'+key,BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    if not material:raise RuntimeError('Material creation failed '+key)
    material.set_editor_property('used_with_nanite',True);material.set_editor_property('used_with_instanced_static_meshes',True)
    material.set_editor_property('two_sided',key=='Mirror')
    slab=ML.create_material_expression(material,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    def connect(node,output,pin,prop):
        ML.connect_material_expressions(node,output,slab,pin)
        ML.connect_material_property(node,output,prop)
    if 'basecolor' in desc:
        node=texture_node(material,textures[desc['basecolor']],'BaseColor');output='RGB'
        if 'tint' in desc:
            multiply=ML.create_material_expression(material,u.MaterialExpressionMultiply)
            ML.connect_material_expressions(node,'RGB',multiply,'A');ML.connect_material_expressions(vector(material,desc['tint']),'',multiply,'B')
            node=multiply;output=''
    else:node=vector(material,desc['color']);output=''
    connect(node,output,'BaseColor',u.MaterialProperty.MP_BASE_COLOR)
    if 'normal' in desc:connect(texture_node(material,textures[desc['normal']],'Normal'),'RGB','Normal',u.MaterialProperty.MP_NORMAL)
    if 'orm' in desc:
        orm=texture_node(material,textures[desc['orm']],'ORM')
        connect(orm,'G','Roughness',u.MaterialProperty.MP_ROUGHNESS);connect(orm,'B','Metallic',u.MaterialProperty.MP_METALLIC)
        ML.connect_material_property(orm,'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    else:
        connect(scalar(material,desc.get('roughness',.65)),'','Roughness',u.MaterialProperty.MP_ROUGHNESS)
        connect(scalar(material,desc.get('metallic',0)),'','Metallic',u.MaterialProperty.MP_METALLIC)
    if 'emissive' in desc:connect(vector(material,desc['emissive']),'','EmissiveColor',u.MaterialProperty.MP_EMISSIVE_COLOR)
    ML.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    ML.layout_material_expressions(material);ML.recompile_material(material)
    report['materials'].append(path);save(material)
report['stage']='materials_saved';record()

sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if sub is None:sub=u.new_object(u.StaticMeshEditorSubsystem)
meshes={};prototypes={};room_meshes={}
for item in MAN['objects']:
    path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    if mesh:
        if report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:raise RuntimeError('Preserve differing mesh '+path)
    else:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.one_convex_hull_per_ucx=True;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed '+path)
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
            material=u.load_asset(item['materials'][key])
            if not material:raise RuntimeError('Missing shared material '+item['materials'][key])
            mesh.set_material(index,material)
        build=sub.get_lod_build_settings(mesh,0)
        build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True)
        build.set_editor_property('recompute_tangents',True);sub.set_lod_build_settings(mesh,0,build)
        mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',
            u.CollisionTraceFlag.CTF_USE_SIMPLE_AND_COMPLEX if item['simple_collision_hulls'] else u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        n=mesh.get_editor_property('nanite_settings').copy();n.enabled=item['nanite'];n.explicit_tangents=True
        n.generate_fallback=u.NaniteGenerateFallback.ENABLED;n.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        n.fallback_percent_triangles=1.;n.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',n)
        if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Nanite build failed '+path)
        report['meshes'][item['name']]=dict(path=path,source_sha256=digest,source_triangles=item['triangles'],
            collision=item['collision'],nanite=item['nanite'],simple_collision_hulls=item['simple_collision_hulls'])
        save(mesh)
    meshes[item['name']]=mesh
    if item['prototype']:prototypes[item['prototype']]=(mesh,item)
    else:room_meshes.setdefault(item['room_id'],[]).append((mesh,item))
    u.log('STAFF_LIVING_MESH_SAVED '+item['name'])
report['stage']='assets_saved';record()
CFG=json.loads((ROOT/'Config/room.json').read_text('utf-8'))

# Production-ready author descriptors remain drafts until the user accepts the samples.
modules=[]
for room in CFG['rooms']:
    parts=[]
    for mesh,item in room_meshes[room['id']]:
        parts.append(dict(mesh=item['asset'],position=[0,0,0],yaw=0,collision=item['collision'],materials=[]))
    for part in room['furniture']:
        item=prototypes[part['prototype']][1]
        x,y,z=part['position'];parts.append(dict(id=part['id'],mesh=item['asset'],position=[x*100,-y*100,z*100],
            yaw=-part['yaw_blender_deg'],collision=item['collision'],materials=[]))
    lights=[]
    for light in room['lights']:
        x,y,z=light['position'];parts.append(dict(mesh=prototypes['LampFixture'][1]['asset'],position=[x*100,-y*100,(z+.11)*100],yaw=0,collision=False,materials=[]))
        lights.append(dict(light,position=[x*100,-y*100,z*100]))
    ports=[]
    for p in room['ports']:
        x,y,z=p['position'];nx,ny,nz=p['normal']
        ports.append(dict(p,position=[x*100,-y*100,z*100],normal=[nx,-ny,nz],width=p['width']*100,height=p['height']*100))
    cells=[dict(min=[c['min'][0]*100,-c['max'][1]*100,c['min'][2]*100],
                max=[c['max'][0]*100,-c['min'][1]*100,c['max'][2]*100]) for c in room['room_cells']]
    modules.append(dict(id=room['id'],family_id=room['id'],name=room['name'],role='room',parts=parts,lights=lights,
        ports=ports,cells=cells,port_pairs=[[0,1]],anchors=[dict(role='encounter',position=[x*100,-y*100,z*100]) for x,y,z in room['encounter_anchors_m']],
        author_walk_rects_m=room['walk_rects_m'],phase='subject',random_pool_registered=False))
(ROOT/'Config/modules-draft.json').write_text(json.dumps(dict(sequence=CFG['sequence'],modules=modules,
    registered=False,reason='Awaiting user review of complete staff-living theme.'),ensure_ascii=False,indent=2),encoding='utf-8')

AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if AA is None:AA=u.new_object(u.EditorActorSubsystem)

def location(p,offset=(0,0,0)):
    return u.Vector((p[0]+offset[0])*100,-(p[1]+offset[1])*100,(p[2]+offset[2])*100)

def owned(actor,label,room='Environment'):
    actor.set_actor_label('StaffSubject_'+label);actor.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(room)])
    actor.set_folder_path('StaffLiving/'+room);return actor

def static(mesh,item,p,offset,label,room,yaw=0):
    a=AA.spawn_actor_from_class(u.StaticMeshActor,location(p,offset),u.Rotator(pitch=0,yaw=-yaw,roll=0))
    if not a:raise RuntimeError('Static actor creation failed '+label)
    owned(a,label,room);c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
    c.set_collision_profile_name('BlockAll' if item['collision'] else 'NoCollision')
    c.set_editor_property('cast_shadow',item['kind'] not in ('Signs','WetGrout','Nosing'))
    return a

def cap(world,p,label):
    mesh=u.load_asset('/Engine/BasicShapes/Cube')
    a=AA.spawn_actor_from_class(u.StaticMeshActor,location([p[0],p[1],1.4]))
    owned(a,label,'PreviewCaps');a.static_mesh_component.set_static_mesh(mesh)
    a.static_mesh_component.set_material(0,u.load_asset(BASE+'/Materials/M_Staff_OlivePaint'))
    a.set_actor_scale3d(u.Vector(.13,3,2.8));a.static_mesh_component.set_collision_profile_name('BlockAll')

def populate_room(room,offset):
    groups={}
    for mesh,item in room_meshes[room['id']]:static(mesh,item,[0,0,0],offset,room['id']+'_'+item['kind'],room['id'])
    for part in room['furniture']:
        mesh,item=prototypes[part['prototype']]
        actor=static(mesh,item,part['position'],offset,room['id']+'_'+part['id'],room['id'],part['yaw_blender_deg'])
        if item['nanite']:groups.setdefault(part['prototype'],[]).append(actor)
    for light in room['lights']:
        mesh,item=prototypes['LampFixture'];p=light['position']
        static(mesh,item,[p[0],p[1],p[2]+.11],offset,room['id']+'_Fixture_'+light['id'],room['id'])
        a=owned(AA.spawn_actor_from_class(u.PointLight,location(p,offset)),room['id']+'_Light_'+light['id'],room['id'])
        c=a.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
        c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(light['lumens'])
        c.set_editor_property('attenuation_radius',light['radius_cm']);c.set_editor_property('cast_shadows',light['cast_shadows'])
        c.set_editor_property('max_draw_distance',light['max_draw_distance_cm']);c.set_editor_property('max_distance_fade_range',light['fade_range_cm'])
        c.set_editor_property('indirect_lighting_intensity',light['indirect']);c.set_light_color(u.LinearColor(*light['tint'],1))
        a.set_editor_property('tags',[u.Name('StaffLiving.Subject'),u.Name(room['id']),u.Name('Dungeon.Light.'+light['role'])])
    # Preserve collision and component policy while reducing repeated furniture components.
    for key,actors in groups.items():
        if len(actors)<2:continue
        cluster=u.PlazaInstanceTools.create_plaza_cluster(actors,'StaffSubject_'+room['id']+'_'+key+'_Instances')
        if cluster:
            owned(cluster,room['id']+'_'+key+'_Instances',room['id'])
            for actor in actors:AA.destroy_actor(actor)

def postprocess():
    pp=owned(AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector()),'Exposure')
    pp.set_editor_property('unbound',True);s=pp.get_editor_property('settings');cfg=CFG['postprocess']
    for key,value in [('override_auto_exposure_min_brightness',True),('auto_exposure_min_brightness',cfg['exposure_ev']),
        ('override_auto_exposure_max_brightness',True),('auto_exposure_max_brightness',cfg['exposure_ev']),
        ('override_auto_exposure_bias',True),('auto_exposure_bias',cfg['exposure_bias']),
        ('override_bloom_intensity',True),('bloom_intensity',cfg['bloom']),
        ('override_vignette_intensity',True),('vignette_intensity',cfg['vignette'])]:s.set_editor_property(key,value)
    pp.set_editor_property('settings',s)

def create_map(target,selected,offsets,combined=False):
    previous=report['maps'].get(target)
    if previous and previous.get('layout_revision')==CFG['layout_revision']:return
    if E.does_asset_exist(target):
        if not previous:raise RuntimeError('Preserve pre-existing preview map '+target)
        world=u.EditorLoadingAndSavingUtils.load_map(target)
        for actor in list(AA.get_all_level_actors()):
            if actor.get_actor_label().startswith('StaffSubject_'):AA.destroy_actor(actor)
            elif actor.__class__.__name__ not in ('WorldSettings','Brush','LevelBounds','DefaultPhysicsVolume'):
                raise RuntimeError('Preserve independently authored actor in '+target)
    else:world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:raise RuntimeError('New blank world failed')
    mode=u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode')
    if not mode:raise RuntimeError('FPS GameMode unavailable')
    world.get_world_settings().set_editor_property('default_game_mode',mode)
    for room,offset in zip(selected,offsets):populate_room(room,offset)
    if combined:
        for offset in ([16,0,0],[48,0,0]):
            for mesh,item in room_meshes['Link']:static(mesh,item,[0,0,0],offset,'Link_'+str(offset[0])+'_'+item['kind'],'Links')
        cap(world,[-16,0,0],'ThemeEntryCap');cap(world,[86,0,0],'ThemeExitCap')
        start=selected[0]['player_start_m'];offset=offsets[0]
    else:
        for port in selected[0]['ports']:cap(world,port['position'],'PortCap_'+port['id'])
        start=selected[0]['player_start_m'];offset=offsets[0]
    owned(AA.spawn_actor_from_class(u.PlayerStart,location(start,offset),u.Rotator(pitch=0,yaw=0,roll=0)),'PlayerStart')
    postprocess()
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',sequence=[r['id'] for r in selected],combined=combined,
        layout_revision=CFG['layout_revision'],game_mode='/Script/FPSGAME.FPSGAMEGameMode')
    record();u.log('STAFF_LIVING_MAP_SAVED '+target)

for room in CFG['rooms']:create_map(CFG['maps'][room['id']],[room],[[0,0,0]])
create_map(CFG['sample_map'],CFG['rooms'],CFG['preview_placements_m'],True)
report.update(stage='samples_saved',furniture_instances=sum(len(r['furniture']) for r in CFG['rooms']),
    room_ids=CFG['sequence'],return_command='open '+CFG['return_map'],
    console_commands=['open '+CFG['sample_map']]+['open '+CFG['maps'][r['id']] for r in CFG['rooms']])
record();u.log('STAFF_LIVING_DELIVERY_SAVED')
