"""Where do the forearm/upper-arm twist helpers actually hold skin?"""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']

groups = {g.name: g.index for g in arms.vertex_groups}
weights = {}
for vertex in arms.data.vertices:
    weights[vertex.index] = {g.group: g.weight for g in vertex.groups}


def along(name, head_bone, tail_bone):
    """Normalised position of each dominant vertex along the limb bone axis."""
    head = rig.data.bones[head_bone].head_local
    tail = rig.data.bones[tail_bone].tail_local
    axis = (tail - head)
    length = axis.length
    axis = axis.normalized()
    index = groups.get(name)
    positions = []
    for vertex in arms.data.vertices:
        weight = weights[vertex.index].get(index, 0.0)
        if weight <= .5:
            continue
        total = sum(weights[vertex.index].values())
        if weight < total - weight:
            continue
        positions.append((vertex.co - head).dot(axis) / length)
    if not positions:
        return None
    positions.sort()
    return {
        'vertices': len(positions),
        'min': positions[0],
        'p10': positions[int(len(positions) * .1)],
        'median': positions[len(positions) // 2],
        'p90': positions[int(len(positions) * .9)],
        'max': positions[-1],
    }


report = {
    'upperarm': {name: along(name, 'upperarm_l', 'lowerarm_l') for name in
                 ('upperarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l')},
    'lowerarm': {name: along(name, 'lowerarm_l', 'hand_l') for name in
                 ('lowerarm_l', 'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l')},
    'bone_lengths_m': {
        'upperarm_l': (rig.data.bones['lowerarm_l'].head_local - rig.data.bones['upperarm_l'].head_local).length,
        'lowerarm_l': (rig.data.bones['hand_l'].head_local - rig.data.bones['lowerarm_l'].head_local).length,
    },
    'twist_parents': {name: (rig.data.bones[name].parent.name if rig.data.bones[name].parent else None)
                      for name in ('lowerarm_twist_01_l', 'lowerarm_twist_02_l',
                                   'upperarm_twist_01_l', 'upperarm_twist_02_l')},
}
(P / 'twist_weights.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
print('TWIST_WEIGHTS_DONE')
