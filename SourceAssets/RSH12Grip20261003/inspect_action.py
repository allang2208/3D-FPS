"""Inspect the held/fire/cock contact and framing requested by the user, offline."""
import bpy,json,math,sys
from pathlib import Path
O=Path(__file__).parent;sys.path.insert(0,str(O));from pose_geometry import *
metadata=json.loads((B/'Single/authoring.json').read_text());path=SA/'single/A_RSH12_aim_fire_Editable.blend';results=[]
for t in (0,.06,.30,.45,.60,.85,1.):
 bpy.ops.wm.open_mainfile(filepath=str(path));rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');rig.data.pose_position='POSE';scene=bpy.context.scene
 scene.frame_set(0);bpy.context.view_layer.update();reference={b.name:b.matrix.copy() for b in rig.pose.bones}
 scene.frame_set(round(t*120));bpy.context.view_layer.update();p={b.name:b.matrix.copy() for b in rig.pose.bones}
 if t<.14:aim=1.
 elif t<.30:aim=1-(lambda x:x*x*(3-2*x))((t-.14)/.16)
 elif t<.78:aim=0.
 else:aim=(lambda x:x*x*(3-2*x))((t-.78)/.22)
 frame=render(rig,p,metadata,'cock_'+str(round(t*1000)).zfill(4),'hip',reference,aim)
 results.append(dict(time=t,aim_weight=aim,vertical_fov=75-20*aim))
(O/'action_inspection.json').write_text(json.dumps(results,indent=2))
