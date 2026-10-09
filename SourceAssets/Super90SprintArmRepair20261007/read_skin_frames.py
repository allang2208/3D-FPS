from pathlib import Path
from mathutils import Vector
import math
p=Path('D:/FPS3D/FPSGAME/SourceAssets/Super90TacticalSprint20261007/author_sprint.py');s={'__file__':str(p)};exec(compile(p.read_text().split('profiles={f:')[0],str(p),'exec'),s)
r=s['rest'];u0=r['lowerarm_l'].translation-r['upperarm_l'].translation;f0=r['hand_l'].translation-r['lowerarm_l'].translation;h0=u0.cross(f0).normalized()
for family in ('base','vertical'):
 for t in (0,.2,.4,1):
  pose=s['pose'](t,None,family);u=pose['lowerarm_l'].translation-pose['upperarm_l'].translation;f=pose['hand_l'].translation-pose['lowerarm_l'].translation;h=u.cross(f).normalized()
  print('SKIN_FRAME',family,t,[(n,round(math.degrees(((pose[n].to_quaternion()@r[n].to_quaternion().inverted())@h0).angle(h)),2)) for n in ('upperarm_l','lowerarm_l','lowerarm_aux_l')],flush=True)
