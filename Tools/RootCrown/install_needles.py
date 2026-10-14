"""Install only the second attack and the requested doubled melee coverage."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/NeedlesV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'importing_needles','saved':[],'runtime_tested':False,'audio_auditioned':False}
RECEIPT=ROOT/'Reports/ue-needles-import.json'
source=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'RootCrown/import_helpers','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; preserve it before asset integration')
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]
    if dirty:raise RuntimeError('Root Crown has unsaved packages: '+str(dirty))
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    body=u.load_asset(DEST+'/RigV01/SK_RootCrown');opts=fbx(True,body.skeleton)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    clip=import_file(ROOT/'Exports/NeedlesV01/A_RootCrown_NeedleFan_V01.fbx','A_RootCrown_NeedleFan_V01',VERSION,opts,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False)
    clip.set_preview_skeletal_mesh(body);align_root_units(clip,body)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compression did not finish')
    save(clip);save(body.skeleton)
    opts=u.FbxImportUI();opts.set_editor_property('automated_import_should_detect_type',False)
    opts.set_editor_property('mesh_type_to_import',u.FBXImportType.FBXIT_STATIC_MESH)
    opts.set_editor_property('import_as_skeletal',False);opts.set_editor_property('import_mesh',True)
    opts.set_editor_property('import_animations',False);opts.set_editor_property('import_materials',False);opts.set_editor_property('import_textures',False)
    data=opts.get_editor_property('static_mesh_import_data')
    data.set_editor_property('convert_scene',True);data.set_editor_property('convert_scene_unit',True)
    data.set_editor_property('auto_generate_collision',False)
    data.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    needle=import_file(ROOT/'Exports/NeedlesV01/SM_RootCrownNeedle.fbx','SM_RootCrownNeedle',VERSION,opts,u.FbxFactory())
    mat=create('M_RootCrownNeedle',VERSION,u.Material,u.MaterialFactoryNew())
    ME.delete_all_material_expressions(mat)
    slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    color=ME.create_material_expression(mat,u.MaterialExpressionVertexColor)
    rough=ME.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.48)
    specular=ME.create_material_expression(mat,u.MaterialExpressionConstant);specular.set_editor_property('r',.25)
    # VertexColor's first output is the unnamed RGB mask in this engine build.
    for node,output,pin,prop in [(color,'','BaseColor',u.MaterialProperty.MP_BASE_COLOR),(rough,'','Roughness',u.MaterialProperty.MP_ROUGHNESS),(specular,'','Specular',u.MaterialProperty.MP_SPECULAR)]:
        if not ME.connect_material_expressions(node,output,slab,pin):raise RuntimeError('Needle material input failed: '+pin)
        ME.connect_material_property(node,output,prop)
    if not ME.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Needle surface output failed')
    errors=list(ME.recompile_material(mat))
    if errors:raise RuntimeError('Needle material compile failed: '+str(errors))
    ME.get_statistics(mat);save(mat)
    needle.set_material(0,mat);save(needle)
    sounds={}
    for role in ('Gesture','Impact'):
        sounds[role]=import_file(ROOT/'Audio/NeedlesV01'/('RootCrown_Needle'+role+'.wav'),'S_RootCrown_Needle'+role,VERSION+'/Audio')
        save(sounds[role])
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    # Preserve the repaired body material and the accepted fast melee clip.
    for prop,value in [('needle_clip',clip),('needle_mesh',needle),('needle_material',mat),('needle_gesture_sound',sounds['Gesture']),('needle_impact_sound',sounds['Impact']),('needle_damage',24.),('needle_cooldown',8.),('needle_min_range',600.),('needle_max_range',1800.),('needle_speed',1600.),('slash_trigger_range',800.),('slash_hit_radius',44.),('slash_reach_scale',2.)]:defaults.set_editor_property(prop,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='needle_assets_and_doubled_slash_saved',blueprint=bp.get_path_name(),needle_clip=clip.get_path_name(),needle_duration=clip.get_play_length(),shots=[1.4,1.7,2.0],pins_per_wave=5,damage_per_player_per_wave=24,needle_range_cm=[600,1800],needle_speed_cm_s=1600,needle_cooldown=8,slash_horizontal_scale=2,slash_contact_radius_cm=44,slash_trigger_cap_cm=800,preserved_slash_clip=defaults.get_editor_property('slash_clip').get_path_name(),preserved_body_material=defaults.get_editor_property('slash_material').get_path_name())
    record();print('ROOT_CROWN_NEEDLES_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
