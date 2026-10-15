"""Import the refined HeQue body, rigid chain and basic animation set; save the F6 blueprint."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HeQueBoss20261014/RigV01')
DEST='/Game/Monsters/HeQue';VERSION=DEST+'/RigV01'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'importing','saved':[],'gameplay_tested':False,'multiplayer_tested':False,'attacks_implemented':False}
RECEIPT=ROOT/'Records/ue-import.json'
helpers=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','create','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'HeQue/import_helpers','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE is active; preserve the user session before HeQue asset integration')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved HeQue assets')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    mesh=import_file(ROOT/'Export/SK_HeQue.fbx','SK_HeQue',VERSION,fbx(),u.FbxFactory())
    for asset in (mesh,mesh.skeleton,mesh.physics_asset):
        if asset:save(asset)
    textures={}
    for role in ('BaseColor','Normal','MetallicRoughness'):
        tex=import_file(ROOT/'Textures'/('T_HeQue_'+role+'.png'),'T_HeQue_'+role,VERSION+'/Textures')
        tex.set_editor_property('srgb',role=='BaseColor')
        if role=='Normal':
            tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
        elif role=='MetallicRoughness':tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
        save(tex);textures[role]=tex
    mat=create('M_HeQue_Body',VERSION+'/Materials',u.Material,u.MaterialFactoryNew())
    ME.delete_all_material_expressions(mat);mat.set_editor_property('used_with_skeletal_mesh',True);mat.set_editor_property('two_sided',True)
    slab=ME.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    for role,pin,prop,ch in [('BaseColor','BaseColor',u.MaterialProperty.MP_BASE_COLOR,'RGB'),('Normal','Normal',u.MaterialProperty.MP_NORMAL,'RGB'),('MetallicRoughness','Roughness',u.MaterialProperty.MP_ROUGHNESS,'G'),('MetallicRoughness','Metallic',u.MaterialProperty.MP_METALLIC,'B')]:
        node=ME.create_material_expression(mat,u.MaterialExpressionTextureSample);node.texture=textures[role]
        node.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if role=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_MASKS if role=='MetallicRoughness' else u.MaterialSamplerType.SAMPLERTYPE_COLOR
        ME.connect_material_property(node,ch,prop);ME.connect_material_expressions(node,ch,slab,pin)
    ME.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(mat);save(mat)
    iron=create('M_HeQue_ChainIron',VERSION+'/Materials',u.Material,u.MaterialFactoryNew())
    ME.delete_all_material_expressions(iron);iron.set_editor_property('used_with_skeletal_mesh',True)
    metal_slab=ME.create_material_expression(iron,u.MaterialExpressionSubstrateShadingModels)
    color=ME.create_material_expression(iron,u.MaterialExpressionConstant3Vector);color.constant=u.LinearColor(.09,.065,.04,1.)
    ME.connect_material_expressions(color,'',metal_slab,'BaseColor');ME.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    for pin,prop,value in [('Metallic',u.MaterialProperty.MP_METALLIC,.8),('Roughness',u.MaterialProperty.MP_ROUGHNESS,.72)]:
        node=ME.create_material_expression(iron,u.MaterialExpressionConstant);node.r=value
        ME.connect_material_expressions(node,'',metal_slab,pin);ME.connect_material_property(node,'',prop)
    ME.connect_material_property(metal_slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);ME.recompile_material(iron);save(iron)
    slots=list(mesh.materials)
    for slot in slots:
        name=str(slot.get_editor_property('imported_material_slot_name'))
        slot.material_interface=iron if 'Chain' in name or 'Iron' in name else mat
    mesh.set_editor_property('materials',slots)
    hit=u.HeQueMonster.build_hit_surface_physics(mesh,VERSION+'/PA_HeQue_HitSurface')
    if not hit:raise RuntimeError('HeQue anatomical hit-surface creation failed')
    save(hit);mesh.set_editor_property('physics_asset',hit);save(mesh)
    clips={};report['root_units']={};author=json.loads((ROOT/'Records/authoring.json').read_text('utf8'))
    for item in author['clips']:
        options=fbx(True,mesh.skeleton);options.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        clip=import_file(ROOT/'Export'/(item['name']+'.fbx'),item['name'],VERSION+'/Animations',options,u.FbxFactory())
        clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',item['loop']);clip.set_preview_skeletal_mesh(mesh)
        report['root_units'][item['role']]=align_root_units(clip,mesh)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compilation did not finish: '+item['name'])
        save(clip);clips[item['role']]=clip
    save(mesh.skeleton)
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.HeQueMonster)
    bp=create('BP_HeQue',DEST,u.Blueprint,factory);u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('visual_mesh',mesh);cdo.set_editor_property('hit_surface_physics',hit)
    for prop,role in [('idle_clip','Idle'),('move_clip','Move'),('turn_left_clip','TurnLeft'),('turn_right_clip','TurnRight'),('stun_clip','Stun'),('air_clip','Air'),('land_clip','Land'),('get_up_clip','GetUp'),('death_clip','Death')]:cdo.set_editor_property(prop,clips[role])
    cdo.set_editor_property('hit_clips',[clips[r] for r in ('HitFront','HitRight','HitBack','HitLeft')])
    for prop,value in [('stride_distance',author['stride_cm']),('walk_speed',110.),('return_speed',90.),('turn_speed',65.),('turn_stride_degrees',48.),('max_health',6000.),('level',12),('rank',u.MonsterRank.BOSS),('experience_reward',0),('corpse_seconds',25.)]:cdo.set_editor_property(prop,value)
    cdo.set_editor_property('ai_controller_class',u.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C'))
    cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    cdo.get_editor_property('mesh').set_anim_instance_class(u.HeQueAnimInstance)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    # Preparation of this character's independent continuous corpse is part
    # of production, not a game simulation or an automated acceptance test.
    folder=ROOT/'SoftCorpse/HeQue';folder.mkdir(parents=True,exist_ok=True)
    corpse=u.load_asset(DEST+'/SoftCorpseV01/SK_HeQue_SoftCorpse') or LIB.duplicate_asset(mesh.get_path_name(),DEST+'/SoftCorpseV01/SK_HeQue_SoftCorpse')
    if not u.M14SoftBodyData.export_surface(corpse,str(folder/'surface.bin'),[]):raise RuntimeError('HeQue corpse surface export failed')
    save(corpse)
    item=dict(key='HeQue',source=mesh.get_path_name(),corpse=corpse.get_path_name(),skeleton=mesh.skeleton.get_path_name())
    (ROOT/'SoftCorpse/sources.json').write_text(json.dumps([item],indent=2),encoding='utf8')
    report.update(stage='living_assets_saved_corpse_prepared',mesh=mesh.get_path_name(),blueprint=bp.get_path_name(),hit_asset=hit.get_path_name(),
        clips={r:dict(path=c.get_path_name(),duration=c.get_play_length()) for r,c in clips.items()},navigation=dict(radius_cm=225,height_cm=450,existing_agent='M10Mawcrawler'),display_height_cm=450)
    record();print('HEQUE_LIVING_ASSETS_SAVED '+bp.get_path_name(),flush=True)
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
