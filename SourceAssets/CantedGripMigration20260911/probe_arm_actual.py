import bpy,json,sys
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O));from audit_m4 import render
for label,file in [('fit',O/'Canted_Refit.blend'),('baked',O/'m4/canted/A_M4_Canted_idle.blend')]:
 bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0);f=json.loads((O/'m4/canted/fit_final.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(f['grip_in_root']);print(label,{n:list(G.inverted()@r.pose.bones[n].matrix.translation) for n in ['upperarm_l','lowerarm_l','hand_l']});render(r,G,'actual_'+label)
