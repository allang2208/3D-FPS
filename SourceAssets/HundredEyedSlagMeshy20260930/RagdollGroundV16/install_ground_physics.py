"""Save an owned physics copy with a scaled-container body; no playback or mesh overwrite."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
project = Path(u.Paths.project_dir()).resolve()
if project not in (ROOT.resolve(), Path('D:/FPS3D/FPSGAME-mp').resolve()):
    raise RuntimeError('Wrong project; assets preserved')
SOURCE = '/Game/Monsters/HundredEyedSlag/PolishV2/PA_HundredEyedSlag_V2'
DEST = '/Game/Monsters/HundredEyedSlag/RagdollGroundV16/PA_HundredEyedSlag_Ground_V16'
source = u.load_asset(SOURCE)
physics = u.load_asset(DEST) if u.EditorAssetLibrary.does_asset_exist(DEST) else u.EditorAssetLibrary.duplicate_asset(SOURCE, DEST)
if not physics:
    raise RuntimeError('Physics copy could not be created')
api = u.get_default_object(u.PhysicsAssetToolset)
names = [str(n) for n in api.call_method('GetBodyNames', (physics,))]
if 'Armature' not in names:
    api.call_method('AddBody', (physics, 'Armature'))
api.call_method('SetSphere', (physics, 'Armature', 'ContainerRoot', u.Vector(), .02))
api.call_method('SetBodyPhysicsMode', (physics, 'Armature', u.BodyPhysicsMode.DEFAULT))

# These subobjects are reflected, although the body's array is private to Python.
root = u.load_object(None, physics.get_path_name() + ':SkeletalBodySetup_16')
pelvis = u.load_object(None, physics.get_path_name() + ':SkeletalBodySetup_0')
if not root or str(root.get_editor_property('bone_name')) != 'Armature':
    raise RuntimeError('Container body was not authored at the expected index')
instance = pelvis.get_editor_property('default_instance')
instance.set_editor_property('mass_in_kg_override', 2.)
instance.set_editor_property('collision_profile_name', 'Custom')
instance.set_editor_property('collision_enabled', u.CollisionEnabled.NO_COLLISION)
root.set_editor_property('default_instance', instance)
root.set_editor_property('collision_trace_flag', u.CollisionTraceFlag.CTF_USE_SIMPLE_AS_COMPLEX)

constraints = api.call_method('GetConstraints', (physics,))
if not any(str(c.get_editor_property('bone1_name')) == 'pelvis' and
           str(c.get_editor_property('bone2_name')) == 'Armature' for c in constraints):
    api.call_method('AddConstraint', (physics, 'pelvis', 'Armature'))
info = u.PhysicsConstraintInfo()
info.set_editor_property('bone1_name', 'pelvis')
info.set_editor_property('bone2_name', 'Armature')
for prop in ('swing1_motion', 'swing2_motion', 'twist_motion'):
    info.set_editor_property(prop, u.ConstraintMotion.LOCKED)
for prop in ('swing1_limit_degrees', 'swing2_limit_degrees', 'twist_limit_degrees'):
    info.set_editor_property(prop, 0.)
api.call_method('SetConstraintLimits', (physics, info))

# This UE build does not expose the constraint instance to Python. Its root
# frames are assigned in rigid-body centimetres to the sampled death pose by
# EnterCorpse, before the first simulated frame. Never use a standing offset.
if not u.EditorAssetLibrary.save_loaded_asset(physics, only_if_is_dirty=False):
    raise RuntimeError('Physics package did not save')
row = {'revision': 'RagdollGroundV16', 'project': str(project), 'physics_asset': physics.get_path_name(),
       'source_physics_asset': source.get_path_name(), 'saved_assets': [physics.get_path_name()],
       'anatomical_bodies_preserved': 16, 'helper_bodies': 1, 'constraint_count': 16,
       'container_bone': 'Armature', 'container_local_radius': .02, 'container_world_radius_cm': 2.,
       'container_constraint_frames': 'Assigned to current death pose by native EnterCorpse before simulation',
       'mesh_asset_modified': False, 'animation_assets_modified': False,
       'runtime_tested': False, 'pie_started': False, 'editor_started': False}
(OUT / 'physics_installation.json').write_text(json.dumps(row, indent=2), encoding='utf-8')
print('SLAG_V16_PHYSICS_SAVED ' + physics.get_path_name(), flush=True)
