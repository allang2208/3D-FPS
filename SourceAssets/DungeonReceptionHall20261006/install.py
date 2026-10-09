"""Background import and creation of one new subject map. No PIE or acceptance run."""
import unreal as u
import json,hashlib,re,traceback,math
from pathlib import Path
from collections import defaultdict
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
CFG=json.loads((ROOT/'Config/layout.json').read_text('utf8'));MAN=json.loads((ROOT/'manifest.json').read_text('utf8'));ROLES=json.loads((ROOT/'Config/materials.json').read_text('utf8'))
BASE=CFG['base'];MAP=CFG['map'];OWNER='ReceptionHall20261006'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
report=dict(stage='preparing',map=MAP,saved_assets=[],reused_placements=0,instance_groups=[],interactions=[],lights=0,
    tests_run=False,rendered=False,game_run=False,editor_opened=False,production_registered=False)
def record(): (ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def asset(path):
    a=u.load_asset(path)
    if not a:raise RuntimeError('Required production asset missing: '+path)
    return a
def saved(a,key):
    E.set_metadata_tag(a,OWNER+'.Source',key)
    if not E.save_loaded_asset(a,False):raise RuntimeError('Unable to save '+a.get_path_name())
    report['saved_assets'].append(a.get_path_name());record();return a
def reuse(path,key):
    if not E.does_asset_exist(path):return None
    a=asset(path)
    if E.get_metadata_tag(a,OWNER+'.Source')!=key:raise RuntimeError('Preserve differing asset '+path)
    report['saved_assets'].append(a.get_path_name());return a
def imported(path,file,options=None,replace=False):
    t=u.AssetImportTask();t.filename=str(file);t.destination_path,t.destination_name=path.rsplit('/',1);t.automated=True;t.replace_existing=replace;t.save=False
    if options:t.options=options;t.factory=u.FbxFactory()
    A.import_asset_tasks([t]);return asset(path)
def guard():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE_ACTIVE: preserve running editor')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('DIRTY_MAP: preserve unsaved map')
def vec(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
def cm(p):return [p[0]*100,-p[1]*100,p[2]*100]
def spawn(cls,p,label,folder='Architecture',yaw=0):
    a=AA.spawn_actor_from_class(cls,vec(p),u.Rotator(pitch=0,yaw=-yaw,roll=0))
    if not a:raise RuntimeError('Spawn failed: '+label)
    a.set_actor_label('Reception_'+label);a.set_folder_path('Reception/'+folder)
    a.set_editor_property('tags',list(a.tags)+[u.Name('Reception.Subject')]);return a
def static(path,p,label,collision=True,yaw=0,scale=None,shadow=True,folder='Architecture',rail=False):
    a=spawn(u.StaticMeshActor,p,label,folder,yaw);c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(asset(path))
    c.set_collision_profile_name('BlockAll' if collision else 'NoCollision');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if collision else u.CollisionEnabled.NO_COLLISION)
    c.set_cast_shadow(shadow);c.set_editor_property('generate_overlap_events',False)
    if scale:a.set_actor_scale3d(u.Vector(*scale))
    if rail:
        a.set_editor_property('tags',list(a.tags)+[u.Name('Traversal.GuardrailDrop')]);c.set_editor_property('component_tags',[u.Name('Traversal.GuardrailDrop')])
    return a
def materials():
    textures={}
    for suffix,channel in [('Signs','color'),('Terrazzo_BaseColor','color'),('Terrazzo_NormalDX','normal'),('Terrazzo_Roughness','rough')]:
        source=ROOT/'Authored/Textures'/('T_Reception_'+suffix+'.png');key=hashlib.sha256(source.read_bytes()).hexdigest();path=BASE+'/Textures/T_Reception_'+suffix
        tex=reuse(path,key)
        if not tex:
            tex=imported(path,source);tex.set_editor_property('srgb',channel=='color');tex.set_editor_property('never_stream',False)
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='normal' else u.TextureCompressionSettings.TC_MASKS if channel=='rough' else u.TextureCompressionSettings.TC_BC7)
            tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD)
            if channel=='normal':tex.set_editor_property('flip_green_channel',False)
            saved(tex,key)
        textures[suffix]=tex
    for name,r in ROLES.items():
        path=r['existing_ue_path']
        if not r.get('new_authored'):asset(path);continue
        key=hashlib.sha256(json.dumps(r,sort_keys=True).encode()).hexdigest()+':substrate-v1';m=reuse(path,key)
        if m:continue
        m=A.create_asset(path.rsplit('/',1)[1],BASE+'/Materials',u.Material,u.MaterialFactoryNew())
        m.set_editor_property('used_with_nanite',True);m.set_editor_property('used_with_instanced_static_meshes',True)
        slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels);slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
        def scalar(v):
            n=L.create_material_expression(m,u.MaterialExpressionConstant);n.set_editor_property('r',v);return n
        def color(v):
            n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector);n.set_editor_property('constant',u.LinearColor(*v,1));return n
        def sample(key,sampler):
            n=L.create_material_expression(m,u.MaterialExpressionTextureSampleParameter2D);n.set_editor_property('parameter_name',key);n.set_editor_property('texture',textures[key]);n.set_editor_property('sampler_type',sampler);return n
        def connect(n,out,prop,pin):L.connect_material_property(n,out,prop);L.connect_material_expressions(n,out,slab,pin)
        b=color(r['basecolor_linear']);out=''
        if name=='Labels':b=sample('Signs',u.MaterialSamplerType.SAMPLERTYPE_COLOR);out='RGB'
        if name in ('Floor','Stone'):
            b=sample('Terrazzo_BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR);out='RGB'
            if name=='Stone':
                mul=L.create_material_expression(m,u.MaterialExpressionMultiply);L.connect_material_expressions(b,'RGB',mul,'A');L.connect_material_expressions(color([1.12,1.04,.90]),'',mul,'B');b=mul;out=''
            connect(sample('Terrazzo_NormalDX',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'RGB',u.MaterialProperty.MP_NORMAL,'Normal')
            rough=sample('Terrazzo_Roughness',u.MaterialSamplerType.SAMPLERTYPE_MASKS);connect(rough,'R',u.MaterialProperty.MP_ROUGHNESS,'Roughness')
        else:connect(scalar(r['roughness']),'',u.MaterialProperty.MP_ROUGHNESS,'Roughness')
        connect(b,out,u.MaterialProperty.MP_BASE_COLOR,'BaseColor');connect(scalar(r['metallic']),'',u.MaterialProperty.MP_METALLIC,'Metallic')
        if name=='Glow':connect(color([2.3,2.15,1.7]),'',u.MaterialProperty.MP_EMISSIVE_COLOR,'EmissiveColor')
        L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
        errors=L.recompile_material(m)
        if errors:raise RuntimeError('Material compile failed '+name+' '+str(errors))
        L.layout_material_expressions(m);saved(m,key)
def meshes():
    for item in MAN['meshes']:
        path=item['mesh'];key=item['sha256'];replace=False
        if E.does_asset_exist(path):
            m=asset(path)
            if E.get_metadata_tag(m,OWNER+'.Source')==key:
                report['saved_assets'].append(m.get_path_name());continue
            # This task can refine its own imported FBX before publishing its new map.
            # Other source assets or an already published subject remain untouched.
            source=m.get_editor_property('asset_import_data').get_first_filename()
            if Path(source).resolve()!=Path(item['fbx']).resolve() or E.does_asset_exist(MAP):raise RuntimeError('Preserve unrelated or published mesh '+path)
            replace=True
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
        opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True
        d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.one_convex_hull_per_ucx=True
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        m=imported(path,item['fbx'],opt,replace)
        for i,slot in enumerate(m.get_editor_property('static_materials')):
            name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));m.set_material(i,asset(item['materials'][name]))
        build=SM.get_lod_build_settings(m,0);build.set_editor_property('use_full_precision_u_vs',True);build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True);SM.set_lod_build_settings(m,0,build)
        m.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
        settings=m.get_editor_property('nanite_settings').copy();settings.enabled=item['nanite'];settings.explicit_tangents=True;m.set_editor_property('nanite_settings',settings)
        if settings.enabled and not u.PlazaInstanceTools.build_nanite_data(m):raise RuntimeError('Native Nanite build failed '+item['name'])
        saved(m,key)
def interactions():
    for p in CFG['containers']:
        a=spawn(u.ColdSteelSceneContainer,p['position_m'],p['id'],'Containers',p['yaw_deg'])
        for key,v in dict(container_id=OWNER+'.'+p['id'],caption=p['caption'],storage_pages=p['storage_pages'],initial_open_fraction=0.,opening_duration=.55,
            opening_motion=getattr(u.ColdSteelContainerMotion,p['opening_motion'].upper()),opened_yaw=p.get('opened_yaw',100.),opened_roll=p.get('opened_roll',105.)).items():a.set_editor_property(key,v)
        a.root_component.set_mobility(u.ComponentMobility.MOVABLE)
        for comp,key in [(a.body,'body'),(a.door,'door')]:comp.set_mobility(u.ComponentMobility.MOVABLE);comp.set_static_mesh(asset(p[key]))
        a.body.set_collision_profile_name('BlockAll');a.door.set_collision_profile_name('NoCollision');a.door_hinge.set_relative_location(u.Vector(*p['hinge']),False,False)
        if p.get('drawer_travel'):a.set_editor_property('drawer_travel',u.Vector(*p['drawer_travel']))
        report['interactions'].append(dict(id=p['id'],type='scene_container'))
    for p in CFG['glass']:
        a=spawn(u.WardGlassWindow,p['position_m'],p['id'],'Glazing',p['yaw_deg']);pane=a.get_editor_property('glass_pane')
        prefix=BASE+'/Meshes/SM_Reception_'+p['glass_kind'];pane.set_static_mesh(asset(prefix+'PaneV5'));pane.set_cast_shadow(False);pane.set_editor_property('receives_decals',False)
        for key,path in dict(fracture_mesh=prefix+'FractureV5',fracture_material='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassFragmentsV5',
            impact_particles='/Game/NiagaraExamples/FX_Weapons/Impacts/NS_Impact_Glass',break_sound='/Game/Weapons/GunplayFX/Impacts/S_Impact_Glass_0').items():pane.set_editor_property(key,asset(path))
        pane.set_editor_property('pane_dimensions',u.Vector(p['width_m']*100,p['height_m']*100,.8));report['interactions'].append(dict(id=p['id'],type='breakable_glass'))
    for p in CFG['doors']:
        a=spawn(u.ColdSteelDoor,p['position_m'],p['id'],'Doors',p['yaw_deg']);cc={c.get_name():c for c in a.get_components_by_class(u.SceneComponent)}
        frame,leaf,hinge=[cc[k] for k in ('DoorFrame','DoorLeaf','DoorHinge')];frame.set_static_mesh(None);frame.set_collision_profile_name('NoCollision');frame.set_visibility(False)
        m=asset(p['leaf_mesh']);leaf.set_static_mesh(m);positive=p['positive_hinge'];sign=1 if positive else -1
        leaf.set_relative_rotation(u.Rotator(pitch=0,yaw=180 if positive else 0,roll=0),False,True)
        b=m.get_bounding_box();center=(b.min+b.max)*.5;extent=(b.max-b.min)*.5
        hinge.set_relative_location(u.Vector(0,sign*extent.y,0),False,True);leaf.set_relative_location(u.Vector(-center.x,-sign*extent.y-center.y,extent.z-center.z),False,True)
        for key,v in dict(hinge_on_positive_y=positive,open_angle_degrees=85.,open_seconds=.55,auto_close_seconds=0.).items():a.set_editor_property(key,v)
        report['interactions'].append(dict(id=p['id'],type='interactive_push_door'))
def build_map():
    guard()
    disk=PROJECT/'Content/GameMaps/Design/L_ReceptionHall_Subject.umap'
    if disk.exists() or E.does_asset_exist(MAP):raise RuntimeError('New subject already exists; preserve saved map and request scoped revision instead')
    world=u.EditorLoadingAndSavingUtils.new_blank_map(False)
    if not world:raise RuntimeError('New map creation failed')
    world.get_world_settings().set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
    for item in MAN['meshes']:
        if item['kind'] in ('Glass','Fracture'):continue
        static(item['mesh'],item.get('position_m',[0,0,0]),item['name'],item['collision'],shadow=item['cast_shadow'],rail=item['kind']=='Balustrades',folder='PreviewOnly' if item['kind']=='PreviewCaps' else 'Architecture')
    groups=defaultdict(list)
    for p in CFG['parts']:
        a=static(p['mesh'],p['position_m'],p['id'],p['collision'],p['yaw_deg'],p['scale'],p['cast_shadow'],'ReusedFurniture')
        # Existing native helper serializes ISM components; source actors survive if a group is unsuitable.
        a.set_editor_property('tags',list(a.tags)+[u.Name('ColdSteel.MainPlaza.Generated')]);groups[(p['mesh'],p['collision'])].append(a);report['reused_placements']+=1
    for (path,col),aa in groups.items():
        if len(aa)<2:
            for a in aa:a.set_editor_property('tags',[u.Name('Reception.Subject')])
            continue
        cluster=u.PlazaInstanceTools.create_plaza_cluster(aa,'Reception_Instances_'+path.rsplit('/',1)[1])
        if cluster:
            cluster.set_editor_property('tags',[u.Name('Reception.Subject'),u.Name('Reception.ReusedInstances')]);cluster.set_folder_path('Reception/ReusedFurniture')
            for a in aa:AA.destroy_actor(a)
            report['instance_groups'].append(dict(mesh=path,count=len(aa)))
        else:
            for a in aa:a.set_editor_property('tags',[u.Name('Reception.Subject')])
    interactions()
    for p in CFG['lights']:
        spot=p['type']=='spot';a=spawn(u.SpotLight if spot else u.PointLight,p['position_m'],p['id'],'Lighting')
        if spot:a.set_actor_rotation(u.Rotator(pitch=-90,yaw=0,roll=0),True)
        c=a.get_component_by_class(u.PointLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
        c.set_intensity(p['intensity']);c.set_editor_property('attenuation_radius',p['radius']*100);c.set_editor_property('cast_shadows',p['cast_shadows'])
        c.set_editor_property('max_draw_distance',5500 if spot else 3800);c.set_editor_property('max_distance_fade_range',650)
        c.set_editor_property('source_radius',8.);c.set_editor_property('source_length',70. if spot else 35.)
        c.set_editor_property('indirect_lighting_intensity',.9);c.set_editor_property('volumetric_scattering_intensity',.15)
        c.set_light_color(u.LinearColor(1.,.92,.79,1.))
        if spot:c.set_editor_property('outer_cone_angle',p['outer_cone_degrees']);c.set_editor_property('inner_cone_angle',p['inner_cone_degrees'])
        a.set_editor_property('tags',list(a.tags)+[u.Name('DungeonLight.'+p['role'])]);report['lights']+=1
    spawn(u.PlayerStart,CFG['player_start_m'],'PlayerStart','PreviewOnly')
    pp=spawn(u.PostProcessVolume,[0,0,0],'ExposureAndContainerOutline','Environment');pp.set_editor_property('unbound',True)
    settings=pp.get_editor_property('settings')
    for key,v in [('auto_exposure_min_brightness',.7),('auto_exposure_max_brightness',.7),('auto_exposure_bias',-.05),('vignette_intensity',.18),('bloom_intensity',.16)]:settings.set_editor_property('override_'+key,True);settings.set_editor_property(key,v)
    blend=u.WeightedBlendable();blend.set_editor_property('weight',1.);blend.set_editor_property('object',asset('/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Materials/M_Staff_ContainerOutline_V4'))
    weighted=settings.get_editor_property('weighted_blendables');weighted.set_editor_property('array',[blend]);settings.set_editor_property('weighted_blendables',weighted);pp.set_editor_property('settings',settings)
    pp.set_editor_property('tags',list(pp.tags)+[u.Name('ColdSteel.SceneContainer.Outline')])
    E.set_metadata_tag(world,OWNER+'.Owner',OWNER);E.set_metadata_tag(world,OWNER+'.Revision',CFG['revision'])
    import runpy
    runpy.run_path(str(PROJECT/'SourceAssets/HallLighting20261007/profile.py'))['reapply_if_installed']()
    if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Reception map save failed')
    report.update(stage='map_saved',console_command='open '+MAP,return_command='open /Game/GameMaps/DayNight_Lighting');record()
def main():
    guard();record();materials();meshes();report['stage']='assets_saved';record();build_map();u.log('RECEPTION_HALL_MAP_SAVED '+MAP)
if __name__=='__main__':
    try:main()
    except Exception:report['error']=traceback.format_exc();record();raise
