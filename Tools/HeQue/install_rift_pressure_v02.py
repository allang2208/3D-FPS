"""Save HeQue Rift Pressure animation, sound, visible wave/membrane materials and bindings."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/RiftPressureV02'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/RiftPressureV02'
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
    if shader=='PressureWave':
        mat.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
        refraction=node(u.MaterialExpressionConstant,r=1.008)
        ME.connect_material_property(refraction,'',u.MaterialProperty.MP_REFRACTION)
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
    options=fbx(True,mesh.skeleton);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
    clip=import_file(ROOT/'Export/A_HeQue_RiftPressureV02.fbx','A_HeQue_RiftPressureV02',VERSION,options,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
    report['root_units']=align_root_units(clip,mesh)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Rift animation compilation unfinished')
    save(clip);save(mesh.skeleton)
    wave_material=material('M_HeQue_PressureWaveV02','PressureWave',5.)
    membrane=material('M_HeQue_TensionMembraneV02','PressureMembrane',1.5)
    mist=material('M_HeQue_PressureMistV02','PressureMist',8.)
    impact=material('M_HeQue_PressureImpactV02','PressureImpact',6.)
    dust=material('M_HeQue_PressureDustV02','PressureDust',8.)
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('auto_generate_collision',False);data.set_editor_property('combine_meshes',True)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    meshes={}
    for name,mat in (('SM_HeQue_PressureShellV02',wave_material),('SM_HeQue_TensionMembraneV02',membrane),
        ('SM_HeQue_PressureMistV02',mist),('SM_HeQue_PressureImpactV02',impact)):
        asset=import_file(ROOT/'Export'/(name+'.fbx'),name,VERSION,options,u.FbxFactory())
        asset.set_material(0,mat);save(asset);meshes[name]=asset
    releases=[]
    for seconds in (1.55,2.15):
        pose=pose_at(clip,mesh,seconds)
        releases.append(u.AnimPoseExtensions.get_bone_pose(pose,'Bone_000',u.AnimPoseSpaces.WORLD).translation)
    sound=import_file(ROOT/'Audio/S_HeQue_RiftPressureV02.wav','S_HeQue_RiftPressureV02',VERSION+'/Audio',factory=u.SoundFactory())
    sound.set_editor_property('volume',1.);save(sound)
    attenuation=create('SA_HeQue_RiftPressureV02V02',VERSION+'/Audio',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation');settings.set_editor_property('attenuation_shape_extents',u.Vector(350,0,0))
    settings.set_editor_property('falloff_distance',3000.);settings.set_editor_property('spatialize',True)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    hit_sound=import_file(ROOT/'Audio/S_HeQue_PressureImpactV02.wav','S_HeQue_PressureImpactV02',VERSION+'/Audio',factory=u.SoundFactory())
    hit_sound.set_editor_property('volume',.8);save(hit_sound)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    for key,value in dict(rift_clip=clip,pressure_mesh=meshes['SM_HeQue_PressureShellV02'],pressure_material=wave_material,
        pressure_membrane_mesh=meshes['SM_HeQue_TensionMembraneV02'],membrane_material=membrane,
        pressure_mist_mesh=meshes['SM_HeQue_PressureMistV02'],pressure_mist_material=mist,
        pressure_impact_mesh=meshes['SM_HeQue_PressureImpactV02'],pressure_impact_material=impact,pressure_dust_material=dust,
        rift_release_points=releases,rift_sound=sound,rift_impact_sound=hit_sound,rift_attenuation=attenuation).items():cdo.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'HeQue.RiftPressure','V02: 56cm thick pressure shells, individual animated origins, 1.55/2.15 releases, 27/30cm recoil, surface impact and conditional dust')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='rift_pressure_v02_saved',blueprint=bp.get_path_name(),clip=clip.get_path_name(),duration=clip.get_play_length(),
        release_times=[1.55,2.15],range_cm=float(cdo.get_editor_property('rift_range')),speed_cm_s=float(cdo.get_editor_property('rift_speed')),
        damage_per_wave=float(cdo.get_editor_property('rift_damage')),pressure_diameter_cm=200,pressure_depth_cm=56,
        release_points=[[p.x,p.y,p.z] for p in releases],fixed_mesh_components=12)
    record();print('HEQUE_RIFT_PRESSURE_V02_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
