"""Super90 tube loader R12: build funnel/props, bake 15 clips and grip deltas.

Blender background. Writes Exports/*.fbx, *_profiles.json, authoring.json and
Super90_Speedloader_R12.blend. Does not export or overwrite the idle.
No game run, render or acceptance test.
"""
import sys, hashlib, shutil
from pathlib import Path
O = Path(__file__).parent
g = {'__file__': str(O / 'r12_core.py')}
for part in ('r12_core.py', 'skin_arm.py', 'r12_motion.py', 'r12_geometry.py'):
    exec(compile((O / part).read_text(encoding='utf-8'), str(O / part), 'exec'), g)
globals().update({k: v for k, v in g.items() if not k.startswith('__')})
sys.path.insert(0, str(S / 'M1911RevolverInspect20260927'))
import author_support as support
X = O / 'Exports'; X.mkdir(exist_ok=True)
REVISION = 'LoaderR12-20261009'

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs: ob.hide_set(False); ob.select_set(True)
    bpy.context.view_layer.objects.active = obs[-1]
def material(name, color, metal, rough):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.diffuse_color = (*color, 1); m.use_nodes = True
    bs = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bs:
        bs.inputs['Base Color'].default_value = (*color, 1); bs.inputs['Metallic'].default_value = metal; bs.inputs['Roughness'].default_value = rough
    return m
anodized = material('S90Loader_Anodized', (.030, .032, .036), 1., .48)
polymer = material('S90Loader_Polymer', (.018, .018, .019), 0., .62)
steel = material('S90Loader_Steel', (.025, .026, .028), 1., .40)
def finish(ob, bevel=.0005):
    if bevel:
        # Soft machined edges on the remaining hard corners only (ears, rails, pin, gusset, slot).
        mod = ob.modifiers.new('Machined edge', 'BEVEL'); mod.width = bevel; mod.segments = 2
        mod.limit_method = 'ANGLE'; mod.angle_limit = math.radians(35); mod.use_clamp_overlap = True
        select([ob]); bpy.ops.object.modifier_apply(modifier=mod.name)
    select([ob]); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(island_margin=.02); bpy.ops.object.mode_set(mode='OBJECT')
    mod = ob.modifiers.new('Export tangent triangles', 'TRIANGULATE'); bpy.ops.object.modifier_apply(modifier=mod.name)
def bind(ob, bone):
    ob.data.transform(rest[bone]); ob.parent = rig; ob.matrix_parent_inverse = I; ob.matrix_basis = I
    vg = ob.vertex_groups.new(name=bone); vg.add(list(range(len(ob.data.vertices))), 1., 'REPLACE')
    mod = ob.modifiers.new('Native rigid mechanism', 'ARMATURE'); mod.object = rig

# Hide the historical loader objects if the source scene carries any.
for ob in list(bpy.data.objects):
    if ob.name.startswith(('SM_Super90_LoaderGuide', 'SpeedloaderTube', 'SpeedloaderPlunger')): bpy.data.objects.remove(ob, do_unlink=True)

funnel, funnel_fit = build_funnel([anodized, steel]); finish(funnel)
select([funnel]); bpy.ops.export_scene.fbx(filepath=str(X / 'SM_Super90_LoaderGuide.fbx'), use_selection=True, object_types={'MESH'},
    axis_forward='-Y', axis_up='Z', bake_anim=False, use_tspace=True, mesh_smooth_type='FACE')
tube, plunger = build_props([anodized, polymer, steel], LAYOUT)
finish(tube); finish(plunger)
bind(tube, 'WPN_Shell'); bind(plunger, PLUNGER_DRIVER)
select([tube, plunger, rig]); rig.animation_data_clear()
for b in rig.pose.bones: b.matrix_basis = I
bpy.ops.export_scene.fbx(filepath=str(X / 'SK_Super90_LoaderProps.fbx'), use_selection=True, object_types={'MESH', 'ARMATURE'},
    axis_forward='-Y', axis_up='Z', add_leaf_bones=False, bake_anim=False, use_tspace=True, mesh_smooth_type='FACE')

def local_rows(world):
    rows = []
    for p in world:
        row = {}
        for n in names:
            local = rest[n].inverted() @ rest[parents[n]] @ p[parents[n]].inverted() @ p[n] if parents[n] else rest[n].inverted() @ p[n]
            row[n] = list(local.decompose())
            if rows and rows[-1][n][1].dot(row[n][1]) < 0: row[n][1].negate()
        rows.append(row)
    return rows

def export_action(name, world, frames):
    support.DURATION = frames[-1] / 60
    rig.animation_data_create(); support.bake_action(rig, scene, name, local_rows(world), frames)
    select([rig]); path = X / (name + '.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE'}, axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0)
    return path

changed = ['clavicle_l', 'upperarm_l', 'lowerarm_l', 'lowerarm_aux_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l'] + finger_names['l']
changed += [n for n in names if n.startswith('upperarm_twist') and n.endswith('_l')]
def delta_tracks(base_rows, adapted_rows, frames):
    tracks = {n: [] for n in changed}
    for base, adapted in zip(base_rows, adapted_rows):
        bue = {n: C @ base[n] @ K[n] for n in changed + [parents[n] for n in changed]}
        aue = {n: C @ adapted[n] @ K[n] for n in changed + [parents[n] for n in changed]}
        for n in changed:
            par = parents[n]; bb = bue[par].inverted() @ bue[n]; aa = aue[par].inverted() @ aue[n]
            q = aa.to_quaternion() @ bb.to_quaternion().inverted()
            if tracks[n] and q.dot(Quaternion((tracks[n][-1][6], *tracks[n][-1][3:6]))) < 0: q.negate()
            elif not tracks[n] and q.w < 0: q.negate()
            dp = aa.translation - bb.translation; ds = aa.to_scale() - bb.to_scale()
            tracks[n].append([*dp, q.x, q.y, q.z, q.w, *ds])
    out = []
    zero = [0, 0, 0, 0, 0, 0, 1, 0, 0, 0]
    for n, values in tracks.items():
        if all(max(abs(a - b) for a, b in zip(v, zero)) < 1e-5 for v in values): continue
        out.append({'bone': n, 'times': [f / 60 for f in frames], 'values': [x for row in values for x in row]})
    return out

ANIM = '/Game/Weapons/Super90/Speedloader20261007/Animations/'
report = {'revision': REVISION, 'reference': 'User Delta Force M1014 speedloader capture (empty), 2026-10-09; phases per Docs/Weapons/super90-speedloader-r12-plan-20261009.md',
          'original_game_prop': True, 'capacity': 7, 'runtime_tested': False, 'source_fps': 60, 'default_play_rate': PLAY_RATE,
          'meshes': {'guide': str(X / 'SM_Super90_LoaderGuide.fbx'), 'props': str(X / 'SK_Super90_LoaderProps.fbx')},
          'prop_drivers': {'tube': 'WPN_Shell', 'pusher': PLUNGER_DRIVER}, 'layout': LAYOUT, 'funnel_fit': funnel_fit,
          'grasp': {'file': str(O / 'knob_grasp.json'), 'fit': GRASP['fit']},
          'clock': {'insert': INSERT, 'step': STEP, 'show_begin': SHOW_BEGIN, 'hide_tail': HIDE_TAIL, 'normal_tail': NORMAL_TAIL,
                    'empty_tail': EMPTY_TAIL, 'release_tail': RELEASE_TAIL, 'cycle_start_tail': CYCLE_START_TAIL, 'cycle_frames': CYCLE_FRAMES},
          'idle_inputs': 'Super90IdleMatchWalk20261008 inputs.json + idle_patch.json (installed idle; not re-exported)', 'clips': [], 'stats': {}}
profiles = {fam: {'family': fam, 'clips': []} for fam in FAMILIES}
for empty in (False, True):
    for count in range(1, 8):
        name = f'A_Super90_loader_{"empty" if empty else "normal"}_{count}'
        frames = list(range(duration(count, empty) + 1))
        world = [pose(f, count, empty)[0] for f in frames]
        path = export_action(name, world, frames)
        report['clips'].append({'name': name, 'file': str(path), 'count': count, 'empty': empty, 'duration': frames[-1] / 60,
                                'contacts': [(INSERT + STEP * i) / 60 for i in range(count)],
                                'release': (last_frame(count) + RELEASE_TAIL) / 60 if empty else None,
                                'props_visible': [SHOW_BEGIN / 60, (last_frame(count) + HIDE_TAIL) / 60]})
        st = [w['_stats']['left'] for w in world]
        report['stats'][name] = {'max_reach_l': max(s['reach'] for s in st), 'min_reach_l': min(s['reach'] for s in st),
                                 'max_shoulder_shift_cm': max(s['shoulder_shift_cm'] for s in st)}
        for fam in FAMILIES:
            adapted = [pose(f, count, empty, fam)[0] for f in frames]
            profiles[fam]['clips'].append({'base': ANIM + name, 'duration': frames[-1] / 60, 'tracks': delta_tracks(world, adapted, frames)})
        print('AUTHORED', name, frames[-1] / 60, flush=True)
name = 'A_Super90_loader_cycle'; frames = list(range(CYCLE_FRAMES + 1))
world = [cycle_pose(f) for f in frames]; path = export_action(name, world, frames)
cycle_release = 1.1 * (RELEASE_TAIL - CYCLE_START_TAIL) / (EMPTY_TAIL - CYCLE_START_TAIL)
report['clips'].append({'name': name, 'file': str(path), 'count': 0, 'empty': True, 'duration': frames[-1] / 60, 'contacts': [], 'release': cycle_release, 'props_visible': None})
for fam in FAMILIES:
    adapted = [cycle_pose(f, fam) for f in frames]
    profiles[fam]['clips'].append({'base': ANIM + name, 'duration': frames[-1] / 60, 'tracks': delta_tracks(world, adapted, frames)})
for fam, data in profiles.items(): (O / (fam + '_profiles.json')).write_text(json.dumps(data, separators=(',', ':')), encoding='utf-8')
for clip in report['clips']: clip['sha256'] = hashlib.sha256(Path(clip['file']).read_bytes()).hexdigest()
rig.animation_data.action = bpy.data.actions['A_Super90_loader_normal_7']; rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_end = duration(7, False); scene.frame_set(0)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'Super90_Speedloader_R12.blend'))
(O / 'authoring.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('SUPER90_LOADER_R12_AUTHORED', len(report['clips']), 'clips; idle untouched', flush=True)
