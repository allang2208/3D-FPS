from pathlib import Path
p=Path(__file__).with_name('build_drop_reload.py');s=p.read_text()
s=s.replace('from mathutils import Matrix,Vector,Quaternion','from mathutils import Matrix,Vector,Quaternion,Euler')
s=s.replace('def update():bpy.context.view_layer.update()', '''def curve(keys,t):
 if t<=keys[0][0]:return keys[0][1].copy()
 if t>=keys[-1][0]:return keys[-1][1].copy()
 for i,((a,A),(b,B)) in enumerate(zip(keys,keys[1:])):
  if t<=b:
   u=(t-a)/(b-a);dt=b-a
   m0=Vector((0,0,0)) if i==0 else (B.translation-keys[i-1][1].translation)/(b-keys[i-1][0])
   m1=Vector((0,0,0)) if i+2==len(keys) else (keys[i+2][1].translation-A.translation)/(keys[i+2][0]-a)
   pos=A.translation*(2*u**3-3*u*u+1)+m0*dt*(u**3-2*u*u+u)+B.translation*(-2*u**3+3*u*u)+m1*dt*(u**3-u*u)
   return Matrix.LocRotScale(pos,A.to_quaternion().slerp(B.to_quaternion(),smooth(u)),Vector((1,1,1)))

def update():bpy.context.view_layer.update()''')
start=s.index(' r.animation_data.action=None;home=');end=s.index(' poses=[];rows=[];',start)
s=s[:start]+''' r.animation_data.action=None;reference=raw;W0=raw[0]['P']['WPN_root'];home=raw[0]['P']['hand_l'];hold=release+4
 # Author small, nonperiodic weight transfers rather than freezing the weapon.
 events=[(0,(0,0,0)),(hold,(0,0,0)),(hold+8,(1.0,-.65,-.9)),(lock,(-.7,.7,1.1)),(lock+17,(.8,-.8,-.7)),(76 if clip=='reload' else 65,(-.45,.5,.6)),(92 if clip=='reload' else 90,(.5,-.45,-.35)),(end-14,(-.25,.35,.25)),(end,(0,0,0))]
 events.sort(key=lambda x:x[0]);swaykeys=[(t,Matrix.Translation(Vector(v))) for t,v in events]
 def weapon(t,old):
  e=curve(swaykeys,t).translation
  early=smooth(t/max(1,release-3));later=smooth((t-hold)/18);finish=smooth((end-t)/18)
  # A five-degree lift keeps the initial grip. The larger reload cant follows only after release.
  initial=Quaternion(Vector((1,0,0)),math.radians(5*early))
  relative=old.to_quaternion()@W0.to_quaternion().inverted();main=Quaternion().slerp(relative,.50)
  q=initial.slerp(main,later);q=Quaternion().slerp(q,finish)
  q=Euler(tuple(math.radians(v) for v in e),'XYZ').to_quaternion()@q
  pos=W0.translation+Vector((0,0,.012*early))*finish
  pos+=((old.translation-W0.translation)*.40-Vector((0,0,.012)))*later*finish
  pos+=Vector((e.z*.002,e.y*.0015,e.x*.002))
  return Matrix.LocRotScale(pos,q@W0.to_quaternion(),Vector((1,1,1)))
 gun=[weapon(k/2,d['P']['WPN_root']) for k,d in enumerate(raw)]
 hand_hold=gun[hold*2]@W0.inverted()@home
 grasp=gun[lock*2]@raw[lock*2]['P']['WPN_root'].inverted()@raw[lock*2]['P']['hand_l']
 away=mix(hand_hold,grasp,.62);away.translation=hand_hold.translation+Vector((-.10,-.075,-.24))
 fetch=grasp.copy();fetch.translation+=Vector((-.025,-.008,-.035))
 handkeys=[(hold,hand_hold),(hold+(pickup-hold)*.60,away),(pickup,fetch),(lock,grasp)]
 raw=[]
 for k,src in enumerate(reference):
  for n,m in src['B'].items():r.pose.bones[n].matrix_basis=m
  update();delta=gun[k]@src['P']['WPN_root'].inverted()
  for b in r.pose.bones:
   if b.name.startswith('WPN_'):b.matrix=delta@src['P'][b.name];update()
  # Both palms retain their exact grip relative to the weapon until the free-hand phase.
  for side in ['l','r']:r.pose.bones['hand_'+side].matrix=delta@src['P']['hand_'+side];update()
  raw.append({'P':{b.name:b.matrix.copy() for b in r.pose.bones},'B':{b.name:b.matrix_basis.copy() for b in r.pose.bones}})
''' + s[end:]
s=s.replace("goal=track(handkeys,t);r.pose.bones['hand_l'].matrix=goal;update()", "goal=gun[k]@W0.inverted()@home if t<=hold else curve(handkeys,t);r.pose.bones['hand_l'].matrix=goal;update()")
s=s.replace("[(0,B),(8,B),(release+3,openB),(pickup,openB),(lock,C)]", "[(0,B),(hold,B),(hold+5,openB),(pickup,openB),(lock,C)]")
# Magazine was already transformed with the full weapon hierarchy in the prepass.
s=s.replace("if t<=release:r.pose.bones['WPN_SOCKET_Magazine'].matrix=src['P']['WPN_root']@raw[0]['P']['WPN_root'].inverted()@raw[0]['P']['WPN_SOCKET_Magazine'];update()", "if t<=release:r.pose.bones['WPN_SOCKET_Magazine'].matrix=gun[k]@W0.inverted()@reference[0]['P']['WPN_SOCKET_Magazine'];update()")
s=s.replace("'release_frame':release,'pickup_frame':pickup", "'release_frame':release,'support_release_frame':hold,'pickup_frame':pickup")
p.write_text(s)
