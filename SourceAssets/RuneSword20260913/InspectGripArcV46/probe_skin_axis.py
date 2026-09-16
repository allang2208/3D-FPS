"""Where along each bone axis does the dominant skin of the arm chain sit?

Needed to place the roll gradient on the bones that actually deform the mesh,
the same way the charged-attack forearm fix measured 0.286 / 0.859.
"""
import bpy, json
from collections import Counter, defaultdict
from pathlib import Path
from mathutils import Vector

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
CHAIN = {}
for side in ('l', 'r'):
    CHAIN[side] = ('clavicle_' + side, 'upperarm_' + side,
                   'upperarm_twist_01_' + side, 'upperarm_twist_02_' + side,
                   'lowerarm_' + side, 'lowerarm_twist_01_' + side,
                   'lowerarm_twist_02_' + side, 'hand_' + side)

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}


# Limb segments, not individual helper bones: the helpers are short carriers
# parked at one end of the limb, so a position has to be measured against the
# joint-to-joint axis the skin actually spans.
LIMB = {
    'upperarm': ('upperarm', 'lowerarm'),
    'lowerarm': ('lowerarm', 'hand'),
    'hand': ('hand', 'middle_01'),
}


def limb_name(bone):
    for prefix in ('upperarm', 'lowerarm', 'hand'):
        if bone.startswith(prefix):
            return prefix
    return None


def bone_segment(name):
    """Proximal joint and distal joint of the limb that carries this bone."""
    limb = limb_name(name)
    if limb is None:
        head = rest[name].translation
        tail = rest[name] @ Vector((0.0, rig.data.bones[name].length, 0.0))
        return head, tail
    proximal, distal = LIMB[limb]
    side = name.rsplit('_', 1)[-1]
    return rest[proximal + '_' + side].translation, rest[distal + '_' + side].translation


dominant = Counter()
along = defaultdict(list)
for vertex in arms.data.vertices:
    if not vertex.groups:
        continue
    best = max(vertex.groups, key=lambda g: g.weight)
    group = arms.vertex_groups[best.group].name
    dominant[group] += 1
    along[group].append(vertex.co.copy())

report = {'source': str(SOURCE), 'bones': {}}
for side in ('l', 'r'):
    for name in CHAIN[side]:
        head, tail = bone_segment(name)
        axis = tail - head
        length = axis.length
        axis = axis / length
        points = along.get(name, [])
        if points:
            positions = sorted((p - head).dot(axis) / length for p in points)
            median = positions[len(positions) // 2]
            low = positions[int(len(positions) * 0.1)]
            high = positions[int(len(positions) * 0.9)]
        else:
            median = low = high = None
        report['bones'][name] = {
            'dominant_vertices': dominant.get(name, 0),
            'length_m': round(length, 5),
            'axis_position_median': None if median is None else round(median, 4),
            'axis_position_p10': None if low is None else round(low, 4),
            'axis_position_p90': None if high is None else round(high, 4),
        }

(P / 'probe_skin_axis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
for name, entry in report['bones'].items():
    print('%-24s verts=%-5d len=%.4f median=%s p10=%s p90=%s' % (
        name, entry['dominant_vertices'], entry['length_m'],
        entry['axis_position_median'], entry['axis_position_p10'],
        entry['axis_position_p90']))
print('PROBE_SKIN_AXIS_DONE')
