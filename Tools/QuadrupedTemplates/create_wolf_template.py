"""Create missing Wolf V1 template assets. No maps, gameplay or animation previews."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path(__file__).resolve().parents[2]
OUT = PROJECT / 'SourceAssets/QuadrupedTemplates'
DEST = '/Game/Monsters/QuadrupedTemplates/WolfV1'
SOURCE = '/Game/AnimalVarietyPack/Wolf'
lib = u.EditorAssetLibrary
tools = u.AssetToolsHelpers.get_asset_tools()
catalog = json.loads((OUT / 'source_catalog.json').read_text(encoding='utf-8'))
source_rows = {row['name']: row for row in catalog['animations']}
mesh = u.load_asset(SOURCE + '/Meshes/SK_Wolf')

# ID, source suffix, loop, hold, terminal, next. No keyframe editing or contact guesses.
SLOTS = [
    ('Idle', 'IdleBreathe', True, False, False, ''),
    ('IdleAlert', 'IdleAggressive', True, False, False, ''),
    ('LookAround', 'IdleLookAround', False, False, False, ''),
    ('Walk', 'Walk', True, False, False, ''),
    ('WalkTurnLeft', 'WalkTurnL', True, False, False, ''),
    ('WalkTurnRight', 'WalkTurnR', True, False, False, ''),
    ('Run', 'Run', True, False, False, ''),
    ('RunTurnLeft', 'RunTurnL', True, False, False, ''),
    ('RunTurnRight', 'RunTurnR', True, False, False, ''),
    ('AttackBite', 'Bite', False, False, False, ''),
    ('AttackRunBite', 'RunBite', False, False, False, ''),
    ('AttackPounce', 'JumpBite', False, False, False, ''),
    ('HitFront', 'GetHitFront', False, False, False, ''),
    ('HitLeft', 'GetHitLeft', False, False, False, ''),
    ('HitRight', 'GetHitRight', False, False, False, ''),
    ('Howl', 'Howl', False, False, False, ''),
    ('RestEnter', 'GoToRest', False, False, False, 'RestLoop'),
    ('RestLoop', 'Rest', True, False, False, ''),
    ('RestExit', 'RestToGoBackUp', False, False, False, ''),
    ('SleepLoop', 'Sleep', True, False, False, ''),
    ('Death', 'Death', False, True, True, ''),
]

# Names are from the installed Skeleton's parent chains, not a humanoid auto-map.
# Wolf_-Ponytail1 is deliberately kept unclassified until its anatomy is viewed.
CHAINS = {
    'MotionRoot': ('root', 'root'),
    'BodyRoot': ('Wolf_', 'Wolf_-Pelvis'),
    'Spine': ('Wolf_-Spine', 'Wolf_-Spine1'),
    'Neck': ('Wolf_-Neck', 'Wolf_-Neck2'),
    'Head': ('Wolf_-Head', 'Wolf_-Head'),
    'HeadAccessory': ('Wolf_-Ponytail1', 'Wolf_-Ponytail1'),
    'Shoulder_L': ('Wolf_-L-Clavicle', 'Wolf_-L-Clavicle'),
    'Shoulder_R': ('Wolf_-R-Clavicle', 'Wolf_-R-Clavicle'),
    'ForeLeg_L': ('Wolf_-L-UpperArm', 'Wolf_-L-Hand'),
    'ForeLeg_R': ('Wolf_-R-UpperArm', 'Wolf_-R-Hand'),
    'ForeToe_L': ('Wolf_-L-Finger0', 'Wolf_-L-Finger0'),
    'ForeToe_R': ('Wolf_-R-Finger0', 'Wolf_-R-Finger0'),
    'HindLeg_L': ('Wolf_-L-Thigh', 'Wolf_-L-Foot'),
    'HindLeg_R': ('Wolf_-R-Thigh', 'Wolf_-R-Foot'),
    'Tail': ('Wolf_-Tail', 'Wolf_-Tail5'),
}

def save(asset):
    if not lib.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())

def create_missing(name, folder, cls, factory):
    existing = u.load_asset(folder + '/' + name) if lib.does_asset_exist(folder + '/' + name) else None
    if existing:
        return existing, False
    asset = tools.create_asset(name, folder, cls, factory)
    if asset is None:
        raise RuntimeError('Could not create ' + folder + '/' + name)
    return asset, True

report = {
    'version': 1,
    'source_listing': catalog['source'],
    'stage': 'UE animation template authoring; not gameplay integration',
    'runtime_tested': False, 'rendered_or_visually_accepted': False,
    'source_keys_reauthored': False,
    'entry': DEST + '/BP_QP_Wolf_Template',
    'native_anim_instance': '/Script/FPSGAME.QuadrupedTemplateAnimInstance',
    'actions': [], 'ik_chains': CHAINS,
    'unclassified_bone': 'Wolf_-Ponytail1',
    'movement': 'in_place_external_movement',
    'nominal_speeds': {'walk_cm_s': 140, 'run_cm_s': 450, 'basis': 'editable initial design values; not measured source travel'},
    'runtime_damage': 'none; contact fields remain -1 until authored from observed motion',
    'policy': 'create missing assets only; preserve existing template edits',
}
definitions = {}
for role, suffix, loop, hold, terminal, followup in SLOTS:
    source_name = 'ANIM_Wolf_' + suffix
    src = SOURCE + '/Animations/' + source_name
    dst = DEST + '/Animations/A_QP_Wolf_' + role
    created = not lib.does_asset_exist(dst)
    clip = lib.duplicate_asset(src, dst) if created else u.load_asset(dst)
    if clip is None:
        raise RuntimeError('Could not create animation ' + dst)
    if created:
        clip.set_editor_property('enable_root_motion', False)
        clip.set_editor_property('force_root_lock', True)
        clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.ANIM_FIRST_FRAME)
        clip.set_editor_property('rate_scale', 1.0)
        clip.set_preview_skeletal_mesh(mesh)
        lib.set_metadata_tag(clip, 'Quadruped.Source', src)
        lib.set_metadata_tag(clip, 'Quadruped.Action', role)
        save(clip)
    entry = u.QuadrupedTemplateAction()
    for prop, value in {
        'sequence': clip, 'loop': loop, 'hold_last_pose': hold, 'terminal': terminal,
        'next_action': followup, 'blend_seconds': 0.15, 'play_rate': 1.0,
        'contact_start_seconds': -1.0, 'contact_end_seconds': -1.0,
    }.items():
        entry.set_editor_property(prop, value)
    definitions[role] = entry
    row = source_rows[source_name]
    report['actions'].append({
        'id': role, 'source': src, 'template': dst,
        'source_seconds': row['seconds'], 'source_frame_intervals': row['frame_intervals'],
        'loop_default': loop, 'hold_default': hold, 'terminal_default': terminal,
        'next_default': followup or None, 'contact_seconds': None,
        'source_rm_alternative': (SOURCE + '/Animations/' + source_name + '_RM') if source_name + '_RM' in source_rows else None,
        'created_this_run': created,
    })

factory = u.DataAssetFactory()
factory.set_editor_property('data_asset_class', u.QuadrupedAnimationSet)
dataset, created = create_missing('DA_QP_Wolf_AnimationSet', DEST, u.QuadrupedAnimationSet, factory)
if created:
    dataset.set_editor_property('reference_mesh', mesh)
    dataset.set_editor_property('actions', definitions)
    dataset.set_editor_property('walk_speed', 140.0)
    dataset.set_editor_property('run_speed', 450.0)
    save(dataset)
report['animation_set'] = dataset.get_path_name()
report['animation_set_created_this_run'] = created

rig, created = create_missing('IK_QP_Wolf_Source', DEST + '/Rig', u.IKRigDefinition, u.IKRigDefinitionFactory())
if created:
    controller = u.IKRigController.get_controller(rig)
    controller.set_skeletal_mesh(mesh)
    controller.set_retarget_root('Wolf_-Pelvis')
    for name, (start, end) in CHAINS.items():
        controller.add_retarget_chain(name, start, end, '')
    save(rig)
report['source_ik_rig'] = rig.get_path_name()
report['rig_created_this_run'] = created

factory = u.BlueprintFactory()
factory.set_editor_property('parent_class', u.QuadrupedAnimationTemplate)
blueprint, created = create_missing('BP_QP_Wolf_Template', DEST, u.Blueprint, factory)
if created:
    # Compilation is asset construction, not an animation/gameplay acceptance run.
    u.BlueprintEditorLibrary.compile_blueprint(blueprint)
    defaults = u.get_default_object(blueprint.generated_class())
    defaults.set_editor_property('animation_set', dataset)
    defaults.set_editor_property('use_owner_velocity', False)
    defaults.set_editor_property('manual_speed', 0.0)
    defaults.get_editor_property('mesh').set_skeletal_mesh_asset(mesh)
    save(blueprint)
report['blueprint_created_this_run'] = created
(OUT / 'template_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('QUADRUPED_WOLF_TEMPLATE_CREATED ' + DEST)
