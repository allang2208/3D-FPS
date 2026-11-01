"""Keep M24's gun and native grip; solve a stock-clear right forearm corridor."""
from pathlib import Path
exec(compile((Path(__file__).parent/'library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
from mathutils.bvhtree import BVHTree
CI=C.inverted();idle,_=pose('idle',0)
gun=bpy.data.objects['M24_base'];gun.data.calc_loop_triangles();bv=BVHTree.FromPolygons([v.co for v in gun.data.vertices],[t.vertices[:] for t in gun.data.loop_triangles],all_triangles=True)
u,l,h='upperarm_r','lowerarm_r','hand_r';iu=idle[l].translation-idle[u].translation;il=idle[h].translation-idle[l].translation;A=iu.length;B=il.length
def frame(x,z):
 x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()
def twist(q,axis):
 if q.w<0:q=-q
 return 2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
def solve(old,offset,phi,write=False):
 S=old[u].translation+CI.to_3x3()@Vector(offset);H=old[h].translation;v=H-S;d=v.length
 if d>=A+B-.001 or d<=abs(A-B)+.001:return None
 axis=v/d;along=(A*A-B*B+d*d)/(2*d);center=S+axis*along;radius=math.sqrt(A*A-along*along)
 pole=old[l].translation-center;pole=(pole-axis*pole.dot(axis)).normalized();E=center+Quaternion(axis,math.radians(phi))@pole*radius
 U=E-S;L=H-E;N=U.cross(L).normalized();N0=iu.cross(il).normalized()
 uq=(frame(U,N)@frame(iu,N0).transposed()).to_quaternion()@idle[u].to_quaternion();lq=(frame(L,N)@frame(il,N0).transposed()).to_quaternion()@idle[l].to_quaternion()
 ax=idle[l].to_quaternion().inverted()@il.normalized();rel=(lq.inverted()@old[h].to_quaternion())@(idle[l].to_quaternion().inverted()@idle[h].to_quaternion()).inverted();roll=twist(rel,ax)
 desired=old[h].to_quaternion()@idle[h].to_quaternion().inverted()@il.normalized();bend=math.degrees(L.normalized().angle(desired))
 inv=rest['WPN_root']@old['WPN_root'].inverted();penetrations=[]
 for f,radius_cm in ((.10,.9),(.18,1.8),(.30,2.7),(.45,3.1),(.62,3.5),(.8,3.7)):
  p=inv@H.lerp(E,f);point,normal,_,dist=bv.find_nearest(p);penetrations.append(max(0,radius_cm-dist*100))
 ec,sc,hc=C@E,C@S,C@H
 up=max(0,ec.z-min(hc.z,sc.z)+3);inward=max(0,-ec.y-5)
 score=18*sum(p*p for p in penetrations)+.012*bend*bend+.025*max(0,bend-55)**2+.01*max(0,abs(math.degrees(roll))-105)**2+.035*up*up+.015*inward*inward+.18*Vector(offset).length_squared+.0015*phi*phi
 detail={'score':score,'bend':bend,'roll':math.degrees(roll),'capsule_penetration_cm':penetrations,'elbow_cm':list(ec),'shoulder_cm':list(sc),'offset_cm':offset,'phi':phi}
 if not write:return detail
 row=clone(old);Um=Matrix.LocRotScale(S,uq,Vector((1,1,1)));Lm=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
 row['clavicle_r'].translation+=CI.to_3x3()@Vector(offset)
 for n in names:
  if under(n,h):continue
  if under(n,l):row[n]=Lm@idle[l].inverted()@idle[n]
  elif under(n,u):row[n]=Um@idle[u].inverted()@idle[n]
 for j,w in ((1,1.),(2,.5)):
  n=f'lowerarm_twist_{j:02d}_r';lr=idle[l].inverted()@idle[n];row[n]=Lm@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*w)@lr.to_quaternion(),lr.to_scale())
 return row,detail
if __name__=='__main__':
 report=[]
 for t in (.10,.15,.20,.25,.325,.40,.46,.55,.68):
  old,_=pose('quick_melee',t);candidates=[]
  for off in ((0,0,0),(0,0,-4),(0,4,-4),(4,0,-4),(-4,0,-4),(0,6,-6),(4,4,-6),(0,0,-8)):
   for phi in range(-160,161,5):
    d=solve(old,off,phi)
    if d:candidates.append(d)
  best=min(candidates,key=lambda v:v['score']);base=solve(old,(0,0,0),0)
  report.append({'t':t,'original':base,'fit':best});print('RIGHT_FIT',t,'original',base,'fit',best,flush=True)
 (O/'right_fit.json').write_text(json.dumps(report,indent=2))
