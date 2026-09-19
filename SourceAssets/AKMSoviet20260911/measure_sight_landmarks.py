import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'AKM_Soviet_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_aim'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
source={'front':(0,-.49903938,.08407259),'rear':(-.00004109,-.1060,.08933),'muzzle':(0,-.5220779,.03745)}
out={k:{'source':list(v),'root_local':list(Vector(v)*.985+Vector((.0008,-.066,.014)))} for k,v in source.items()}
out['old_bones']={n:list((root.inverted()@r.pose.bones[n].matrix).translation) for n in ['WPN_RearSight','WPN_FrontSight','WPN_SOCKET_Muzzle']}
(O/'sight_landmarks.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
