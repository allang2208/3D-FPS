"""Author a closer supported sword idle on the currently installed native tracks.

Run in the existing UE asset batch or Python commandlet. No play, render or tests.
Only Idle/Walk and matching action boundary poses receive the posture offset.
"""
import hashlib
import json
import math
import shutil
from pathlib import Path
import unreal as u

P = Path(__file__).parent
ROOT = Path(u.Paths.project_dir()).resolve()
REVISION = 'SwordIdleClose20260926V1'
# Native sword component faces UE -Y (the component itself is yawed +90).
# Centimetres: toward the player, with a small relaxed drop.
OFFSET = (0.0, 6.0, -1.2)
FOLDERS = {
    'Standard': '/Game/Weapons/AzureRunesword20260913',
    'LongGrip': '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations',
}
CLIPS = ['Idle', 'Walk', 'Inspect', 'Equip', 'Slash1', 'Slash2', 'Thrust',
         'PommelStrike', 'Overhead', 'HeavyCharge', 'HeavyRelease',
         'Guard', 'GuardHit', 'GuardBreak', 'WhirlwindV5',
         'TacticalSprint20260921/SprintEnter', 'TacticalSprint20260921/SprintLoop',
         'TacticalSprint20260921/SprintExit', 'TacticalSprint20260921/SprintOverhead']
E = u.EditorAssetLibrary


def add(a, b): return tuple(x+y for x, y in zip(a, b))
def sub(a, b): return tuple(x-y for x, y in zip(a, b))
def mul(a, k): return tuple(x*k for x in a)
def hadamard(a, b): return tuple(x*y for x, y in zip(a, b))
def divide(a, b): return tuple(x/y for x, y in zip(a, b))
def dot(a, b): return sum(x*y for x, y in zip(a, b))
def length(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1/max(1e-12, length(a)))
def cross(a, b): return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
def inverse(q): return (-q[0], -q[1], -q[2], q[3])


def qmul(a, b):
    return (*add(add(mul(b[:3], a[3]), mul(a[:3], b[3])), cross(a[:3], b[:3])),
            a[3]*b[3]-dot(a[:3], b[:3]))


def rotate(q, p):
    t = mul(cross(q[:3], p), 2)
    return add(add(p, mul(t, q[3])), cross(q[:3], t))


def between(a, b):
    a, b = unit(a), unit(b)
    d = max(-1, min(1, dot(a, b)))
    if d > .999999999: return (0, 0, 0, 1)
    if d < -.9999999:
        axis = cross(a, (1, 0, 0))
        if length(axis) < .001: axis = cross(a, (0, 1, 0))
        return (*unit(axis), 0)
    return unit((*cross(a, b), 1+d))


def smooth(x):
    x = max(0, min(1, x))
    return x*x*x*(10-15*x+6*x*x)


def unpack(t):
    p, q, s = t.translation, t.rotation, t.scale3d
    return {'p': (p.x, p.y, p.z), 'q': (q.x, q.y, q.z, q.w), 's': (s.x, s.y, s.z)}


IDENTITY = {'p': (0, 0, 0), 'q': (0, 0, 0, 1), 's': (1, 1, 1)}


def relative(child, parent):
    return {'p': divide(rotate(inverse(parent['q']), sub(child['p'], parent['p'])), parent['s']),
            'q': unit(qmul(inverse(parent['q']), child['q'])),
            's': divide(child['s'], parent['s'])}


def compose(parent, child):
    return {'p': add(parent['p'], rotate(parent['q'], hadamard(parent['s'], child['p']))),
            'q': unit(qmul(parent['q'], child['q'])), 's': hadamard(parent['s'], child['s'])}


def proximity(world, idle):
    names = ('WPN_root', 'hand_r', 'hand_l')
    dist = max(length(sub(world[n]['p'], idle[n]['p'])) for n in names)
    angle = max(math.degrees(2*math.acos(min(1, abs(dot(world[n]['q'], idle[n]['q']))))) for n in names)
    return 1-smooth(max((dist-.5)/7.5, (angle-3)/29))


def reachable(world, offset):
    for side in ('r', 'l'):
        a, e, h = (world[n+'_'+side]['p'] for n in ('upperarm', 'lowerarm', 'hand'))
        upper, lower = length(sub(e, a)), length(sub(h, e))
        reach = length(sub(add(h, offset), a))
        if not abs(upper-lower)+.001 < reach < upper+lower-.001: return False
    return True


def solve_pose(world, offset, weight, parents, edited):
    desired = {n: dict(t) for n, t in world.items()}
    # One shared shift for both grips and weapon if an unusual source nears reach limits.
    if not reachable(world, offset):
        lo, hi = 0., 1.
        for _ in range(24):
            mid = (lo+hi)*.5
            if reachable(world, mul(offset, mid)): lo = mid
            else: hi = mid
        offset = mul(offset, lo)
    desired['WPN_root']['p'] = add(world['WPN_root']['p'], offset)
    for side in ('r', 'l'):
        U, L, H = (n+'_'+side for n in ('upperarm', 'lowerarm', 'hand'))
        a, e, h = (world[n]['p'] for n in (U, L, H))
        upper, lower = length(sub(e, a)), length(sub(h, e))
        goal = add(h, offset)
        axis = unit(sub(goal, a)); reach = length(sub(goal, a))
        # Let elbows settle slightly down/in while the shoulders stay anchored.
        settle = ((-.7 if side == 'r' else .7)*weight, 0, -.8*weight)
        hint = add(add(e, mul(offset, .4)), settle)
        pole = sub(sub(hint, a), mul(axis, dot(sub(hint, a), axis)))
        if length(pole) < .0001:
            pole = sub(sub(e, a), mul(axis, dot(sub(e, a), axis)))
        along = (upper*upper-lower*lower+reach*reach)/(2*reach)
        height = math.sqrt(max(0, upper*upper-along*along))
        elbow = add(add(a, mul(axis, along)), mul(unit(pole), height))
        desired[U]['q'] = unit(qmul(between(sub(e, a), sub(elbow, a)), world[U]['q']))
        desired[L]['p'] = elbow
        desired[L]['q'] = unit(qmul(between(sub(h, e), sub(goal, elbow)), world[L]['q']))
        desired[H]['p'] = goal
        # The hand's orientation and all finger locals remain the installed grip.
    # Carry twist support in its existing parent frame, including helper chains.
    for n in edited:
        if 'twist' in n:
            parent = parents[n]
            desired[n] = compose(desired[parent], relative(world[n], world[parent]))
    return desired, offset


def asset_path(folder, clip):
    if '/' in clip:
        subfolder, clip = clip.rsplit('/', 1)
        folder += '/'+subfolder
    return folder+'/A_RuneSword_'+clip


targets = [(variant, clip, asset_path(folder, clip)) for variant, folder in FOLDERS.items() for clip in CLIPS]
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = [path for _, _, path in targets if path in dirty]
if conflicts: raise RuntimeError('Unsaved animation edits retained: '+str(conflicts))

mesh = u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
component = u.SkeletalMeshComponent()
component.set_skeletal_mesh_asset(mesh)
names = [str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
parents = {n: str(component.get_parent_bone(n)) for n in names}
edited = [n for n in names if n == 'WPN_root' or any(
    n == stem+'_'+side for side in ('r', 'l') for stem in (
        'upperarm', 'lowerarm', 'hand', 'upperarm_twist_01', 'upperarm_twist_02',
        'lowerarm_twist_01', 'lowerarm_twist_02'))]
needed = list(dict.fromkeys(edited+[parents[n] for n in edited if parents[n] != 'None']))
options = u.AnimPoseEvaluationOptions()
options.evaluation_type = u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh = mesh
receipt_file = P/'receipt.json'
receipt = json.loads(receipt_file.read_text()) if receipt_file.exists() else {
    'revision': REVISION, 'offset_native_cm': OFFSET, 'saved': [], 'unchanged': [], 'runtime_tested': False}


def sample(asset, t):
    pose = u.AnimPoseExtensions.get_anim_pose_at_time(asset, t, options)
    world = {n: unpack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.WORLD)) for n in needed}
    local = {n: unpack(u.AnimPoseExtensions.get_bone_pose(pose, n, u.AnimPoseSpaces.LOCAL)) for n in edited}
    return world, local


for variant, folder in FOLDERS.items():
    out = P/variant
    out.mkdir(parents=True, exist_ok=True)
    idle_source_file = out/'idle_source_pose.json'
    # Retain the pre-change idle for idempotent continuation of a partial batch.
    if idle_source_file.exists():
        idle = json.loads(idle_source_file.read_text())
    else:
        idle, _ = sample(u.load_asset(asset_path(folder, 'Idle')), 0)
        idle_source_file.write_text(json.dumps(idle, indent=2), encoding='utf-8')
    for clip in CLIPS:
        path = asset_path(folder, clip)
        asset = u.load_asset(path)
        if not asset:
            if clip in ('Idle', 'Walk', 'Inspect'): raise RuntimeError('Missing required animation '+path)
            continue
        if E.get_metadata_tag(asset, 'SwordIdle.Revision') == REVISION: continue
        disk = ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        original_hash = hashlib.sha256(disk.read_bytes()).hexdigest()
        # AnimationLibrary reports the compressed sampling count, which can be
        # 240 Hz while tactical sprint's editable model is 120 Hz. Controllers
        # index keys at the model rate; mixing them truncates the motion.
        frames = asset.get_editor_property('data_model_interface').get_number_of_frames()
        seconds = asset.get_play_length()
        core = clip in ('Idle', 'Walk')
        start_world, _ = sample(asset, 0)
        end_world, _ = sample(asset, seconds)
        start_gate, end_gate = proximity(start_world, idle), proximity(end_world, idle)
        if not core and max(start_gate, end_gate) <= 1e-5:
            receipt['unchanged'].append(path)
            continue
        rows, source_rows, previous = [], [], {}
        active = 0
        for frame in range(frames+1):
            t = frame*seconds/frames
            world, local = sample(asset, t)
            source_rows.append({'seconds': t, 'bones': local})
            # The work portion of Inspect, attacks and sprint remains untouched.
            boundary = max(start_gate*(1-smooth(t/.20)), end_gate*smooth((t-(seconds-.28))/.28))
            weight = 1. if core else boundary*proximity(world, idle)
            keys = {n: dict(x) for n, x in local.items()}
            actual_offset = (0, 0, 0)
            if weight > 1e-6:
                desired, actual_offset = solve_pose(world, mul(OFFSET, weight), weight, parents, edited)
                active += 1
                for n in edited:
                    local_new = relative(desired[n], desired.get(parents[n], IDENTITY))
                    local_new['s'] = local[n]['s']
                    keys[n] = local_new
            for n, key in keys.items():
                if n in previous and dot(key['q'], previous[n]) < 0:
                    key['q'] = mul(key['q'], -1)
                previous[n] = key['q']
            rows.append({'seconds': t, 'posture_weight': weight, 'offset_cm': actual_offset, 'bones': keys})
        if not active:
            receipt['unchanged'].append(path)
            continue
        stem = clip.replace('/', '_')
        source_file = out/(stem+'_before.json')
        patch_file = out/(stem+'_keys.json')
        source_file.write_text(json.dumps({'asset': path, 'sha256': original_hash, 'frames': frames,
            'seconds': seconds, 'parents': parents, 'samples': source_rows}, separators=(',', ':')), encoding='utf-8')
        patch_file.write_text(json.dumps({'asset': path, 'revision': REVISION, 'frames': frames,
            'seconds': seconds, 'edited_bones': edited, 'samples': rows}, separators=(',', ':')), encoding='utf-8')
        if hashlib.sha256(disk.read_bytes()).hexdigest() != original_hash:
            raise RuntimeError('Animation package changed during authoring; retained: '+path)
        backup = P/'Before'/variant/(stem+'.uasset')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists(): shutil.copy2(disk, backup)
        controller = asset.get_editor_property('controller')
        if controller is None:
            controller = u.AnimDataController()
            controller.set_model(asset.get_editor_property('data_model_interface'))
        controller.open_bracket('Closer sword idle with supported elbows and preserved grips', False)
        try:
            for n in edited:
                keys = [row['bones'][n] for row in rows]
                if not controller.set_bone_track_keys(n, [u.Vector(*k['p']) for k in keys],
                        [u.Quat(*k['q']) for k in keys], [u.Vector(*k['s']) for k in keys], False):
                    raise RuntimeError('Could not author '+n+' in '+path)
        finally:
            controller.close_bracket(False)
        E.set_metadata_tag(asset, 'SwordIdle.Revision', REVISION)
        E.set_metadata_tag(asset, 'SwordIdle.AuthorSource', str(patch_file))
        export = out/(stem+'.fbx')
        task = u.AssetExportTask()
        task.object = asset
        task.filename = str(export)
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.options = u.FbxExportOption()
        task.options.ascii = False
        if not u.Exporter.run_asset_export_task(task): raise RuntimeError('FBX export failed '+path)
        import_data = asset.get_editor_property('asset_import_data')
        if import_data and hasattr(import_data, 'update_filename_only'):
            import_data.update_filename_only(str(export))
        if not E.save_loaded_asset(asset, False): raise RuntimeError('Save failed '+path)
        receipt['saved'].append({'asset': path, 'variant': variant, 'clip': clip, 'seconds': seconds,
            'posture_frames': active, 'total_frames': frames+1, 'backup': str(backup),
            'editable_keys': str(patch_file), 'fbx': str(export)})
        receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
        print('SWORD_IDLE_CLOSE_SAVED', variant, clip, active, '/', frames+1, flush=True)
receipt_file.write_text(json.dumps(receipt, indent=2), encoding='utf-8')
print('SWORD_IDLE_CLOSE_COMPLETE', len(receipt['saved']), flush=True)
