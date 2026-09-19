"""Measure skin distortion of the left arm across the charged attack.

Compares evaluated (armature-deformed) edge lengths against the rest mesh and
attributes the worst distortion to the dominant bone of each edge. The right
arm is measured with the same method as a control, and Idle supplies the
baseline. Read-only; nothing is saved into the blend.
"""
import bpy, json
import numpy as np
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'
FPS = 480.0
CLIPS = ('Guard', 'HeavyCharge', 'HeavyRelease', 'Slash1', 'Slash2')
STRIDE = 2  # sample every 2 authoring frames (240 Hz)
WATCH = ('upperarm_l', 'lowerarm_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l',
         'lowerarm_twist_01_l', 'lowerarm_twist_02_l', 'hand_l',
         'upperarm_r', 'lowerarm_r', 'lowerarm_twist_01_r', 'upperarm_twist_01_r')

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']

rest = np.array([v.co for v in arms.data.vertices], dtype=np.float64)
edges = np.array([tuple(e.vertices) for e in arms.data.edges], dtype=np.int64)
rest_len = np.linalg.norm(rest[edges[:, 0]] - rest[edges[:, 1]], axis=1)
keep_edge = rest_len > 1e-6
edges = edges[keep_edge]
rest_len = rest_len[keep_edge]

group_index = {g.name: g.index for g in arms.vertex_groups}
weights = np.zeros((len(rest), len(group_index)), dtype=np.float64)
for v in arms.data.vertices:
    for g in v.groups:
        weights[v.index, g.group] = g.weight


def dominant_mask(name, threshold=0.5):
    index = group_index.get(name)
    if index is None:
        return np.zeros(len(rest), dtype=bool)
    owned = weights[:, index] > threshold
    other = weights.sum(axis=1) - weights[:, index]
    return owned & (weights[:, index] >= other)


bone_edges = {}
for name in WATCH:
    mask = dominant_mask(name)
    bone_edges[name] = np.where(mask[edges[:, 0]] & mask[edges[:, 1]])[0]

depsgraph = bpy.context.evaluated_depsgraph_get()
report = {'source': str(SOURCE), 'stride_frames': STRIDE, 'clips': {}}

for clip in CLIPS:
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    start, end = map(int, action.frame_range)
    frames = list(range(start, end + 1, STRIDE))
    rows = []
    for f in frames:
        scene.frame_set(f)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        evaluated = arms.evaluated_get(depsgraph)
        co = np.array([v.co for v in evaluated.data.vertices], dtype=np.float64)
        current = np.linalg.norm(co[edges[:, 0]] - co[edges[:, 1]], axis=1)
        ratio = current / rest_len
        entry = {'frame': f, 'seconds': f / FPS}
        for name, index in bone_edges.items():
            if len(index) == 0:
                continue
            r = ratio[index]
            entry[name] = {
                'p999': float(np.quantile(r, .999)),
                'max': float(r.max()),
                'min': float(r.min()),
                'mean': float(r.mean()),
            }
        rows.append(entry)
    report['clips'][clip] = rows

summary = {}
for clip, rows in report['clips'].items():
    bones = sorted({k for row in rows for k in row if k not in ('frame', 'seconds')})
    entry = {}
    for bone in bones:
        series = [row[bone]['p999'] for row in rows if bone in row]
        worst = max(rows, key=lambda r: r[bone]['p999'] if bone in r else 0)
        entry[bone] = {
            'worst_p999': worst[bone]['p999'],
            'at_seconds': worst['seconds'],
            'mean_p999': float(np.mean(series)),
        }
    summary[clip] = entry

report['summary'] = summary
(P / 'skin_distortion.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

print('DISTORTION_DONE', flush=True)
for clip in CLIPS:
    print('===', clip)
    for bone, value in summary[clip].items():
        print('   %-24s worst p999=%.3f at %.3f s  mean=%.3f'
              % (bone, value['worst_p999'], value['at_seconds'], value['mean_p999']))
