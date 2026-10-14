"""Save the third attack as proximity mines and author its radius-matched signal material."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/MinesV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
RECEIPT=ROOT/'Reports/ue-mines-import.json'
report={'stage':'authoring_mine_signal','saved':[],'gameplay_tested':False,'multiplayer_tested':False,'rendered':False}
def helpers(path,names):
    tree=ast.parse(Path(path).read_text('utf8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'RootCrown/mine_helpers','exec'),globals())
helpers('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py',('record','save','create','import_file'))
helpers('D:/FPS3D/FPSGAME/Tools/RootCrown/install_roots.py',('node','wire','output','custom','material','finish'))
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved Root Crown assets')
    signal=material('M_RootCrownMineSignal')
    signal.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE)
    signal.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
    signal.set_editor_property('disable_depth_test',False)
    inputs={'UV':node(signal,u.MaterialExpressionTextureCoordinate),'Exposure':node(signal,u.MaterialExpressionEyeAdaptation)}
    inputs['Radius']=node(signal,u.MaterialExpressionScalarParameter,parameter_name='Radius',default_value=.5)
    inputs['Opacity']=node(signal,u.MaterialExpressionScalarParameter,parameter_name='Opacity',default_value=.18)
    inputs['Tint']=node(signal,u.MaterialExpressionVectorParameter,parameter_name='Tint',default_value=u.LinearColor(.5,.025,.018,1))
    paint=custom(signal,'''float2 p=(UV-.5)*2.0;float r=length(p);
float width=.018;float ring=1.0-smoothstep(width,width+.012,abs(r-Radius));
float spokes=pow(saturate(cos(atan2(p.y,p.x+1e-5)*12.0)),18.0);
float fill=(1.0-smoothstep(Radius-.08,Radius,r))*.035;
float marker=ring*(.7+.3*spokes)+fill;
float alpha=saturate(marker*Opacity)*(1.0-smoothstep(1.005,1.02,r));
return float4(Tint.rgb*(1.3+ring*2.0)/max(.08,Exposure),alpha);''',inputs,u.CustomMaterialOutputType.CMOT_FLOAT4)
    rgb=node(signal,u.MaterialExpressionComponentMask,r=True,g=True,b=True,a=False)
    alpha=node(signal,u.MaterialExpressionComponentMask,r=False,g=False,b=False,a=True)
    wire(paint,rgb);wire(paint,alpha);output(rgb,u.MaterialProperty.MP_EMISSIVE_COLOR);output(alpha,u.MaterialProperty.MP_OPACITY);finish(signal)
    planting=import_file(ROOT/'Audio/MinesV01/RootCrown_MinePlant.wav','S_RootCrownMinePlant',VERSION+'/Audio');save(planting)
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    # The new fragments are instanced meshes; author their shader usage before gameplay.
    flesh=defaults.get_editor_property('root_flesh_material')
    ME.set_material_usage(flesh,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES);finish(flesh)
    for key,value in {'mine_signal_material':signal,'root_gesture_sound':planting,'mine_trigger_radius':140.,'mine_blast_radius':280.,'mine_fuse_seconds':.45,
                      'mine_lifetime':25.,'root_damage':60.,'root_knot_health':80.,'root_cooldown':14.}.items():defaults.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='mines_saved',blueprint=bp.get_path_name(),mines_per_cast=3,maximum_groups=1,arming_seconds=2.,
                  trigger_radius_cm=140,blast_radius_cm=280,fuse_seconds=.45,lifetime_seconds=25,maximum_blast_damage=60,edge_damage_fraction=.35,
                  accepted_hit_cripple_seconds=5,cripple_movement_reduction=.5,
                  mine_health=80,shooting='neutralizes without damaging explosion',boss_death='clears remaining mines',
                  material=signal.get_path_name(),fragment_material=flesh.get_path_name(),planting_sound=planting.get_path_name(),burst_fx='FPSImpactFXSubsystem.SpawnSacRupture: shared pressure wave, dust, blood mist and droplets',
                  fragments_per_mine=10,burst_visual_seconds=1.2,preserved_body_material=defaults.get_editor_property('slash_material').get_path_name(),
                  preserved_animation=defaults.get_editor_property('root_clip').get_path_name(),
                  entry='RootCrownRig / 根冠 M-01')
    record();print('ROOT_CROWN_MINES_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
