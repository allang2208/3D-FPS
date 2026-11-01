from pathlib import Path
import math,json
P=Path(__file__).resolve().parent
source=(P/'author_motion.py').read_text(encoding='utf-8')
exec(compile(source.split('\nbest=None')[0],str(P/'author_motion.py'),'exec'))
neutral_local=(grip.to_quaternion()@rest['hand_r'].to_quaternion().inverted())@spec['r']['b']
print('NEUTRAL_VS_SHAFT',list(neutral_local),flush=True)
rows=[]
for xyz in [(.30,.34,-.14),(.34,.32,-.16),(.36,.30,-.16),(.32,.36,-.18),(.34,.36,-.12)]:
 for sd in [(.1,.35,.932),(.12,.50,.857),(.1,.6,.794)]:
  axis=Vector(sd).normalized();qbase=(q0@Vector((0,0,1))).rotation_difference(axis)@q0;best=None
  for roll_deg in range(-180,181,8):
   q=Quaternion(axis,math.radians(roll_deg))@qbase;w=Matrix.LocRotScale(Vector(xyz)-q@grip.translation,q,Vector((1,1,1)));h=w@grip
   for sw in range(-180,181,4):
    e,ua,fa,du,df,tw,bn=elbow_frame('r',shoulder_top['r'],h,math.radians(sw))
    cost=10*bn*bn+1.2*tw*tw+100*max(0,.18-e.x)**2+40*max(0,e.z+.08)**2
    if best is None or cost<best[0]:best=(cost,dict(hand=xyz,shaft=sd,roll=roll_deg,swivel=sw,bend=math.degrees(bn),twist=math.degrees(tw),elbow=list(e),head=list(w@Vector((0,0,.916)))))
  rows.append(best[1])
rows.sort(key=lambda x:x['bend']+abs(x['twist'])*.35)
(P/'target-options.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows[:5]),flush=True)
