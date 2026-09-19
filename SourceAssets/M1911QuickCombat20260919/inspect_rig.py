"""检查 M1911_RearFinish_Editable.blend：rig 对象、action 列表、骨名与 idle 采样。"""
import bpy

SRC = r'D:\FPS3D\FPSGAME\SourceAssets\M1911RearRain20260913\M1911_RearFinish_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=SRC)

print('[INSPECT] objects:')
for o in bpy.data.objects:
    print('  obj %s type=%s' % (o.name, o.type))
print('[INSPECT] actions:')
for a in bpy.data.actions:
    print('  action %s frames=%s..%s' % (a.name, a.frame_start, a.frame_end))
armatures = [o for o in bpy.data.objects if o.type == 'ARMATURE']
for rig in armatures:
    bones = [b.name for b in rig.data.bones]
    print('[INSPECT] armature %s bones=%d' % (rig.name, len(bones)))
    print('[INSPECT] wpn bones:', [n for n in bones if n.startswith('WPN')])
    print('[INSPECT] hand bones:', [n for n in bones if 'hand' in n])
    print('[INSPECT] clavicle/upperarm:', [n for n in bones if n.startswith(('clavicle', 'upperarm', 'lowerarm'))])
    print('[INSPECT] fingers:',
          [n for n in bones if n.startswith(('thumb_', 'index_', 'middle_', 'ring_', 'pinky_'))])
    print('[INSPECT] root-ish:', [n for n in bones if n in ('root', 'pelvis', 'spine_01', 'spine_02', 'spine_03')])
print('[INSPECT] M1911_QUICKCOMBAT_INSPECT_DONE')
