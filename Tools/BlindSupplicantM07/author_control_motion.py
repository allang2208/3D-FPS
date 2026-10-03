"""Fit existing humanoid stun and recovery sources to M07's own bind skeleton.

Only source animation poses are evaluated for authoring. Cloth evaluation,
gameplay, simulation, renders and acceptance tests are never started.
"""
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT / 'Motion'
FPS = 30
SOURCES = {
    'Dizzy': ROOT.parent / 'HumanoidStun20260926/fitted/A_Nurse_Dizzy.fbx',
    'Fall': ROOT.parent / 'HumanoidKnockdown20260926/fitted/A_Nurse_Hit_Knockback.fbx',
    'GetUp': ROOT.parent / 'HumanoidKnockdown20260926/fitted/A_Nurse_LayToIdle.fbx',
    'ProneGetUp': ROOT.parent / 'HumanoidKnockdown20260926/fitted/A_Nurse_ProneToIdle.fbx',
}


def update():
    bpy.context.view_layer.update()


def activate(rig, action):
    rig.animation_data_create()
    rig.animation_data.action = action
    if action and action.slots:
        rig.animation_data.action_slot = action.slots[0]
    for track in rig.animation_data.nla_tracks:
        track.mute = True


def read_sources():
    result = {}
    for suffix, path in SOURCES.items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(path), use_anim=True)
        donor = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        action = donor.animation_data.action
        activate(donor, action)
        rate = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
        start, end = action.frame_range
        duration = (end - start) / rate
        samples = []
        for i in range(round(duration * FPS) + 1):
            f = start + i / FPS * rate
            bpy.context.scene.frame_set(math.floor(f), subframe=f % 1)
            samples.append({p.name: donor.matrix_world @ p.matrix for p in donor.pose.bones})
        result[suffix] = {
            'frames': samples, 'duration': (len(samples) - 1) / FPS,
            'rest': {b.name: donor.matrix_world @ b.matrix_local for b in donor.data.bones},
            'source_action': action.name, 'source_fps': rate,
        }
    return result


def set_matrix(rig, name, matrix):
    rig.pose.bones[name].matrix = matrix
    update()


def solve_leg(rig, side, destination):
    first, mid, last = [rig.pose.bones[p + '_' + side] for p in ('thigh', 'calf', 'foot')]
    p0, p1, p2 = [p.matrix.translation.copy() for p in (first, mid, last)]
    l1, l2 = (p1 - p0).length, (p2 - p1).length
    direction = destination - p0
    distance = max(.0001, min(direction.length, l1 + l2 - .00001))
    direction.normalize()
    along = (l1*l1 - l2*l2 + distance*distance) / (2*distance)
    pole = p1 - p0
    pole -= direction * pole.dot(direction)
    if pole.length < .00001:
        pole = Vector((0, -1, 0))
        pole -= direction * pole.dot(direction)
    pole.normalize()
    elbow = p0 + direction * along + pole * math.sqrt(max(0, l1*l1 - along*along))
    ankle_q = last.matrix.to_quaternion()
    q = (p1 - p0).rotation_difference(elbow - p0) @ first.matrix.to_quaternion()
    set_matrix(rig, first.name, Matrix.LocRotScale(p0, q, Vector((1, 1, 1))))
    pm, pe = mid.matrix.translation.copy(), last.matrix.translation.copy()
    q = (pe - pm).rotation_difference(p0 + direction*distance - pm) @ mid.matrix.to_quaternion()
    set_matrix(rig, mid.name, Matrix.LocRotScale(pm, q, Vector((1, 1, 1))))
    set_matrix(rig, last.name, Matrix.LocRotScale(last.matrix.translation, ankle_q, Vector((1, 1, 1))))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = read_sources()
    bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'Authoring/M07_Separated_Master.blend'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE' and
               o.data.bones.get('gill_01_00') is not None)
    # The control delivery is deliberately rig-only. The original editable
    # body/cloth master remains untouched, and no display modifier is evaluated.
    for obj in list(bpy.data.objects):
        if obj != rig:
            bpy.data.objects.remove(obj, do_unlink=True)
    activate(rig, None)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)
    rig.hide_set(False)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.render.fps_base = 1
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    world_rest = {n: rig.matrix_world @ m for n, m in rest.items()}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    inv = rig.matrix_world.inverted()
    for p in ordered:
        p.rotation_mode = 'QUATERNION'
    report = {'stage': 'M07 stun and reversible recovery source motions authored',
              'fps': FPS, 'tested': False, 'cloth_simulation_played': False,
              'animation_license': 'CC0-1.0',
              'source_repository': 'https://github.com/Mesh2Motion/mesh2motion-app',
              'source_commit': '2d3d1ff03247d9e7e830d1ae375653da4e2146e2',
              'license_file': str(ROOT.parent / 'HumanoidKnockdown20260926/LICENSE-CC0.MD'),
              'source_provenance': [str(ROOT.parent / 'HumanoidKnockdown20260926/source_manifest.json'),
                                    str(ROOT.parent / 'HumanoidStun20260926/source_manifest.json')],
              'clips': {}}
    for suffix, data in source.items():
        name = 'A_M07_' + suffix
        action = bpy.data.actions.new(name)
        action.use_fake_user = True
        activate(rig, action)
        scene.frame_start, scene.frame_end = 1, len(data['frames'])
        anchors = None
        previous = {}
        ratio = world_rest['pelvis'].translation.z / max(.1, data['rest']['pelvis'].translation.z)
        source_rest_pelvis = data['rest']['pelvis'].translation
        source_first = data['frames'][0]['pelvis'].translation
        drift = data['frames'][-1]['pelvis'].translation - source_first
        for index, raw in enumerate(data['frames']):
            frame = index + 1
            scene.frame_set(frame)
            target = {}
            for p in ordered:
                n, parent = p.name, p.parent.name if p.parent else None
                local = rest[parent].inverted() @ rest[n] if parent else rest[n]
                position = target[parent] @ local.translation if parent else rest[n].translation
                if n in raw:
                    delta = raw[n].to_quaternion() @ data['rest'][n].to_quaternion().inverted()
                    q = (inv.to_quaternion() @ delta @ world_rest[n].to_quaternion()).normalized()
                    if n == 'pelvis':
                        offset = raw[n].translation - source_rest_pelvis
                        # Preserve a fall/recovery's authored vertical displacement.
                        # Horizontal drift is removed so shared navigation owns travel.
                        offset.x -= source_first.x - source_rest_pelvis.x
                        offset.y -= source_first.y - source_rest_pelvis.y
                        if suffix == 'Dizzy':
                            offset -= drift * (index / max(1, scene.frame_end - 1))
                        position = inv @ (world_rest[n].translation + offset*ratio)
                    matrix = Matrix.LocRotScale(position, q, Vector((1, 1, 1)))
                else:
                    matrix = target[parent] @ local if parent else rest[n]
                target[n] = matrix
                p.matrix_basis = local.inverted() @ target[parent].inverted() @ matrix if parent else rest[n].inverted() @ matrix
            update()
            if suffix == 'Dizzy':
                if anchors is None:
                    anchors = {s: rig.pose.bones['foot_'+s].matrix.translation.copy() for s in ('l','r')}
                for side, point in anchors.items():
                    solve_leg(rig, side, point)
            else:
                # Contact sizing comes from the anatomical collision dimensions,
                # rather than the long outer membrane silhouette.
                radii = {'pelvis': .14, 'spine_02': .16, 'spine_04': .16,
                         'head': .14, 'hand_l': .025, 'hand_r': .025,
                         'foot_l': .03, 'foot_r': .03, 'ball_l': .02, 'ball_r': .02}
                low = min((rig.matrix_world @ rig.pose.bones[n].matrix.translation).z - radius
                          for n, radius in radii.items())
                if low < .002:
                    matrix = rig.pose.bones['pelvis'].matrix.copy()
                    matrix.translation += inv.to_3x3() @ Vector((0, 0, .002-low))
                    set_matrix(rig, 'pelvis', matrix)
            seconds = index / FPS
            for p in ordered:
                if p.name.startswith('gill_'):
                    panel, segment = map(int, p.name.split('_')[1:])
                    phase = (panel-1)*.38
                    period = max(.01, data['duration']) if suffix == 'Dizzy' else 4
                    wave = math.sin(2*math.pi*seconds/period-phase) - math.sin(-phase)
                    p.rotation_quaternion = Quaternion(Vector((1, 0, 0)), wave*math.radians(1+segment*.7))
                q = p.rotation_quaternion.copy()
                if p.name in previous and q.dot(previous[p.name]) < 0:
                    q.negate()
                    p.rotation_quaternion = q
                previous[p.name] = q
                for prop in ('location', 'rotation_quaternion', 'scale'):
                    p.keyframe_insert(data_path=prop, frame=frame, group=p.name)
        scene.frame_set(1)
        destination = OUT / (name + '.fbx')
        bpy.ops.export_scene.fbx(filepath=str(destination), use_selection=True, object_types={'ARMATURE'},
            add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
            bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
            bake_anim_simplify_factor=0, axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS')
        report['clips'][name] = {'file': str(destination), 'seconds': data['duration'], 'fps': FPS,
            'loop': suffix == 'Dizzy', 'source': str(SOURCES[suffix]), 'source_action': data['source_action'],
            'fit': 'M07 anatomical lengths, hierarchy, rest frames, inplace horizontal movement and gill breathing'}
        (OUT / 'control_motion_manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print('M07_CONTROL_EXPORTED ' + name, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'M07_ControlMotion.blend'))
    print(json.dumps({'saved': str(OUT / 'M07_ControlMotion.blend'), 'clips': list(report['clips']), 'tested': False}), flush=True)


if __name__ == '__main__':
    main()
