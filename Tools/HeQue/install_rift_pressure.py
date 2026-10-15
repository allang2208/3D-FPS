"""Save HeQue Rift Pressure animation, sound, visible wave/membrane materials and bindings."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/RiftPressureV01'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/RiftPressureV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'importing','saved':[],'gameplay_tested':False,'visual_tested':False,'audio_auditioned':False,'multiplayer_tested':False}
RECEIPT=ROOT/'Records/ue-import.json'
helpers=ast.parse((PROJECT/'Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'HeQue/rift_import','exec'))

def material(name,shader,depth_distance):
    mat=create(name,VERSION+'/Materials',u.Material,u.MaterialFactoryNew());ME.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True);mat.set_editor_property('disable_depth_test',False)
    def node(cls,**props):
        n=ME.create_material_expression(mat,cls)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def wire(a,b,pin,output=''):
        if not ME.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material connection failed: '+pin)
    uv=node(u.MaterialExpressionTextureCoordinate)
    alpha=node(u.MaterialExpressionScalarParameter,parameter_name='PulseAlpha',default_value=1.)
    phase=node(u.MaterialExpressionScalarParameter,parameter_name='PulsePhase',default_value=0.)
    custom=node(u.MaterialExpressionCustom,description='HeQue '+shader,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4,
        code=(ROOT/'Authoring'/(shader+'.hlsl')).read_text('utf8'))
    pins=[]
    for key in ('UV','Alpha','Phase'):
        pin=u.CustomInput();pin.set_editor_property('input_name',key);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for source,key in ((uv,'UV'),(alpha,'Alpha'),(phase,'Phase')):wire(source,custom,key)
    rgb=node(u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    opacity=node(u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(custom,rgb,str(ME.get_material_expression_input_names(rgb)[0]));wire(custom,opacity,str(ME.get_material_expression_input_names(opacity)[0]))
    depth=node(u.MaterialExpressionDepthFade,fade_distance_default=depth_distance)
    wire(opacity,depth,str(ME.get_material_expression_input_names(depth)[0]))
    ME.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR);ME.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    ME.recompile_material(mat);save(mat);return mat

previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE before changing HeQue assets')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue packages')
    old=PROJECT/'Content/Monsters/HeQue/BP_HeQue.uasset';backup=ROOT/'Before/BP_HeQue.uasset'
    if old.exists() and not backup.exists():shutil.copy2(old,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    if not mesh or not bp:raise RuntimeError('HeQue foundation assets missing')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=fbx(True,mesh.skeleton);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    clip=import_file(ROOT/'Export/A_HeQue_RiftPressure.fbx','A_HeQue_RiftPressure',VERSION,options,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
    report['root_units']=align_root_units(clip,mesh)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Rift animation compilation unfinished')
    save(clip);save(mesh.skeleton)
    wave_material=material('M_HeQue_PressureWave','PressureWave',12.)
    membrane=material('M_HeQue_TensionMembrane','PressureMembrane',3.)
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('auto_generate_collision',False);data.set_editor_property('combine_meshes',True)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    lens=import_file(ROOT/'Export/SM_HeQue_PressureLens.fbx','SM_HeQue_PressureLens',VERSION,options,u.FbxFactory())
    lens.set_material(0,wave_material);save(lens)
    sound=import_file(ROOT/'Audio/S_HeQue_RiftPressure.wav','S_HeQue_RiftPressure',VERSION+'/Audio',factory=u.SoundFactory())
    sound.set_editor_property('volume',1.);save(sound)
    attenuation=create('SA_HeQue_RiftPressure',VERSION+'/Audio',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation');settings.set_editor_property('attenuation_shape_extents',u.Vector(350,0,0))
    settings.set_editor_property('falloff_distance',3000.);settings.set_editor_property('spatialize',True)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for key,value in dict(rift_clip=clip,pressure_mesh=lens,pressure_material=wave_material,membrane_material=membrane,
        rift_sound=sound,rift_attenuation=attenuation,rift_damage=38.,rift_range=2400.,rift_speed=1400.,rift_cooldown=7.5).items():cdo.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'HeQue.RiftPressure','Two rising air warnings; pulses 1.55/2.15; same locked 3D line; solid geometry occludes')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='rift_pressure_saved',blueprint=bp.get_path_name(),clip=clip.get_path_name(),duration=clip.get_play_length(),
        release_times=[1.55,2.15],range_cm=2400,speed_cm_s=1400,damage_per_wave=38,pressure_diameter_cm=200)
    record();print('HEQUE_RIFT_PRESSURE_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
