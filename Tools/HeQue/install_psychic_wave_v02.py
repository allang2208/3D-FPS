"""Save the smooth layered front and explicit 120 degree/s HeQue turn speed."""
import ast,json,shutil,traceback
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/PsychicWaveV02'
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/PsychicWaveV02'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report=dict(stage='importing',saved=[],gameplay_tested=False,visual_tested=False)
RECEIPT=ROOT/'Records/ue-import.json'
for path,names in (('Tools/RootCrown/install.py',('record','save','create','import_file')),
    ('Tools/HeQue/install_psychic_v01.py',('node','wire','custom'))):
    tree=ast.parse((PROJECT/path).read_text('utf8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'HeQue/psychic_front_import','exec'))

def build_material(flow):
    mat=create('M_HeQue_PsychicFrontV02',VERSION+'/Materials',u.Material,u.MaterialFactoryNew());ME.delete_all_material_expressions(mat)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided',True);mat.set_editor_property('disable_depth_test',False)
    mat.set_editor_property('enable_responsive_aa',True)
    def scalar(name,default):return node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=default)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    texture=node(mat,u.MaterialExpressionTextureObjectParameter,parameter_name='FlowTex',texture=flow,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    alpha=scalar('PulseAlpha',0.);phase=scalar('PulsePhase',0.);seed=scalar('WaveSeed',0.);radius=scalar('WaveRadiusCm',100.)
    color=node(mat,u.MaterialExpressionVertexColor)
    normal=node(mat,u.MaterialExpressionPixelNormalWS);view=node(mat,u.MaterialExpressionCameraVectorWS)
    sources={'UV':(uv,''),'FlowTex':(texture,''),'Alpha':(alpha,''),'Phase':(phase,''),'Seed':(seed,''),
        'Layer':(color,''),'NormalWS':(normal,''),'View':(view,'')}
    c=custom(mat,'PsychicFront',sources,u.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(mat,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    opacity=node(mat,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(c,'',rgb,str(ME.get_material_expression_input_names(rgb)[0]));wire(c,'',opacity,str(ME.get_material_expression_input_names(opacity)[0]))
    depth=node(mat,u.MaterialExpressionDepthFade,fade_distance_default=12.)
    wire(opacity,'',depth,str(ME.get_material_expression_input_names(depth)[0]))
    ME.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    ME.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY)
    offset=custom(mat,'PsychicFrontOffset',{'Layer':(color,''),'Radius':(radius,''),
        'NormalWS':(node(mat,u.MaterialExpressionVertexNormalWS),'')},u.CustomMaterialOutputType.CMOT_FLOAT3)
    ME.connect_material_property(offset,'',u.MaterialProperty.MP_WORLD_POSITION_OFFSET)
    mat.set_editor_property('refraction_method',u.RefractionMode.RM_INDEX_OF_REFRACTION)
    mat.set_editor_property('refraction_depth_bias',2.)
    refraction=custom(mat,'PsychicFrontRefraction',{'Layer':(color,''),'Alpha':(alpha,'')},u.CustomMaterialOutputType.CMOT_FLOAT1)
    ME.connect_material_property(refraction,'',u.MaterialProperty.MP_REFRACTION)
    ME.recompile_material(mat);save(mat);return mat

previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue packages')
    before=ROOT/'Before/BP_HeQue.uasset';source=PROJECT/'Content/Monsters/HeQue/BP_HeQue.uasset'
    if source.exists() and not before.exists():shutil.copy2(source,before)
    bp=u.load_asset(DEST+'/BP_HeQue')
    if not bp:raise RuntimeError('Original HeQue Blueprint missing')
    authored=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    flow=import_file(ROOT/'Textures/T_HeQue_PsychicFlowV02.png','T_HeQue_PsychicFlowV02',VERSION+'/Textures')
    flow.set_editor_property('srgb',False);flow.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7)
    flow.set_editor_property('address_x',u.TextureAddress.TA_WRAP);flow.set_editor_property('address_y',u.TextureAddress.TA_CLAMP)
    save(flow);mat=build_material(flow)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=False;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('auto_generate_collision',False);data.set_editor_property('combine_meshes',True)
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    mesh=import_file(ROOT/'Export/SM_HeQue_PsychicFrontV02.fbx','SM_HeQue_PsychicFrontV02',VERSION,options,u.FbxFactory())
    mesh.set_material(0,mat);save(mesh)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    report['previous']=dict(turn_speed=float(cdo.get_editor_property('turn_speed')),
        wave_mesh=cdo.get_editor_property('psychic_wave_mesh').get_path_name(),
        wave_material=cdo.get_editor_property('psychic_wave_material').get_path_name())
    cdo.set_editor_property('turn_speed',120.);cdo.set_editor_property('psychic_wave_mesh',mesh);cdo.set_editor_property('psychic_wave_material',mat)
    LIB.set_metadata_tag(bp,'HeQue.PsychicWave','V02: smooth refractive front; seamless warped flow and eroding fixed-width wake; 3 reused components; original damage clock')
    LIB.set_metadata_tag(bp,'HeQue.Turning','120 deg/s cap, acceleration and braking, distance-matched turn animation')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='psychic_wave_v02_turn120_saved',blueprint=bp.get_path_name(),turn_speed_degrees_per_second=float(cdo.get_editor_property('turn_speed')),
        material=mat.get_path_name(),mesh=mesh.get_path_name(),texture=flow.get_path_name(),triangles=authored['triangles'],
        fixed_components=3,layer_offsets_cm=authored['layer_offsets_cm'],damage_radius_cm=float(cdo.get_editor_property('psychic_radius')),
        wave_damage=float(cdo.get_editor_property('psychic_damage')),fade_seconds=.24,original_animation_preserved=cdo.get_editor_property('psychic_clip').get_path_name())
    record();print('HEQUE_PSYCHIC_WAVE_V02_SAVED '+json.dumps(report,ensure_ascii=False),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
