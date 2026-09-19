exec(open('D:/FPS3D/FPSGAME/SourceAssets/M4Infima/check_export.py').read().split("d=bpy.data.cameras.new")[0])
import json
print('RIG',list(rig.matrix_world),[(b.name,list(b.matrix.translation),list(b.scale))for b in rig.pose.bones if b.name in ['hand_r','WPN_root','VM_Root']])
for o in s.objects:
 if o.type=='MESH' and o.parent==rig:
  print('MESH',o.name,list(o.matrix_world),len(o.data.vertices),list(o.data.vertices[0].co),[(g.group,g.weight)for g in o.data.vertices[0].groups])
for n in ['WPN_root','hand_r']:
 b=rig.pose.bones[n];print('DELTA',n,list(b.matrix@b.bone.matrix_local.inverted()))
for o in s.objects:
 if o.type=='MESH' and o.parent==rig and o.name.startswith('SK_Manny'):
  used={g.group for v in o.data.vertices for g in v.groups if g.weight>0}
  print('MISSING_GROUPS',[(g.name,g.index)for g in o.vertex_groups if g.index in used and g.name not in rig.data.bones])
  print('MOD',[(m.name,m.type)for m in o.modifiers])
