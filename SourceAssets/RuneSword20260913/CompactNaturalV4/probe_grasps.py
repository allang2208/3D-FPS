import bpy,json,sys,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent;sys.path.insert(0,str(P))
from arm_solver import ArmSolver
bpy.ops.wm.open_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
r=bpy.data.objects['SK_RuneSword_Rig'];s=bpy.context.scene
def pose(clip,f):
 a=bpy.data.actions['A_RuneSword_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(f)
 return r.pose.bones['WPN_root'].matrix.copy()
sf=pose('Idle',0);ready=json.loads((P/'authoring.json').read_text())['ready_grasp_degrees']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
grasp={side:Matrix.Rotation(-math.radians(ready[side]),4,'Z')@Matrix.Translation((0,0,-depth))@sf.inverted()@r.pose.bones['hand_'+side].matrix for side,depth in [('l',-.172),('r',-.072)]}
solver=ArmSolver(rest,grasp,{})
for clip,f,side in [('Idle',0,'l'),('Idle',0,'r'),('Slash1',197,'r'),('Slash2',178,'l')]:
 sf=pose(clip,f);path=json.loads((P/('grasp_path_'+clip+'.json')).read_text())[side]
 vals=[]
 for a in range(-360,361):
  H=solver.hand(side,sf,math.radians(a));c,A,E,T,*_=solver.support(side,H)
  fd=(T-E).normalized();old=(rest['hand_'+side].translation-rest['lowerarm_'+side].translation).normalized()
  hd=H.to_quaternion()@rest['hand_'+side].to_quaternion().inverted()@old
  vals.append((c,a,math.degrees(fd.angle(hd))))
 print('GRASP',clip,f,side,'ready',ready[side],'chosen',math.degrees(path[f]),'best',min(vals),flush=True)
