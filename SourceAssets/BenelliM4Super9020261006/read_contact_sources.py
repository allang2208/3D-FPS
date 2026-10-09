import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(r'D:/FPS3D/FPSGAME');O=P/'SourceAssets/BenelliM4Super9020261006'
bpy.ops.wm.open_mainfile(filepath=str(O/'BenelliM4_Original_Editable.blend'));r=bpy.data.objects['Rig'];s=bpy.context.scene
rows={}
for clip in ['M4_Idle','M4_ReloadOne_type1','M4_ReloadFull_type1','M4_ReloadOne_type2']:
 a=next(a for a in bpy.data.actions if a.name.endswith('|'+clip));r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 rows[clip]=[]
 for f in range(int(a.frame_range[0]),int(a.frame_range[1])+1,5):
  s.frame_set(f);bpy.context.view_layer.update();row={'frame':f,'t':(f-1)/s.render.fps}
  for n in ['Main','Slider','Load','Shell','hand_L','hand_R','lowerarm_L','lowerarm_R','upperarm_L','upperarm_R']:
   m=r.matrix_world@r.pose.bones[n].matrix;row[n]=[list(x) for x in m]
  rows[clip].append(row)
(O/'source_contact_tracks.json').write_text(json.dumps(rows,indent=2))
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'));r=bpy.data.objects['SK_M4_Infima'];print('TARGET_RIG',r.matrix_world)
for n in ['clavicle_l','upperarm_l','lowerarm_l','hand_l','hand_r','index_metacarpal_l','index_01_l','index_02_l','index_03_l','WPN_root']:
 if n in r.data.bones:print(n,'head',list(r.data.bones[n].head_local),'tail',list(r.data.bones[n].tail_local),'axes',[list(x) for x in r.data.bones[n].matrix_local.to_3x3()])
print('ALL_BONES',list(r.data.bones.keys()))
