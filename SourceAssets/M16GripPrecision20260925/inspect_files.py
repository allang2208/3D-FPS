"""Structural read of the current M4 / M16 insertion sources (no writes)."""
import bpy, json, sys
from pathlib import Path
O = Path(__file__).parent; S = O.parent
report = {}
def dump(label, path, action=None):
    bpy.ops.wm.open_mainfile(filepath=str(path), use_scripts=False)
    r = bpy.data.objects['SK_M4_Infima']
    a = bpy.data.actions[action] if action else r.animation_data.action
    meshes = []
    for o in bpy.context.scene.objects:
        if o.type != 'MESH':
            continue
        par = o.parent.name if o.parent else None
        mods = [m.type for m in o.modifiers]
        vg = [g.name for g in o.vertex_groups]
        meshes.append({'name': o.name, 'parent': par, 'parent_type': o.parent_type,
                       'parent_bone': o.parent_bone, 'mods': mods, 'groups': len(vg),
                       'verts': len(o.data.vertices), 'world': [list(row) for row in o.matrix_world]})
    report[label] = {'file': str(path), 'action': a.name if a else None,
                     'armature': r.name, 'bones': [b.name for b in r.pose.bones],
                     'meshes': meshes, 'fps': bpy.context.scene.render.fps,
                     'frame_range': list(a.frame_range) if a else None}
dump('m4_reload', S/'ExtMagContact20260919/A_M4_ExtContact_reload.blend')
dump('m16_reload', S/'M16RemovalMelee20260920/Animations/base/A_M16_reload.blend')
dump('m16_idle', S/'M16Gameplay20260919/M16_Manny_Editable.blend', 'M16_idle')
(O/'inspect_files.json').write_text(json.dumps(report, indent=2))
print('INSPECT_OK', flush=True)