"""Which local bone axis points along the limb, and what the rest frame looks like."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
NAMES = ('upperarm_r', 'upperarm_twist_01_r', 'upperarm_twist_02_r', 'lowerarm_r',
         'lowerarm_twist_01_r', 'lowerarm_twist_02_r', 'hand_r', 'middle_01_r')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
action = bpy.data.actions['A_RuneSword_Inspect']
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()

rows = {}
for name in NAMES:
    bone = rig.data.bones.get(name)
    if bone is None:
        continue
    matrix = rest[name]
    axes = {}
    for label, vector in (('X', Vector((1, 0, 0))), ('Y', Vector((0, 1, 0))),
                          ('Z', Vector((0, 0, 1)))):
        axes[label] = [round(v, 4) for v in (matrix.to_3x3() @ vector).normalized()]
    children = [b.name for b in bone.children]
    tail = rest[children[0]].translation if children else None
    length = bone.length
    rows[name] = {
        'rest_head': [round(v, 4) for v in matrix.translation],
        'rest_child_head': None if tail is None else [round(v, 4) for v in tail],
        'bone_length': round(length, 4),
        'rest_axes': axes,
        'children': children,
    }

(P / 'probe_bone_axes.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
for name, entry in rows.items():
    print('%-22s len=%.4f children=%s' % (name, entry['bone_length'], entry['children']))
    print('    head=%s child=%s' % (entry['rest_head'], entry['rest_child_head']))
    for label in ('X', 'Y', 'Z'):
        print('    %s -> %s' % (label, entry['rest_axes'][label]))
    if entry['rest_child_head']:
        direction = Vector(entry['rest_child_head']) - Vector(entry['rest_head'])
        direction.normalize()
        for label in ('X', 'Y', 'Z'):
            axis = Vector(entry['rest_axes'][label])
            print('    angle(child_dir, %s) = %.1f deg'
                  % (label, math.degrees(direction.angle(axis))))
print('PROBE_BONE_AXES_DONE')
