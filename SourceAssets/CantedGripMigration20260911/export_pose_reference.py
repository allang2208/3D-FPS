import bpy,json
from pathlib import Path
O=Path(__file__).parent;out={}
for weapon,variant in [('m4','canted')]+[('akm',v) for v in ['vertical','prism','angled','canted']]:
 d=O/weapon/variant;prefix=f'A_{weapon.upper()}_{"Canted" if weapon=="m4" else variant}_';bpy.ops.wm.open_mainfile(filepath=str(d/(prefix+'idle.blend')));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();out[weapon+'/'+variant]={n:list(r.pose.bones[n].matrix.translation*100) for n in ['WPN_root','upperarm_l','lowerarm_l','hand_l']+[d+'_'+str(j).zfill(2)+'_l' for d in ['index','middle','ring','pinky','thumb'] for j in [1,2,3]]}
(O/'pose_reference_cm.json').write_text(json.dumps(out,indent=2))
