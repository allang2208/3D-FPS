"""Bake a grounded weight-shift bite from the existing wolf clip, then bind it.

Run with UE Python. This authors assets and an editable FBX; it does not run,
render or test the game. Source clips and their gameplay timing stay intact.
"""
import json
import math
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'SourceAssets/WolfMonster/BiteV2'
OUT.mkdir(parents=True, exist_ok=True)
SOURCE = '/Game/Monsters/QuadrupedTemplates/WolfV1/Animations/A_QP_Wolf_AttackBite'
TARGET = '/Game/Monsters/QuadrupedTemplates/WolfV2/Animations/A_QP_Wolf_Bite_WeightShift'
SETS = ['/Game/Monsters/QuadrupedTemplates/WolfV1/DA_QP_Wolf_AnimationSet',
        '/Game/Monsters/Wolf/DA_Wolf_AnimationSet']
LIB = u.EditorAssetLibrary
PARAMETERS = json.loads((OUT / 'motion_parameters.json').read_text(encoding='utf-8'))

def add(a, b): return tuple(x + y for x, y in zip(a, b))
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def mul(a, s): return tuple(x * s for x in a)
def component_mul(a, b): return tuple(x * y for x, y in zip(a, b))
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def length(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1.0 / max(1e-12, length(a)))
def inverse(q): return (-q[0], -q[1], -q[2], q[3])

def qmul(a, b):
    v = add(add(mul(b[:3], a[3]), mul(a[:3], b[3])), cross(a[:3], b[:3]))
    return (*v, a[3]*b[3]-dot(a[:3], b[:3]))

def rotate(q, p):
    t = mul(cross(q[:3], p), 2.0)
    return add(add(p, mul(t, q[3])), cross(q[:3], t))

def axis_angle(axis, radians):
    return (*mul(unit(axis), math.sin(radians*.5)), math.cos(radians*.5))

def between(a, b):
    a, b = unit(a), unit(b)
    d = max(-1.0, min(1.0, dot(a, b)))
    if d > .9999999:
        return (0., 0., 0., 1.)
    if d < -.9999999:
        axis = cross(a, (1., 0., 0.))
        if length(axis) < .0001: axis = cross(a, (0., 1., 0.))
        return axis_angle(axis, math.pi)
    return unit((*cross(a, b), 1.0 + d))

def envelope(name, time):
    keys = PARAMETERS[name]
    if time <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if time <= t1:
            f = max(0., min(1., (time-t0)/(t1-t0)))
            f = f*f*(3.-2.*f)
            return v0 + (v1-v0)*f
    return keys[-1][1]

def unpack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return {'p': (p.x, p.y, p.z), 'q': (q.x, q.y, q.z, q.w), 's': (s.x, s.y, s.z)}

source = u.load_asset(SOURCE)
mesh = u.load_asset('/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents = {name: str(component.get_parent_bone(name)) for name in names}
options = u.AnimPoseEvaluationOptions()
options.set_editor_property('evaluation_type', u.AnimDataEvalType.SOURCE)
options.set_editor_property('optional_skeletal_mesh', mesh)
frames = u.AnimationLibrary.get_num_frames(source)
duration = source.get_play_length()

def fk(local):
    result = {}
    for name in names:
        t, parent = local[name], parents[name]
        if parent not in result:
            result[name] = dict(t)
        else:
            base = result[parent]
            result[name] = {'p': add(base['p'], rotate(base['q'], component_mul(base['s'], t['p']))),
                            'q': unit(qmul(base['q'], t['q'])), 's': component_mul(base['s'], t['s'])}
    return result

def set_world_rotation(local, name, rotation):
    world = fk(local)
    parent = parents[name]
    local[name]['q'] = unit(qmul(inverse(world[parent]['q']), rotation)) if parent in world else unit(rotation)

def turn_bone(local, name, axis, radians):
    current = fk(local)[name]['q']
    set_world_rotation(local, name, qmul(axis_angle(axis, radians), current))

def solve_leg(local, chain, goal, paw_rotation):
    """Fit rotations to fixed-length segments, retaining the source bend side.

    Forelegs use a two-link solution; hindlegs keep the extra hock segment.
    Foot orientation is restored after the chain so toes retain their support.
    """
    world = fk(local)
    points = [world[name]['p'] for name in chain]
    lengths = [length(sub(b, a)) for a, b in zip(points, points[1:])]
    origin = points[0]
    offset = sub(goal, origin)
    reach = min(length(offset), sum(lengths)-.001)
    goal = add(origin, mul(unit(offset), reach))
    if len(chain) == 3:
        reach = max(reach, abs(lengths[0]-lengths[1])+.001)
        forward = unit(offset)
        bend = sub(sub(points[1], origin), mul(forward, dot(sub(points[1], origin), forward)))
        if length(bend) < .001:
            bend = cross(forward, (1., 0., 0.))
        along = (lengths[0]**2-lengths[1]**2+reach**2)/(2.*reach)
        height = math.sqrt(max(0., lengths[0]**2-along**2))
        points[1] = add(add(origin, mul(forward, along)), mul(unit(bend), height))
        points[2] = add(origin, mul(forward, reach))
    else:
        # Small offsets start from the authored anatomical bend, not a straight chain.
        for _ in range(24):
            points[-1] = goal
            for i in range(len(points)-2, -1, -1):
                points[i] = add(points[i+1], mul(unit(sub(points[i], points[i+1])), lengths[i]))
            points[0] = origin
            for i in range(1, len(points)):
                points[i] = add(points[i-1], mul(unit(sub(points[i], points[i-1])), lengths[i-1]))
            if length(sub(points[-1], goal)) < .001:
                break
    for i, name in enumerate(chain[:-1]):
        world = fk(local)
        old = sub(world[chain[i+1]]['p'], world[name]['p'])
        wanted = sub(points[i+1], world[name]['p'])
        set_world_rotation(local, name, qmul(between(old, wanted), world[name]['q']))
    set_world_rotation(local, chain[-1], paw_rotation)

chains = [[f'Wolf_-{side}-{part}' for part in ('UpperArm', 'Forearm', 'Hand')] for side in ('L', 'R')]
chains += [[f'Wolf_-{side}-{part}' for part in ('Thigh', 'Calf', 'HorseLink', 'Foot')] for side in ('L', 'R')]
changed = ['Wolf_', 'Wolf_-Spine', 'Wolf_-Neck', 'Wolf_-Neck1', 'Wolf_-Neck2']
changed += [name for chain in chains for name in chain]
before_rows, after_rows = [], []
for frame in range(frames+1):
    time = frame*duration/frames
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(source, time, options)
    original = {name: unpack(u.AnimPoseExtensions.get_bone_pose(pose, name, u.AnimPoseSpaces.LOCAL)) for name in names}
    local = {name: dict(t) for name, t in original.items()}
    source_world = fk(original)
    if 0 < frame < frames:
        # Container root stays unchanged; the animal shifts weight within its capsule.
        parent = source_world[parents['Wolf_']]
        component_delta = (0., envelope('body_forward_cm', time), envelope('body_height_cm', time))
        parent_delta = rotate(inverse(parent['q']), component_delta)
        local_delta = tuple(value / scale for value, scale in zip(parent_delta, parent['s']))
        local['Wolf_']['p'] = add(local['Wolf_']['p'], local_delta)
        strength = envelope('drive', time)
        turn_bone(local, 'Wolf_-Spine', (1., 0., 0.), math.radians(PARAMETERS['shoulder_pitch_degrees'])*strength)
        world = fk(local)
        direction = sub(world['Wolf_-Head']['p'], world['Wolf_-Neck']['p'])
        yaw = math.atan2(direction[0], direction[1])*PARAMETERS['reduce_neck_side_arc']*strength
        yaw = max(-math.radians(18.), min(math.radians(18.), yaw))
        for bone, share in zip(('Wolf_-Neck', 'Wolf_-Neck1', 'Wolf_-Neck2'), (.5, .3, .2)):
            turn_bone(local, bone, (0., 0., 1.), yaw*share)
        turn_bone(local, 'Wolf_-Neck1', (1., 0., 0.),
                  math.radians(PARAMETERS['neck_counter_pitch_degrees'])*envelope('neck_follow', time))
        for index, chain in enumerate(chains):
            goal = source_world[chain[-1]]['p']
            if index == 0:
                goal = add(goal, (0., envelope('lead_paw_forward_cm', time), envelope('lead_paw_lift_cm', time)))
            solve_leg(local, chain, goal, source_world[chain[-1]]['q'])
    before_rows.append({'seconds': time, 'bones': {name: original[name] for name in changed}})
    after_rows.append({'seconds': time, 'bones': {name: local[name] for name in changed}})

# Keep the editable source samples and parameters even if asset saving is interrupted.
(OUT / 'bake_keys.json').write_text(json.dumps({'source': SOURCE, 'seconds': duration,
    'intervals': frames, 'parents': parents, 'changed_bones': changed,
    'before_local': before_rows, 'after_local': after_rows}, indent=2), encoding='utf-8')

clip = u.load_asset(TARGET) if LIB.does_asset_exist(TARGET) else LIB.duplicate_asset(SOURCE, TARGET)
if clip is None:
    raise RuntimeError('Could not create ' + TARGET)
authored = LIB.get_metadata_tag(clip, 'Wolf.BiteMotionVersion') != '2'
if authored:
    model = clip.get_editor_property('data_model_interface')
    controller = clip.get_editor_property('controller')
    if controller is None:
        controller = u.AnimDataController()
        controller.set_model(model)
    controller.open_bracket('Author wolf bite weight shift and planted supports', False)
    try:
        for name in changed:
            keys = [row['bones'][name] for row in after_rows]
            positions = [u.Vector(*key['p']) for key in keys]
            rotations = [u.Quat(*key['q']) for key in keys]
            scales = [u.Vector(*key['s']) for key in keys]
            if not controller.set_bone_track_keys(name, positions, rotations, scales, False):
                raise RuntimeError('Could not author bone ' + name)
    finally:
        controller.close_bracket(False)
    clip.set_editor_property('enable_root_motion', False)
    clip.set_editor_property('force_root_lock', True)
    clip.set_editor_property('root_motion_root_lock', u.RootMotionRootLock.ANIM_FIRST_FRAME)
    clip.set_editor_property('rate_scale', 1.)
    clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip, 'Wolf.BiteMotionVersion', '2')
    LIB.set_metadata_tag(clip, 'Wolf.BiteSource', SOURCE)
    if not LIB.save_loaded_asset(clip, False):
        raise RuntimeError('Could not save authored clip')

bindings = []
for path in SETS:
    dataset = u.load_asset(path)
    actions = dataset.get_editor_property('actions')
    action = actions['AttackBite']
    previous = action.get_editor_property('sequence').get_path_name()
    if LIB.get_metadata_tag(dataset, 'Wolf.BiteMotionVersion') != '2':
        action.set_editor_property('sequence', clip)
        # Loop, play rate, contact window and blend duration retain their existing values.
        actions['AttackBite'] = action
        dataset.set_editor_property('actions', actions)
        LIB.set_metadata_tag(dataset, 'Wolf.BiteMotionVersion', '2')
        if not LIB.save_loaded_asset(dataset, False):
            raise RuntimeError('Could not save ' + path)
    bindings.append({'set': path, 'previous_sequence': previous,
                     'current_sequence': action.get_editor_property('sequence').get_path_name(),
                     'contact_start': action.get_editor_property('contact_start_seconds'),
                     'contact_end': action.get_editor_property('contact_end_seconds')})

export = u.AssetExportTask()
export.object = clip
export.filename = str(OUT / 'A_QP_Wolf_Bite_WeightShift.fbx')
export.automated = True
export.prompt = False
export.replace_identical = True
export.options = u.FbxExportOption()
export.options.set_editor_property('export_preview_mesh', False)
export.options.set_editor_property('level_of_detail', False)
export.options.set_editor_property('bake_material_inputs', u.FbxMaterialBakeMode.DISABLED)
export.exporter = u.AnimSequenceExporterFBX()
if not u.Exporter.run_asset_export_task(export):
    raise RuntimeError('Could not export editable wolf bite FBX')
(OUT / 'authoring_manifest.json').write_text(json.dumps({
    'version': 2, 'source': SOURCE, 'asset': TARGET, 'authored_this_run': authored,
    'seconds': duration, 'intervals': frames, 'bindings': bindings,
    'export': export.filename, 'export_contains': 'skeleton_and_animation', 'parameters': PARAMETERS,
    'source_reference': 'Godot Quaternius Attack continuous frames viewed in the preceding comparison',
    'runtime_tested': False, 'rendered_or_visually_accepted': False,
    'gameplay_timing_modified': False, 'actor_movement_modified': False,
}, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('WOLF_BITE_V2_AUTHORED ' + TARGET)
