"""Import only three locomotion sequences and update the owned monster Blueprint."""
from pathlib import Path
import json
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BoundCongregateMeshy20261006'
OUT = ROOT/'LocomotionV2'
DEST = '/Game/Monsters/BoundCongregate'
E, AT = u.EditorAssetLibrary, u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != PROJECT/'FPSGAME.uproject':
    raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; preserve the running game and defer this asset import')
manifest = json.loads((OUT/'motion_manifest.json').read_text())
targets = {DEST+'/Animations/'+v['name'] for v in manifest['clips'].values()} | {DEST+'/BP_BoundCongregate'}
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty & targets:
    raise RuntimeError('Unsaved target assets retained: '+str(sorted(dirty & targets)))
mesh = u.load_asset(DEST+'/SK_BoundCongregate')
bp = u.load_asset(DEST+'/BP_BoundCongregate')
controller = E.load_blueprint_class('/Game/Monsters/AI/BP_MonsterAIController')
if not mesh or not bp or not controller:
    raise RuntimeError('Required existing mesh, Blueprint or shared controller missing')
behavior = u.get_default_object(controller).get_editor_property('behavior')
if not behavior:
    raise RuntimeError('Shared controller has no Behavior Tree')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
saved, clips = [], {}
def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: '+str(asset))
    saved.append(asset.get_path_name())
for role, data in manifest['clips'].items():
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_as_skeletal = True
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = options.import_textures = options.create_physics_asset = False
    options.skeleton = mesh.skeleton
    animation = options.anim_sequence_import_data
    animation.convert_scene = animation.convert_scene_unit = True
    animation.force_front_x_axis = False
    animation.import_uniform_scale = 1
    animation.set_editor_property('use_default_sample_rate', False)
    animation.set_editor_property('custom_sample_rate', manifest['fps'])
    animation.set_editor_property('animation_length', u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task = u.AssetImportTask()
    task.filename = data['file']
    task.destination_path, task.destination_name = DEST+'/Animations', data['name']
    task.factory, task.options = u.FbxFactory(), options
    task.automated = task.replace_existing = task.replace_existing_settings = True
    task.save = False
    AT.import_asset_tasks([task])
    clip = u.load_asset(task.destination_path+'/'+task.destination_name)
    if not clip: raise RuntimeError('Animation import failed: '+data['name'])
    clip.set_editor_property('loop', True)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_preview_skeletal_mesh(mesh)
    save(clip)
    clips[role] = clip
save(mesh.skeleton)
cdo = u.get_default_object(bp.generated_class())
for prop, role in [('move_clip','Walk'), ('turn_left_clip','TurnLeft'), ('turn_right_clip','TurnRight')]:
    cdo.set_editor_property(prop, clips[role])
cdo.set_editor_property('animation_walk_speed', manifest['walk_speed_cm'])
cdo.set_editor_property('ai_controller_class', controller)
cdo.set_editor_property('auto_possess_ai', u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
u.BlueprintEditorLibrary.compile_blueprint(bp)
save(bp)
result = dict(complete=True, revision=manifest['revision'], saved=saved,
              walk_speed_cm=manifest['walk_speed_cm'], game_walk_speed_cm=cdo.get_editor_property('walk_speed'),
              controller=controller.get_path_name(), behavior=behavior.get_path_name(),
              gameplay_tested=False, rendered=False)
(OUT/'ue_delivery.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('BOUND_CONGREGATE_LOCOMOTION_V2_SAVED '+json.dumps(result))
