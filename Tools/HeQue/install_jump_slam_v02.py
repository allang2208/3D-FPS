"""Import and save the jump-slam assets on the existing HeQue Blueprint."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/JumpSlamV02'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/JumpSlamV02'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report=dict(stage='importing',saved=[],gameplay_tested=False,visual_tested=False,audio_auditioned=False,multiplayer_tested=False)
RECEIPT=ROOT/'Records/ue-import.json'
for path,names in (('Tools/RootCrown/install.py',('record','save','create','import_file','fbx','pose_at','align_root_units')),
    ('Tools/HeQue/install_psychic_v01.py',('node','wire','custom'))):
    tree=ast.parse((PROJECT/path).read_text('utf8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'HeQue/jump_import','exec'))

def ground_material(flow,ring):
    shader='JumpGroundWave' if ring else 'JumpGroundImpact'
    mat=create('M_HeQue_'+shader+'V02',VERSION+'/Materials',u.Material,u.MaterialFactoryNew())
    ME.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True);mat.set_editor_property('disable_depth_test',False)
    mat.set_editor_property('enable_responsive_aa',True)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    texture=node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='FlowTex',texture=flow,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    alpha=node(mat,u.MaterialExpressionScalarParameter,parameter_name='PulseAlpha',default_value=0.)
    phase=node(mat,u.MaterialExpressionScalarParameter,parameter_name='PulsePhase',default_value=0.)
    color=custom(mat,shader,{'UV':(uv,''),'FlowTex':(texture,''),'Alpha':(alpha,''),'Phase':(phase,'')},u.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    opacity=node(mat,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(color,'',rgb,str(ME.get_material_expression_input_names(rgb)[0]))
    wire(color,'',opacity,str(ME.get_material_expression_input_names(opacity)[0]))
    depth=node(mat,u.MaterialExpressionDepthFade,fade_distance_default=8.)
    wire(opacity,'',depth,str(ME.get_material_expression_input_names(depth)[0]))
    ME.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    ME.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    if ring:
        radius=node(mat,u.MaterialExpressionScalarParameter,parameter_name='WaveRadiusCm',default_value=100.)
        center=node(mat,u.MaterialExpressionVectorParameter,parameter_name='WaveOrigin',default_value=u.LinearColor(0,0,0,0))
        normal=node(mat,u.MaterialExpressionVectorParameter,parameter_name='GroundNormal',default_value=u.LinearColor(0,0,1,0))
        position=node(mat,u.MaterialExpressionWorldPosition)
        offset=custom(mat,'JumpGroundOffset',{'UV':(uv,''),'Radius':(radius,''),'Center':(center,''),'Up':(normal,''),'Position':(position,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
        ME.connect_material_property(offset,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    ME.recompile_material(mat);save(mat);return mat

previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue packages')
    for relative in ('BP_HeQue.uasset','RigV01/SK_HeQue_Skeleton.uasset'):
        source=PROJECT/'Content/Monsters/HeQue'/relative;backup=ROOT/'Before'/relative
        backup.parent.mkdir(parents=True,exist_ok=True)
        if source.exists() and not backup.exists():shutil.copy2(source,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    flow=u.load_asset(DEST+'/PsychicWaveV02/Textures/T_HeQue_PsychicFlowV02')
    if not mesh or not bp or not flow:raise RuntimeError('Delivered HeQue rig, Blueprint or flow texture missing')
    authored=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    clips={};report['root_units']={}
    for entry in authored['clips']:
        options=fbx(True,mesh.skeleton)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',authored['fps'])
        clip=import_file(ROOT/'Export'/(entry['name']+'.fbx'),entry['name'],VERSION+'/Animations',options,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][entry['role']]=align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Jump animation compilation unfinished: '+entry['name'])
        save(clip);clips[entry['role']]=clip
    save(mesh.skeleton)
    materials={role:ground_material(flow,role=='Wave') for role in ('Wave','Impact')}
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('auto_generate_collision',False);data.set_editor_property('combine_meshes',True)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    meshes={}
    for role in ('Wave','Impact'):
        name='SM_HeQue_JumpGround'+role+'V02'
        asset=import_file(ROOT/'Export'/(name+'.fbx'),name,VERSION,options,u.FbxFactory())
        asset.set_material(0,materials[role]);save(asset);meshes[role]=asset
    sounds={}
    for role in ('Charge','Air','Impact'):
        name='S_HeQue_Jump'+role+'V02'
        sound=import_file(ROOT/'Audio'/(name+'.wav'),name,VERSION+'/Audio',factory=u.SoundFactory())
        save(sound);sounds[role]=sound
    attenuation=create('SA_HeQue_JumpV02',VERSION+'/Audio',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents',u.Vector(300,0,0))
    settings.set_editor_property('falloff_distance',2200.);settings.set_editor_property('spatialize',True)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    report['previous_jump_assets']={key:cdo.get_editor_property(key).get_path_name() for key in
        ('jump_charge_clip','jump_air_clip','jump_dive_clip','jump_recover_clip','jump_wave_mesh','jump_impact_mesh','jump_wave_material','jump_impact_material')
        if cdo.get_editor_property(key)}
    bindings=dict(jump_charge_clip=clips['Charge'],jump_air_clip=clips['Air'],jump_dive_clip=clips['Dive'],jump_recover_clip=clips['Recover'],
        jump_wave_mesh=meshes['Wave'],jump_impact_mesh=meshes['Impact'],jump_wave_material=materials['Wave'],jump_impact_material=materials['Impact'],
        jump_charge_sound=sounds['Charge'],jump_air_sound=sounds['Air'],jump_impact_sound=sounds['Impact'],jump_attenuation=attenuation)
    for key,value in bindings.items():cdo.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'HeQue.JumpSlam','V02: 1.95s slow charge; 1600cm/s dive; 0.067s compression/0.23s rebound; bright ground-wave front; 2.60s recovery; original damage and cooldown')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='jump_slam_v02_saved',blueprint=bp.get_path_name(),
        clips={role:dict(path=clip.get_path_name(),duration=clip.get_play_length()) for role,clip in clips.items()},
        charge_seconds=authored['charge_seconds'],recovery_seconds=authored['recovery_seconds'],
        jump_height_cm=float(cdo.get_editor_property('jump_height')),minimum_clearance_jump_cm=authored['minimum_clearance_jump_cm'],
        impact_radius_cm=float(cdo.get_editor_property('jump_impact_radius')),impact_damage=float(cdo.get_editor_property('jump_impact_damage')),
        wave_radius_cm=float(cdo.get_editor_property('jump_wave_radius')),wave_damage=float(cdo.get_editor_property('jump_wave_damage')),
        wave_seconds=authored['wave_seconds'],cooldown=float(cdo.get_editor_property('jump_cooldown')),
        dive_speed_cm_per_second=authored['dive_speed_cm_per_second'],compression_peak_seconds=authored['compression_peak_seconds'],
        rebound_peak_seconds=authored['rebound_peak_seconds'],low_recovery_hold_until=authored['low_recovery_hold_until'],
        impact_trigger='actual Character.Landed',hits_per_player_per_cast=1,fixed_vfx_components=2,f6_id='HeQue')
    record();print('HEQUE_JUMP_SLAM_V02_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
