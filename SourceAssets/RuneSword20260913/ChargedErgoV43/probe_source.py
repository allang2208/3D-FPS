"""Read-only probe: current charged-attack source state and left-arm chain."""
import bpy, json, sys
from pathlib import Path

P = Path(__file__).parent
SOURCE = P.parent / 'OffscreenLeftInspectV42/AzureRunesword_OffscreenLeftInspectV42.blend'

bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']

report = {
    'source': str(SOURCE),
    'fps': scene.render.fps / scene.render.fps_base,
    'objects': sorted(o.name for o in bpy.data.objects),
    'rig_scale': list(rig.scale),
    'bone_count': len(rig.data.bones),
    'left_chain_children': {},
    'actions': {},
}

for name in ('upperarm_l', 'lowerarm_l', 'hand_l', 'upperarm_twist_01_l', 'upperarm_twist_02_l', 'clavicle_l'):
    bone = rig.data.bones.get(name)
    report['left_chain_children'][name] = sorted(b.name for b in bone.children_recursive) if bone else None

for action in bpy.data.actions:
    start, end = action.frame_range
    report['actions'][action.name] = {
        'frames': [start, end],
        'seconds': (end - start) / (scene.render.fps / scene.render.fps_base),
        'slots': [s.name_display for s in action.slots] if hasattr(action, 'slots') else [],
    }

(P / 'probe_source.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PROBE_DONE', flush=True)
