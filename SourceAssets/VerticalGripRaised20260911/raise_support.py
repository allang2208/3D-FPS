import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;report={}
for key,title in [('vertical','Vertical'),('prism','Prism')]:
 olddir=O.parent/'VerticalGripClass20260911'/key;d=O/key;bpy.ops.wm.open_mainfile(filepath=str(olddir/f'A_M4_{title}_idle.blend'));r=bpy.data.objects['SK_M4_Infima'];bpy.context.scene.frame_set(0);bpy.context.view_layer.update();fit=json.loads((d/'fit_final.json').read_text());profile=json.loads((d/'profile.json').read_text());G=r.pose.bones['WPN_root'].matrix@Matrix(fit['grip_in_root']);v=Vector(profile['forearm_direction']);new=Vector((v.x,v.y,0)).normalized()*math.sqrt(1-.34**2)+Vector((0,0,.34));l2=(r.data.bones['hand_l'].head_local-r.data.bones['lowerarm_l'].head_local).length;oldE=r.pose.bones['lowerarm_l'].head.copy();E=r.pose.bones['hand_l'].head-G.to_3x3()@new*l2;delta=E-oldE;profile['shoulder_offset']=list(Vector(profile['shoulder_offset'])+delta);profile['forearm_direction']=list(new);profile['raise_reference']=str(olddir);profile['elbow_raise_in_mount_m']=list(G.to_3x3().inverted()@delta);(d/'profile.json').write_text(json.dumps(profile,indent=2));report[key]=profile['elbow_raise_in_mount_m']
(O/'raise_parameters.json').write_text(json.dumps(report,indent=2));print('RAISED',report)
