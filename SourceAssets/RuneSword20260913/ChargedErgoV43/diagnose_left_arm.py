"""Measure the charged attack's left arm chain over the whole clip.

Read-only: opens the current rune-sword authoring source (V42 chain, which
carries the accepted V22 charged-arm fix) and samples the left arm every
half frame at the 480 Hz authoring rate. Also compares the two runtime arms
carriers so an animation-side defect can be told apart from a mesh-side one.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
RUNE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FROST = P.parent.parent / 'FrostSwordModules20260915/FrostSword_Modular_Editable.blend'
FPS = 480.0
CLIPS = ('HeavyCharge', 'HeavyRelease', 'Slash1')


def arm_carrier(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['SK_RuneSword_Rig']
    arms = bpy.data.objects['SK_Manny_Arms_Export']
    return {
        'blend': str(path),
        'rig_bones': len(rig.data.bones),
        'arms_vertices': len(arms.data.vertices),
        'arms_polygons': len(arms.data.polygons),
        'arms_vertex_groups': len(arms.vertex_groups),
        'arms_materials': [m.name if m else None for m in arms.data.materials],
        'arms_modifiers': [(m.type, getattr(m, 'object', None).name if getattr(m, 'object', None) else None)
                           for m in arms.modifiers],
        'clavicle_l_head': list(rig.data.bones['clavicle_l'].head_local),
        'upperarm_l_head': list(rig.data.bones['upperarm_l'].head_local),
        'upperarm_l_tail': list(rig.data.bones['upperarm_l'].tail_local),
        'lowerarm_l_tail': list(rig.data.bones['lowerarm_l'].tail_local),
        'hand_l_tail': list(rig.data.bones['hand_l'].tail_local),
    }


def measure(path, clips):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    rest_dir = {n: (rest[t].translation - rest[n].translation).normalized()
                for n, t in (('upperarm_l', 'lowerarm_l'), ('lowerarm_l', 'hand_l'))}

    out = {}
    for clip in clips:
        action = bpy.data.actions['A_RuneSword_' + clip]
        rig.animation_data.action = action
        rig.animation_data.action_slot = action.slots[0]
        start, end = map(int, action.frame_range)
        rows = []
        for half in range(start * 2, end * 2 + 1):
            f = half / 2.0
            scene.frame_set(int(f), subframe=f - int(f))
            bpy.context.view_layer.update()
            pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
            A = pose['upperarm_l'].translation
            E = pose['lowerarm_l'].translation
            H = pose['hand_l'].translation
            ud = (E - A).normalized()
            fd = (H - E).normalized()
            uq = pose['upperarm_l'].to_quaternion() @ rest['upperarm_l'].to_quaternion().inverted()
            fq = pose['lowerarm_l'].to_quaternion() @ rest['lowerarm_l'].to_quaternion().inverted()
            hq = pose['hand_l'].to_quaternion() @ rest['hand_l'].to_quaternion().inverted()
            # Forearm roll measured about its own axis against the frame the
            # upper-arm deformation would carry the forearm into.
            transport = uq @ rest_dir['lowerarm_l']
            relative = fq @ (transport.rotation_difference(fd) @ uq).inverted()
            axis = Vector((relative.x, relative.y, relative.z))
            roll = 2 * math.atan2(axis.dot(fd), relative.w)
            roll = (roll + math.pi) % (2 * math.pi) - math.pi
            rows.append({
                'frame': f,
                'seconds': f / FPS,
                'elbow_flex_deg': math.degrees(ud.angle(fd)),
                'elbow_roll_deg': math.degrees(roll),
                'wrist_bend_deg': math.degrees(fd.angle(hq @ rest_dir['lowerarm_l'])),
                'upper_axis_error_deg': math.degrees(ud.angle(uq @ rest_dir['upperarm_l'])),
                'fore_axis_error_deg': math.degrees(fd.angle(fq @ rest_dir['lowerarm_l'])),
                'upper_len_m': (E - A).length,
                'fore_len_m': (H - E).length,
            })
        out[clip] = rows
    return out


report = {'fps': FPS, 'carriers': {}, 'clips': {}}
report['carriers']['rune'] = arm_carrier(RUNE)
report['carriers']['frost'] = arm_carrier(FROST)
report['clips'] = measure(RUNE, CLIPS)

summary = {}
for clip, rows in report['clips'].items():
    keys = ('elbow_flex_deg', 'elbow_roll_deg', 'wrist_bend_deg',
            'upper_axis_error_deg', 'fore_axis_error_deg')
    entry = {'samples': len(rows), 'seconds': rows[-1]['seconds']}
    for key in keys:
        worst = max(rows, key=lambda r: abs(r[key]))
        entry[key] = {
            'max_abs': worst[key],
            'at_seconds': worst['seconds'],
            'mean_abs': sum(abs(r[key]) for r in rows) / len(rows),
        }
    # Where does the axial difference across the elbow stay above a threshold?
    for threshold in (20.0, 30.0, 45.0):
        hits = [r['seconds'] for r in rows if abs(rows[0]['elbow_roll_deg']) < 1e9 and abs(r['elbow_roll_deg']) > threshold]
        entry['elbow_roll_above_%d' % threshold] = {
            'count': len(hits),
            'first': hits[0] if hits else None,
            'last': hits[-1] if hits else None,
        }
    summary[clip] = entry
report['summary'] = summary

(P / 'left_arm_timeline.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('DIAGNOSE_DONE', flush=True)
print(json.dumps(summary, indent=2), flush=True)
