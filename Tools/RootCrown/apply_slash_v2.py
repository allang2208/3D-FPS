"""Repair the diagnosed vertex/pixel error, then bind the 2x downstroke assets."""
import ast,json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';VERSION=DEST+'/SlashV02'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();ME=u.MaterialEditingLibrary
report={'stage':'applying','saved':[],'game_started':False,'material_check_requested':True}
RECEIPT=ROOT/'Reports/slash_v2_delivery.json'
source=ast.parse(Path('D:/FPS3D/FPSGAME/Tools/RootCrown/install.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in ('record','save','import_file','fbx','pose_at','align_root_units')],type_ignores=[]),'RootCrown/import_helpers','exec'))
previous=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX')
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('End the existing PIE before binding new animation assets')
    dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith(DEST)]
    if dirty:raise RuntimeError('Unsaved Root Crown packages: '+str(dirty))
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');cdo=u.get_default_object(bp.generated_class())
    mat=cdo.get_editor_property('slash_material')
    nodes={};pending=[ME.get_material_property_input_node(mat,p) for p in (u.MaterialProperty.MP_FRONT_MATERIAL,u.MaterialProperty.MP_BASE_COLOR)]
    while pending:
        node=pending.pop()
        if not node or node.get_path_name() in nodes:continue
        nodes[node.get_path_name()]=node;pending.extend(c for c in ME.get_inputs_for_material_expression(mat,node) if c)
    mask=next(n for n in nodes.values() if isinstance(n,u.MaterialExpressionCustom) and 'smoothstep(56.0' in n.get_editor_property('code'))
    position=next(n for n in nodes.values() if isinstance(n,u.MaterialExpressionPreSkinnedPosition))
    interpolator=next((n for n in nodes.values() if isinstance(n,u.MaterialExpressionVertexInterpolator)),None)
    if not interpolator:interpolator=ME.create_material_expression(mat,u.MaterialExpressionVertexInterpolator,-650,-450)
    if not ME.connect_material_expressions(position,'',interpolator,'VS'):raise RuntimeError('Vertex-stage input was not connected')
    if not ME.connect_material_expressions(interpolator,'',mask,'P'):raise RuntimeError('Pixel-stage mask input was not connected')
    errors=list(ME.recompile_material(mat));report['compile_errors']=errors
    if errors:raise RuntimeError('Root Crown shader compile errors: '+str(errors))
    # In the existing D3D12 editor this submits and finishes the actual SM6
    # shaders, including the skeletal vertex factory. NullRHI is not evidence.
    stats=ME.get_statistics(mat)
    report['shader_statistics']={name:stats.get_editor_property(name) for name in ('num_vertex_shader_instructions','num_pixel_shader_instructions','num_samplers','num_pixel_texture_samples','num_interpolator_scalars')}
    if report['shader_statistics']['num_pixel_shader_instructions']<=0:raise RuntimeError('No compiled pixel shader statistics; material repair is not yet confirmed')
    textures=[t.get_path_name() for t in ME.get_material_used_textures(mat)];report['textures']=textures
    for role in ('BaseColor','Normal','MetallicRoughness'):
        if not any('T_RootCrown_'+role+'.' in path for path in textures):raise RuntimeError('Missing preserved PBR texture: '+role)
    report['material']=mat.get_path_name();report['vertex_to_pixel_interpolation']=True
    save(mat)
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    mesh=cdo.get_editor_property('visual_mesh');opts=fbx(True,mesh.skeleton)
    opts.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
    name='A_RootCrown_CrownSlash_V02'
    clip=import_file(ROOT/'Exports/SlashV02'/(name+'.fbx'),name,VERSION,opts,u.FbxFactory())
    clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True);clip.set_editor_property('loop',False)
    clip.set_preview_skeletal_mesh(mesh);align_root_units(clip,mesh)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation compression did not finish')
    save(clip);save(mesh.skeleton)
    sound=import_file(ROOT/'Audio/SlashV02/RootCrown_SlashGesture.wav','S_RootCrown_SlashGesture_V02',VERSION+'/Audio');save(sound)
    contact=json.loads((ROOT/'Exports/SlashV02/contact.json').read_text('utf8'));frames=[]
    for row in contact['frames']:
        frame=u.RootCrownEdgeFrame();frame.set_editor_property('time',row['time']);frame.set_editor_property('points',[u.Vector(*v) for v in row['points']]);frames.append(frame)
    cdo.set_editor_property('slash_clip',clip);cdo.set_editor_property('slash_gesture_sound',sound);cdo.set_editor_property('slash_frames',frames)
    cdo.set_editor_property('slash_material',mat);cdo.get_editor_property('mesh').set_material(0,mat)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='material_repaired_and_v2_saved',clip=clip.get_path_name(),blueprint=bp.get_path_name(),downstroke_before=.4,downstroke_after=.2,speed_multiplier=2.,downstroke_window=[1.1,1.3],contact_frame_count=len(frames),last_contact_frame=frames[-1].get_editor_property('time'),total_duration=clip.get_play_length(),damage_unchanged=cdo.get_editor_property('slash_damage'),cooldown_unchanged=cdo.get_editor_property('slash_cooldown'),native_code_changed=False,gameplay_tested=False,audio_auditioned=False)
    record();print('ROOT_CROWN_V2_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(previous))
