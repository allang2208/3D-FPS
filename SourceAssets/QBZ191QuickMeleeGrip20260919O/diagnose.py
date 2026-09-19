import bpy,json,math,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
src=P.parent/'RifleQuickMelee20260919/QBZ191/Base/QBZ191_QuickCombat_Base_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(src))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
def pose(f):
 s.frame_set(f);bpy.context.view_layer.update();return {b.name:b.matrix.copy() for b in r.pose.bones}
idle=pose(0);hi=idle['WPN_root'].inverted()@idle['hand_r']
ref=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
rows=[]
for f in [0,8,12,20,32,60,86,100,108]:
 p=pose(f);h=p['WPN_root'].inverted()@p['hand_r'];fixed=p['WPN_root']@hi
 sh,el,wr=[p[n].translation for n in ['upperarm_r','lowerarm_r','hand_r']]
 a,b=(el-sh).length,(wr-el).length;v=fixed.translation-sh;d=v.length;axis=v.normalized()
 desired=fixed.to_quaternion()@rest['hand_r'].to_quaternion().inverted()@ref
 along=(a*a-b*b+d*d)/(2*d);rad=math.sqrt(max(0,a*a-along*along));center=sh+axis*along
 pole=-desired+axis*desired.dot(axis);pole.normalize();best=center+rad*pole
 rows.append({'frame':f,'relative_grip_shift_cm':100*(h.translation-hi.translation).length,
 'relative_grip_turn_deg':math.degrees(hi.to_quaternion().rotation_difference(h.to_quaternion()).angle),
 'fixed_min_bend':math.degrees(desired.angle((fixed.translation-best).normalized())),
 'shoulder':list(sh),'wrist':list(wr),'fixed_wrist':list(fixed.translation),'desired_fore':list(desired),
 'root': [list(row) for row in p['WPN_root']], 'lengths':[a,b]})
(P/'diagnosis.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2),flush=True)
