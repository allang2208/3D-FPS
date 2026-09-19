import bpy,json
from pathlib import Path
O=Path(__file__).parent;out={}
for gun,file,frame in [('M4','ExtMagRebuild20260919/M4_ExtMag_reload_Editable.blend',76),('AKM','AKMReloadPolish20260911/base/A_AKM_reload.blend',148)]:
 bpy.ops.wm.open_mainfile(filepath=str(O.parent/file));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
 W=r.matrix_world;M=W@r.pose.bones['WPN_SOCKET_Magazine'].matrix@r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()@W.inverted()
 out[gun]={n:list((M.inverted()@W@r.pose.bones[n].matrix).translation) for n in ['hand_l','thumb_01_l','thumb_03_l','index_01_l','index_03_l','middle_01_l','middle_03_l','ring_01_l','ring_03_l','pinky_01_l','pinky_03_l']}
(O/'contact_coordinates.json').write_text(json.dumps(out,indent=2))
