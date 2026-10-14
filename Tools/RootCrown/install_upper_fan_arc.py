"""Save the upper-fan needle animation and the contact-driven white slash arc."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'importing_upper_fan_and_white_arc','saved':[],'gameplay_tested':False,'rendered':False}
RECEIPT=ROOT/'Reports/ue-upper-fan-arc-import.json'
source=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'RootCrown/import_helpers','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')

def node(mat,cls,**props):
    expression=ME.create_material_expression(mat,cls)
    for key,value in props.items():expression.set_editor_property(key,value)
    return expression

def wire(a,b,pin=''):
    if not ME.connect_material_expressions(a,'',b,pin):raise RuntimeError('White arc material input failed: '+pin)

try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; preserve it before asset integration')
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]
    if dirty:raise RuntimeError('Root Crown has unsaved packages: '+str(dirty))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    body=u.load_asset(DEST+'/RigV01/SK_RootCrown');opts=fbx(True,body.skeleton)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    clip=import_file(ROOT/'Exports/NeedlesV02/A_RootCrown_NeedleFan_V02.fbx','A_RootCrown_NeedleFan_V02',DEST+'/NeedlesV02',opts,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False)
    clip.set_preview_skeletal_mesh(body);report['root_units']=align_root_units(clip,body)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compression did not finish')
    save(clip);save(body.skeleton)

    material=create('M_RootCrownWhiteArc',DEST+'/SlashVfxV01',u.Material,u.MaterialFactoryNew())
    for expression in list(ME.get_material_expressions(material)):ME.delete_material_expression(material,expression)
    material.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    material.set_editor_property('two_sided',True)
    material.set_editor_property('disable_depth_test',False)
    inputs={'UV':node(material,u.MaterialExpressionTextureCoordinate),
            'Exposure':node(material,u.MaterialExpressionEyeAdaptation),
            'Seconds':node(material,u.MaterialExpressionScalarParameter,parameter_name='Seconds',default_value=0.),
            'Opacity':node(material,u.MaterialExpressionScalarParameter,parameter_name='Opacity',default_value=0.)}
    code='''
float v=saturate(UV.y);
float core=exp(-pow((v-0.70)/0.085,2.0));
float halo=pow(saturate(sin(v*3.14159265)),2.0)*0.16;
float streak=0.75+0.25*sin(UV.x*72.0-Seconds*45.0);
float ends=smoothstep(0.0,0.08,UV.x)*(1.0-smoothstep(0.92,1.0,UV.x));
float alpha=(core*0.85+halo*streak)*ends*saturate(Opacity);
float3 white=float3(0.96,0.985,1.0)*(3.2+core*2.0)/max(0.06,Exposure);
return float4(white,alpha);
'''
    custom=node(material,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    custom.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,custom,name)
    rgb=node(material,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=node(material,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(custom,rgb);wire(custom,alpha)
    depth=node(material,u.MaterialExpressionDepthFade,fade_distance_default=4.)
    wire(alpha,depth,str(ME.get_material_expression_input_names(depth)[0]))
    if not ME.connect_material_property(rgb,'',u.MaterialProperty.MP_EMISSIVE_COLOR):raise RuntimeError('White arc emissive output failed')
    if not ME.connect_material_property(depth,'',u.MaterialProperty.MP_OPACITY):raise RuntimeError('White arc opacity output failed')
    errors=list(ME.recompile_material(material))
    if errors:raise RuntimeError('White arc material compile failed: '+str(errors))
    ME.get_statistics(material);save(material)

    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    defaults.set_editor_property('needle_clip',clip);defaults.set_editor_property('slash_arc_material',material)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    outlets=json.loads((ROOT/'Exports/NeedlesV02/outlets.json').read_text('utf8'))
    report.update(stage='upper_fan_and_white_arc_saved',needle_clip=clip.get_path_name(),duration=clip.get_play_length(),
                  outlets=outlets['outlets'],blade_rotation_degrees=outlets['blade_rotation_degrees'],
                  arc_material=material.get_path_name(),arc_source='same SlashFrames, SlashPointWorld, SlashReachScale and SlashHitRadius as damage',
                  arc_afterglow_seconds=.22,shots=[1.4,1.7,2.0],
                  preserved_slash_clip=defaults.get_editor_property('slash_clip').get_path_name(),
                  preserved_body_material=defaults.get_editor_property('slash_material').get_path_name(),
                  slash_reach_scale=defaults.get_editor_property('slash_reach_scale'),slash_hit_radius_cm=defaults.get_editor_property('slash_hit_radius'))
    record();print('ROOT_CROWN_UPPER_FAN_ARC_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
