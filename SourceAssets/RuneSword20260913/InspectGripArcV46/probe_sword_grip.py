"""How the sword moves relative to the hand, and how the sword is bound.

``G(t) = inverse(hand) x sword`` is the whole twirl as seen from the palm, and
is what has to be rebuilt to match the reference.  The pivot of that motion is
the fixed point of G, which is the practical definition of the contact point.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).parent
SOURCES = {
    'v42': P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend',
    'v46': P / 'AzureRunesword_InspectGripArcV46.blend',
}
FPS = 120.0
CLIP = 'A_RuneSword_Inspect'
SWORD_BONES = ('WPN_root', 'WPN_root_r', 'Weapon_r', 'RuneSword_root')


def describe(rig):
    out = {'bones': {}}
    for bone in rig.data.bones:
        if bone.parent is None or 'WPN' in bone.name or 'Weapon' in bone.name \
                or 'RuneSword' in bone.name:
            out['bones'][bone.name] = {
                'parent': bone.parent.name if bone.parent else None,
                'children': [b.name for b in bone.children],
            }
    return out


report = {}
for label, path in SOURCES.items():
    bpy.ops.wm.open_mainfile(filepath=str(path))
    scene = bpy.context.scene
    rig = bpy.data.objects['SK_RuneSword_Rig']
    action = bpy.data.actions[CLIP]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]

    sword = None
    for name in SWORD_BONES:
        if name in rig.pose.bones:
            sword = name
            break
    entry = {'source': str(path), 'sword_bone': sword, 'rig': describe(rig)}
    entry['meshes'] = {}
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ('Rune' in ob.name or 'Sword' in ob.name):
            entry['meshes'][ob.name] = {
                'parent': ob.parent.name if ob.parent else None,
                'parent_type': ob.parent_type,
                'parent_bone': ob.parent_bone,
                'modifiers': [m.type for m in ob.modifiers],
                'vertex_groups': [g.name for g in ob.vertex_groups][:12],
            }

    start, end = map(int, action.frame_range)
    rows = []
    for f in range(start, end + 1, 2):
        scene.frame_set(f)
        bpy.context.view_layer.update()
        hand = rig.pose.bones['hand_r'].matrix
        weapon = rig.pose.bones[sword].matrix
        relative = hand.inverted() @ weapon
        translation, rotation, scale = relative.decompose()
        axis, angle = rotation.to_axis_angle()
        rows.append({
            'frame': f, 'seconds': round(f / FPS, 4),
            'angle_deg': round(math.degrees(angle), 2),
            'axis': [round(v, 3) for v in axis],
            'offset_m': [round(v, 5) for v in translation],
            'sword_head': [round(v, 4) for v in weapon.translation],
            'hand_head': [round(v, 4) for v in hand.translation],
        })
    entry['rows'] = rows
    report[label] = entry

(P / 'probe_sword_grip.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

for label, entry in report.items():
    print('=== %s sword bone=%s parent=%s' % (
        label, entry['sword_bone'],
        entry['rig']['bones'].get(entry['sword_bone'], {}).get('parent')))
    for name, info in entry['meshes'].items():
        print('    mesh %s parent=%s(%s) mods=%s groups=%s'
              % (name, info['parent'], info['parent_bone'], info['modifiers'],
                 info['vertex_groups'][:6]))
for label, entry in report.items():
    print('=== relative motion %s' % label)
    print('%7s %7s %8s %-22s %-28s %-22s' % ('frame', 'sec', 'angle', 'axis',
                                              'offset', 'sword_head'))
    for row in entry['rows']:
        if 0.30 <= row['seconds'] <= 1.0:
            print('%7d %7.3f %8.1f %-22s %-28s %-22s'
                  % (row['frame'], row['seconds'], row['angle_deg'],
                     row['axis'], row['offset_m'], row['sword_head']))
print('PROBE_SWORD_GRIP_DONE')
