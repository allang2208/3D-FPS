"""Blender (background): where the rebuilt magazine and the fixed magwell collar sit in the
A762 authoring file, in armature space (metres), at rest. Read-only.

blender -b <A762_AccessoryReady_Editable.blend> -P probe_magwell_source.py
"""
import bpy
from mathutils import Vector

arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
inv = arm.matrix_world.inverted()
print('ARMATURE', arm.name)
for b in ('WPN_root', 'WPN_SOCKET_Magazine', 'WPN_bolt'):
    if b in arm.data.bones:
        print('BONE', b, tuple(round(x, 5) for x in arm.data.bones[b].head_local))


def bbox(objs):
    pts = [inv @ (o.matrix_world @ v.co) for o in objs for v in o.data.vertices]
    lo = [round(min(p[i] for p in pts), 4) for i in range(3)]
    hi = [round(max(p[i] for p in pts), 4) for i in range(3)]
    return lo, hi


groups = {
    'collar': [o for o in bpy.data.objects if o.type == 'MESH' and 'MagwellCollar' in o.name],
    'magazine_shell': [o for o in bpy.data.objects if o.type == 'MESH' and 'Magazine_CompleteShell' in o.name],
    'magazine_follower': [o for o in bpy.data.objects if o.type == 'MESH' and 'Magazine_Follower' in o.name],
    'receiver': [o for o in bpy.data.objects if o.type == 'MESH' and o.name == 'A762_Receiver'],
    'trigger': [o for o in bpy.data.objects if o.type == 'MESH' and o.name == 'A762_Trigger'],
    'bolt': [o for o in bpy.data.objects if o.type == 'MESH' and o.name == 'A762_Bolt'],
}
for k, objs in groups.items():
    if objs:
        print('BBOX', k, [o.name for o in objs][:3], bbox(objs))
    else:
        print('BBOX', k, 'missing')
