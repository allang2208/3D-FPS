from pathlib import Path
exec(compile((Path(__file__).parent/'audit_bolt.py').read_text().split('out=[];folder=')[0],'audit','exec'))
def adjust(row,phi,offset=(0,0,0)):
 old=clone(row);out=clone(row);u,l,h='upperarm_l','lowerarm_l','hand_l'
 S=old[u].translation+C.inverted().to_3x3()@Vector(offset);H=old[h].translation
 A=(rest[l].translation-rest[u].translation).length;B=(rest[h].translation-rest[l].translation).length
 axis=H-S;d=axis.length
 if d>A+B-.0001:raise ValueError('Unreachable shoulder')
 axis.normalize();pole=old[l].translation-S;pole-=axis*pole.dot(axis);pole.normalize();pole=Quaternion(axis,math.radians(phi))@pole
 along=(A*A-B*B+d*d)/(2*d);E=S+axis*along+pole*math.sqrt(max(0,A*A-along*along))
 def frame(x,z):
  x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()
 before_u=old[l].translation-old[u].translation;before_l=old[h].translation-old[l].translation;before_n=before_u.cross(before_l).normalized();after_n=(E-S).cross(H-E).normalized()
 UQ=(frame(E-S,after_n)@frame(before_u,before_n).transposed()).to_quaternion()@old[u].to_quaternion()
 LQ=(frame(H-E,after_n)@frame(before_l,before_n).transposed()).to_quaternion()@old[l].to_quaternion()
 U=Matrix.LocRotScale(S,UQ,Vector((1,1,1)));L=Matrix.LocRotScale(E,LQ,Vector((1,1,1)))
 for n in names:
  if under(n,h):continue
  if under(n,l):out[n]=L@old[l].inverted()@old[n]
  elif under(n,u):out[n]=U@old[u].inverted()@old[n]
 out['clavicle_l']=U@old[u].inverted()@old['clavicle_l']
 axis=rest[l].to_quaternion().inverted()@(rest[h].translation-rest[l].translation).normalized()
 relative=LQ.inverted()@old[h].to_quaternion()@(rest[l].to_quaternion().inverted()@rest[h].to_quaternion()).inverted()
 if relative.w<0:relative=-relative
 roll=2*math.atan2(Vector((relative.x,relative.y,relative.z)).dot(axis),relative.w)
 for i,fraction in ((1,1),(2,.5)):
  n=f'lowerarm_twist_{i:02d}_l';lr=local_rest[n]
  out[n]=L@Matrix.LocRotScale(lr.translation,Quaternion(axis,roll*fraction)@lr.to_quaternion(),Vector((1,1,1)))
 return out
folder=O/'candidates';folder.mkdir(exist_ok=True);s.render.resolution_x=960;s.render.resolution_y=540
rows=[]
for phi,offset in ((40,(3,0,-8)),(60,(3,0,-8)),(80,(3,0,-8)),(40,(5,-2,-8)),(60,(5,-2,-8)),(80,(5,-2,-8))):
 row=adjust(component(local_pose('fire',23/30)),phi,offset)
 rows.append({'phi':phi,'offset':offset,**stats(row)});render(row,folder/f'root_{phi:+03}_{offset[0]}_{offset[2]}.png')
(O/'root_candidates.json').write_text(json.dumps(rows,indent=2));print('ROOT_CANDIDATES',json.dumps(rows),flush=True)
