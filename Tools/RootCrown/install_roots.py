"""Import and save the third Root Crown attack; preserve the two existing moves."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/RootsV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'importing_root_enclosure','saved':[],'gameplay_tested':False,'multiplayer_tested':False}
RECEIPT=ROOT/'Reports/ue-roots-import.json'
source=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'RootCrown/import_helpers','exec'))

def node(mat,cls,**props):
    result=ME.create_material_expression(mat,cls)
    for key,value in props.items():result.set_editor_property(key,value)
    return result
def wire(a,b,pin=''):
    if not ME.connect_material_expressions(a,'',b,pin):raise RuntimeError('Root material input failed: '+pin)
def output(a,prop):
    if not ME.connect_material_property(a,'',prop):raise RuntimeError('Root material output failed: '+str(prop))
def custom(mat,code,inputs,kind):
    result=node(mat,u.MaterialExpressionCustom,code=code,output_type=kind)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    result.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,result,name)
    return result
def material(name):
    result=create(name,VERSION,u.Material,u.MaterialFactoryNew())
    for e in list(ME.get_material_expressions(result)):ME.delete_material_expression(result,e)
    result.set_editor_property('two_sided',True);return result
def finish(mat):
    errors=list(ME.recompile_material(mat))
    if errors:raise RuntimeError('Root material compile failed: '+str(errors))
    ME.get_statistics(mat);save(mat)

previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; preserve it before asset integration')
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]
    if dirty:raise RuntimeError('Root Crown has unsaved packages: '+str(dirty))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    body=u.load_asset(DEST+'/RigV01/SK_RootCrown');opts=fbx(True,body.skeleton)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    clip=import_file(ROOT/'Exports/RootsV01/A_RootCrown_RootEnclosure_V01.fbx','A_RootCrown_RootEnclosure_V01',VERSION,opts,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False)
    clip.set_preview_skeletal_mesh(body);report['root_units']=align_root_units(clip,body)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Root animation compression did not finish')
    save(clip);save(body.skeleton)
    opts=u.FbxImportUI();opts.set_editor_property('automated_import_should_detect_type',False)
    opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
    for key,value in [('import_as_skeletal',False),('import_mesh',True),('import_animations',False),('import_materials',False),('import_textures',False)]:opts.set_editor_property(key,value)
    data=opts.get_editor_property('static_mesh_import_data')
    for key,value in [('convert_scene',True),('convert_scene_unit',True),('auto_generate_collision',False),('vertex_color_import_option',u.VertexColorImportOption.REPLACE)]:data.set_editor_property(key,value)
    knot=import_file(ROOT/'Exports/RootsV01/SM_RootCrownKnot.fbx','SM_RootCrownKnot',VERSION,opts,u.FbxFactory())

    flesh=material('M_RootCrownRootFlesh')
    uv=node(flesh,u.MaterialExpressionTextureCoordinate);color=node(flesh,u.MaterialExpressionVertexColor)
    rise=node(flesh,u.MaterialExpressionScalarParameter,parameter_name='Rise',default_value=1.)
    signal=node(flesh,u.MaterialExpressionScalarParameter,parameter_name='Signal',default_value=0.)
    skin=custom(flesh,'''float3 skin=lerp(float3(.24,.075,.06),float3(.58,.45,.36),pow(saturate(UV.y),2.0));
float vein=smoothstep(.92,1.0,sin(UV.x*118.0+sin(UV.y*15.0)*2.0));
return lerp(skin,float3(.09,.12,.17),vein*.45)*lerp(float3(.7,.7,.7),Color.rgb,.6);''',{'UV':uv,'Color':color},u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(skin,u.MaterialProperty.MP_BASE_COLOR)
    output(node(flesh,u.MaterialExpressionConstant,r=.36),u.MaterialProperty.MP_ROUGHNESS)
    output(node(flesh,u.MaterialExpressionConstant,r=.42),u.MaterialProperty.MP_SPECULAR)
    glow=custom(flesh,'return float3(.65,.035,.015)*Signal;',{'Signal':signal},u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(glow,u.MaterialProperty.MP_EMISSIVE_COLOR)
    displacement=custom(flesh,'return float3(0,0,(saturate(Rise)-1.0)*UV.y*80.0);',{'UV':uv,'Rise':rise},u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(displacement,u.MaterialProperty.MP_WORLD_POSITION_OFFSET);finish(flesh)
    knot.set_material(0,flesh);save(knot)

    warning=material('M_RootCrownVeinWarning')
    warning.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    warning.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    warning.set_editor_property('disable_depth_test',False)
    inputs={'UV':node(warning,u.MaterialExpressionTextureCoordinate),'Exposure':node(warning,u.MaterialExpressionEyeAdaptation)}
    for name,value in [('Opacity',0.),('Growth',0.),('Seconds',0.)]:inputs[name]=node(warning,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    code='''float center=exp(-pow((UV.y-.5)/.12,2.0));
float branch=exp(-pow((abs(UV.y-.5)-(.19+.09*sin(UV.x*43.0)))/.045,2.0));
float silhouette=(center+branch*.4)*pow(saturate(sin(UV.y*3.14159265)),.3);
float reveal=1.0-smoothstep(Growth-.04,Growth,UV.x);
float pulse=.7+.3*sin(UV.x*38.0-Seconds*12.0);
float alpha=saturate(silhouette*Opacity*reveal*pulse);
return float4(lerp(float3(.65,.015,.008),float3(1.0,.30,.16),center)*3.5/max(.08,Exposure),alpha);'''
    paint=custom(warning,code,inputs,u.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(warning,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=node(warning,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(paint,rgb);wire(paint,alpha)
    output(rgb,u.MaterialProperty.MP_EMISSIVE_COLOR);output(alpha,u.MaterialProperty.MP_OPACITY);finish(warning)

    sounds={}
    for role in ('RootGesture','KnotBreak'):
        sounds[role]=import_file(ROOT/'Audio/RootsV01'/('RootCrown_'+role+'.wav'),'S_RootCrown_'+role,VERSION+'/Audio');save(sounds[role])
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    for key,value in [('root_clip',clip),('root_knot_mesh',knot),('root_flesh_material',flesh),('root_warning_material',warning),('root_gesture_sound',sounds['RootGesture']),('root_break_sound',sounds['KnotBreak']),('root_damage',45.),('root_knot_health',80.),('root_cooldown',14.)]:defaults.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='root_enclosure_saved',animation=clip.get_path_name(),duration=clip.get_play_length(),knot_mesh=knot.get_path_name(),warning_seconds=2.,release_times=[2.,2.35,2.7],area_radius_cm=250,damage_per_edge=45,knot_health=80,slow_percent=.35,slow_seconds=2,cooldown=14,maximum_groups=1,
                  preserved_needle_clip=defaults.get_editor_property('needle_clip').get_path_name(),preserved_slash_clip=defaults.get_editor_property('slash_clip').get_path_name(),preserved_body_material=defaults.get_editor_property('slash_material').get_path_name())
    record();print('ROOT_CROWN_ROOTS_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
