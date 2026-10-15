"""Import and save the complete suspended-heart spell on the existing HeQue actor."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/PsychicV01'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/PsychicV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary;P=u.AnimPoseExtensions
report=dict(stage='importing',saved=[],gameplay_tested=False,visual_tested=False,audio_auditioned=False,multiplayer_tested=False)
RECEIPT=ROOT/'Records/ue-import.json'
helpers=ast.parse((PROJECT/'Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'HeQue/psychic_import','exec'))

def node(mat,cls,**props):
    n=ME.create_material_expression(mat,cls)
    for key,value in props.items():n.set_editor_property(key,value)
    return n
def wire(a,output,b,pin):
    if not ME.connect_material_expressions(a,output,b,pin):raise RuntimeError('Material connection failed: '+pin)
def custom(mat,shader,sources,result):
    c=node(mat,u.MaterialExpressionCustom,description='HeQue '+shader,output_type=result,
        code=(ROOT/'Authoring'/(shader+'.hlsl')).read_text('utf8'))
    inputs=[]
    for name in sources:
        entry=u.CustomInput();entry.set_editor_property('input_name',name);inputs.append(entry)
    c.set_editor_property('inputs',inputs)
    for name,(source,output) in sources.items():wire(source,output,c,name)
    return c
def surface_material(name,shader,mask=None):
    mat=create(name,VERSION+'/Materials',u.Material,u.MaterialFactoryNew());ME.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True);mat.set_editor_property('disable_depth_test',False)
    if mask:mat.set_editor_property('used_with_skeletal_mesh',True)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    alpha=node(mat,u.MaterialExpressionScalarParameter,parameter_name='PulseAlpha',default_value=0.)
    phase=node(mat,u.MaterialExpressionScalarParameter,parameter_name='PulsePhase',default_value=0.)
    sources={'UV':(uv,''),'Alpha':(alpha,''),'Phase':(phase,'')}
    if mask:
        sample=node(mat,u.MaterialExpressionTextureSample,texture=mask,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        sources['Mask']=(sample,'R')
    else:sources['Rim']=(node(mat,u.MaterialExpressionFresnel),'')
    c=custom(mat,shader,sources,u.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    opacity=node(mat,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(c,'',rgb,str(ME.get_material_expression_input_names(rgb)[0]));wire(c,'',opacity,str(ME.get_material_expression_input_names(opacity)[0]))
    ME.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    if mask:
        # Overlay lies on the original opaque skin. DepthFade here would erase
        # the organ glow because the two surfaces share the same depth.
        ME.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    else:
        depth=node(mat,u.MaterialExpressionDepthFade,fade_distance_default=8.)
        wire(opacity,'',depth,str(ME.get_material_expression_input_names(depth)[0]))
        ME.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
        mat.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
        refraction=node(mat,u.MaterialExpressionConstant,r=1.009)
        ME.connect_material_property(refraction,'',u.MaterialProperty.MP_REFRACTION)
    ME.recompile_material(mat);save(mat);return mat
def view_material():
    mat=create('M_HeQue_FearViewV01',VERSION+'/Materials',u.Material,u.MaterialFactoryNew());ME.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_POST_PROCESS)
    mat.set_editor_property('blendable_location',u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    scene=node(mat,u.MaterialExpressionSceneTexture,scene_texture_id=u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    uv=node(mat,u.MaterialExpressionScreenPosition)
    strength=node(mat,u.MaterialExpressionScalarParameter,parameter_name='FearStrength',default_value=0.)
    phase=node(mat,u.MaterialExpressionScalarParameter,parameter_name='FearPhase',default_value=0.)
    c=custom(mat,'PsychicFearView',{'SceneColor':(scene,'Color'),'UV':(uv,'ViewportUV'),'Strength':(strength,''),'Phase':(phase,'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    ME.connect_material_property(c,'',u.MaterialProperty.MP_EMISSIVE_COLOR);ME.recompile_material(mat);save(mat);return mat

def values(v):return [v.x,v.y,v.z]
def sub(a,b):return [x-y for x,y in zip(a,b)]
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue packages')
    for relative in ('BP_HeQue.uasset','RigV01/SK_HeQue_Skeleton.uasset'):
        source=PROJECT/'Content/Monsters/HeQue'/relative;backup=ROOT/'Before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
        if source.exists() and not backup.exists():shutil.copy2(source,backup)
    mesh=u.load_asset(DEST+'/RigV01/SK_HeQue');bp=u.load_asset(DEST+'/BP_HeQue')
    if not mesh or not bp:raise RuntimeError('Delivered HeQue assets missing')
    authored=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=fbx(True,mesh.skeleton);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',authored['fps'])
    clip=import_file(ROOT/'Export'/(authored['clip']+'.fbx'),authored['clip'],VERSION,options,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False);clip.set_preview_skeletal_mesh(mesh)
    report['root_units']=align_root_units(clip,mesh)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Psychic animation compilation unfinished')
    save(clip);save(mesh.skeleton)
    first=pose_at(clip,mesh,0.);names=list(authored['reference_heads']);src=[authored['reference_heads'][n] for n in names]
    dst=[values(P.get_ref_bone_pose(first,n,u.AnimPoseSpaces.WORLD).translation) for n in names]
    a,b,c=[sub(v,src[0]) for v in src[1:]];det=dot(a,cross(b,c))
    if abs(det)<1e-8:raise RuntimeError('Degenerate rig conversion basis')
    def imported(position):
        v=sub(position,src[0]);coeff=[dot(v,cross(b,c))/det,dot(v,cross(c,a))/det,dot(v,cross(a,b))/det]
        return u.Vector(*[dst[0][j]+sum(coeff[k]*(dst[k+1][j]-dst[0][j]) for k in range(3)) for j in range(3)])
    ref=P.get_ref_bone_pose(first,'Bone_000',u.AnimPoseSpaces.WORLD)
    core_offset=u.MathLibrary.inverse_transform_location(ref,imported(authored['core_center_source']))
    releases=[]
    for seconds in authored['releases']:
        pose=pose_at(clip,mesh,seconds);frame=P.get_bone_pose(pose,'Bone_000',u.AnimPoseSpaces.WORLD)
        releases.append(u.MathLibrary.transform_location(frame,core_offset))
    mask=import_file(ROOT/'Textures/T_HeQue_CoreMaskV01.png','T_HeQue_CoreMaskV01',VERSION+'/Textures')
    mask.set_editor_property('srgb',False);mask.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS);save(mask)
    core_material=surface_material('M_HeQue_PsychicCoreV01','PsychicCore',mask)
    wave_material=surface_material('M_HeQue_PsychicWaveV01','PsychicWave');fear_material=view_material()
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('auto_generate_collision',False);data.set_editor_property('combine_meshes',True)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    wave_mesh=import_file(ROOT/'Export/SM_HeQue_PsychicShellV01.fbx','SM_HeQue_PsychicShellV01',VERSION,options,u.FbxFactory())
    wave_mesh.set_material(0,wave_material);save(wave_mesh)
    sound=import_file(ROOT/'Audio/S_HeQue_PsychicHeartV01.wav','S_HeQue_PsychicHeartV01',VERSION+'/Audio',factory=u.SoundFactory());save(sound)
    ear=import_file(ROOT/'Audio/S_HeQue_FearEarV01.wav','S_HeQue_FearEarV01',VERSION+'/Audio',factory=u.SoundFactory());save(ear)
    attenuation=create('SA_HeQue_PsychicV01',VERSION+'/Audio',u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=attenuation.get_editor_property('attenuation');settings.set_editor_property('attenuation_shape_extents',u.Vector(300,0,0))
    settings.set_editor_property('falloff_distance',1800.);settings.set_editor_property('spatialize',True)
    attenuation.set_editor_property('attenuation',settings);save(attenuation)
    body_slot=next((i for i,s in enumerate(mesh.materials) if s.material_interface and 'Body' in s.material_interface.get_name()),None)
    if body_slot is None:raise RuntimeError('Cannot identify the real flesh material slot')
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    bindings=dict(psychic_clip=clip,psychic_wave_mesh=wave_mesh,psychic_wave_material=wave_material,psychic_core_material=core_material,
        psychic_fear_view_material=fear_material,psychic_sound=sound,psychic_fear_sound=ear,psychic_attenuation=attenuation,
        psychic_release_points=releases,psychic_core_offset=core_offset,psychic_body_material_slot=body_slot,
        psychic_radius=authored['radius_cm'],psychic_damage=authored['damage_per_wave'],psychic_cooldown=authored['cooldown'])
    for key,value in bindings.items():cdo.set_editor_property(key,value)
    LIB.set_metadata_tag(bp,'HeQue.Psychic','Suspended heart: 1.60/2.20/2.80s three 10m waves, 25 magic each, one 3s fear per cast, recovery through 5.20s')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='psychic_heart_v01_saved',blueprint=bp.get_path_name(),clip=clip.get_path_name(),duration=clip.get_play_length(),
        releases=authored['releases'],release_points=[values(v) for v in releases],core_offset=values(core_offset),body_slot=body_slot,
        radius_cm=float(cdo.get_editor_property('psychic_radius')),damage_per_wave=float(cdo.get_editor_property('psychic_damage')),
        fear_seconds=3,fear_applications_per_cast=1,cooldown=float(cdo.get_editor_property('psychic_cooldown')),f6_id='HeQue')
    record();print('HEQUE_PSYCHIC_HEART_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
