import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;P=O.parents[1]
f=P/'SourceAssets/Super90LocomotionIdleGrip20261010/Super90_Locomotion_IdleGrip_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(f),use_scripts=False)
r=bpy.data.objects['SK_Super90'];s=bpy.context.scene
print('RIG',r.name,[list(row) for row in r.matrix_world])
print('ACTIONS',[a.name for a in bpy.data.actions if 'idle' in a.name.lower() or 'reload' in a.name.lower()])
for ob in s.objects:
 if ob.type=='MESH':print('MESH',ob.name,len(ob.data.vertices),[m.name if m else '' for m in ob.data.materials])
for n in ('WPN_root','WPN_Trigger','WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Muzzle','WPN_bolt','hand_r','hand_l'):
 print('BONE',n,'rest',list(r.data.bones[n].matrix_local.translation),'pose',list(r.pose.bones[n].matrix.translation))
