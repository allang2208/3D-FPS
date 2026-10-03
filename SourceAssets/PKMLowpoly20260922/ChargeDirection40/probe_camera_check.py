"""Where do the visible PKM arms/weapon actually sit in camera space?

Camera mapping from Framing11/read_handle.py:
    camera_cm = (rig_y*100 + anchor_x, rig_x*100 + anchor_y, rig_z*100 + anchor_z)
checked against the evaluated (skinned) meshes, not just bone heads.
"""
import json
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PKMLowpoly20260922')
HERE = ROOT / 'ChargeDirection40'
ANCHOR = (9.0, 9.0, -11.0)


def to_cam(p):
    return np.array([p[1] * 100 + ANCHOR[0], p[0] * 100 + ANCHOR[1],
                     p[2] * 100 + ANCHOR[2]])


def screen(p):
    if p[0] <= 1.0:
        return (float('nan'), float('nan'))
    h = p[0] * np.tan(np.radians(75.0) / 2.0)
    w = h * 16.0 / 9.0
    return (p[1] / w, p[2] / h)


out = {}
for label, blend in (('charge', ROOT / 'Charge34' / 'PKM_base_ChargePush_Editable.blend'),
                     ('hands', ROOT / 'HandReload10' / 'PKM_ReloadHands_Editable.blend')):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    rig = bpy.data.objects['PKM_Manny_Rig']
    scene.render.fps = 120
    print('\n===', label, blend.name, '===')
    print('actions with idle/reload:',
          [a.name for a in bpy.data.actions if 'idle' in a.name.lower()][:6])
    for action_name, frames in (('PKM_Game_idle', [0]),
                                ('PKM34_base_reload_empty', [0, 528, 600, 618, 696])):
        if action_name not in bpy.data.actions:
            print('  missing', action_name)
            continue
        a = bpy.data.actions[action_name]
        rig.animation_data.action = a
        rig.animation_data.action_slot = a.slots[0]
        for f in frames:
            scene.frame_set(f)
            bpy.context.view_layer.update()
            pb = rig.pose.bones

            def sh(name):
                if name not in pb:
                    return None
                p = to_cam(np.array(pb[name].head))
                s = screen(p)
                return (np.round(p, 1).tolist(), [round(v, 2) for v in s])
            info = {n: sh(n) for n in ('hand_l', 'hand_r', 'WPN_Trigger',
                                       'PKM_Charge', 'WPN_root')}
            dg = bpy.context.evaluated_depsgraph_get()
            arms = None
            for ob in scene.objects:
                if ob.type == 'MESH' and 'Arms' in ob.name and ob.parent == rig:
                    arms = ob
            bounds = None
            if arms:
                ev = arms.evaluated_get(dg)
                me = ev.to_mesh()
                pts = np.array([to_cam(np.array(ev.matrix_world @ v.co))
                                for v in me.vertices])
                bounds = [np.round(pts.min(axis=0), 1).tolist(),
                          np.round(pts.max(axis=0), 1).tolist()]
                ev.to_mesh_clear()
            print('  %-26s f%-4d arms_cam_bounds %s' % (action_name, f, bounds))
            for n, v in info.items():
                if v:
                    print('        %-16s cam %-24s screen %s' % (n, v[0], v[1]))
            out['%s/%s/%d' % (label, action_name, f)] = {'bones': info, 'arms': bounds}

(HERE / 'camera_check.json').write_text(json.dumps(out, indent=2), encoding='utf-8')
print('CAMERA_CHECK_DONE')