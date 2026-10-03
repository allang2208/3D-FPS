"""List the action each PKM family editable blend carries."""
import json
from pathlib import Path

import bpy

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
BLENDS = []
for fam in ('angled', 'canted', 'prism', 'vertical'):
    BLENDS.append((fam, 'idle', ROOT / 'GripContact15' / ('PKM_%s_Editable.blend' % fam)))
    BLENDS.append((fam, 'reload', ROOT / 'Reload16' / ('PKM_%s_Reload_Editable.blend' % fam)))
    BLENDS.append((fam, 'reload_empty', ROOT / 'Charge34' / ('PKM_%s_ChargePush_Editable.blend' % fam)))

out = {}
for fam, clip, path in BLENDS:
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects.get('PKM_Manny_Rig')
    actions = []
    for a in bpy.data.actions:
        actions.append({'name': a.name,
                        'range': [int(a.frame_range[0]), int(a.frame_range[1])],
                        'fcurves': sum(len(bag.fcurves) for layer in a.layers
                                       for strip in layer.strips
                                       for bag in strip.channelbags)})
    out['%s/%s' % (fam, clip)] = {'file': path.name, 'rig': bool(rig),
                                  'fps': bpy.context.scene.render.fps,
                                  'actions': actions}
    print('%-24s %-46s fps=%s' % (fam + '/' + clip, path.name, bpy.context.scene.render.fps))
    for a in actions:
        print('     %-34s frames %s  fcurves %d' % (a['name'], a['range'], a['fcurves']))

(Path(__file__).parent / 'family_actions.json').write_text(
    json.dumps(out, indent=2), encoding='utf-8')
print('FAMILY_PROBE_DONE')