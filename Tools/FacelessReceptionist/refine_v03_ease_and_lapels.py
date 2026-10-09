from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist')
f=p/'fit_motion_v03.py';s=f.read_text(encoding='utf-8')
s=s.replace("else:n=rest_bvh.find_nearest(Vector(p))[1]","""else:
   n=o.data.vertices[len(normals)].normal.copy()
   reference=rest_bvh.find_nearest(Vector(p))[1]
   if n.dot(reference)<0:n=-n
   n.normalize()""")
s=s.replace("for i,pad in enumerate(padding):","""# Filter ease over physical cloth regions, rather than only a few dense edges.
 raw_points=data['points'];keys=[]
 for p in raw_points:
  if 'Skirt' in o.name:
   part=0;u=(p[2]-.48)/.65;theta=math.atan2(p[0],-(p[1]-.027))
  else:
   side='l' if p[0]>=0 else 'r'
   a,b,c=[rest_world@rig.data.bones[n+'_'+side].head_local for n in ['upperarm','lowerarm','hand']]
   if abs(p[0])>.225:
    best=None;vp=Vector(p)
    for seg,(q,r) in enumerate([(a,b),(b,c)]):
     t=max(0,min(1,(vp-q).dot(r-q)/(r-q).length_squared));center=q.lerp(r,t)
     if best is None or (vp-center).length<best[0]:best=((vp-center).length,center,(seg+t)/2,(r-q).normalized())
    _,center,u,tangent=best
    axis=Vector((0,1,0));axis=(axis-tangent*axis.dot(tangent)).normalized();cross=tangent.cross(axis)
    d=vp-center;theta=math.atan2(d.dot(cross),d.dot(axis));part=1 if side=='l' else 2
   else:
    part=0;u=(p[2]-.97)/.62;theta=math.atan2(p[0],-(p[1]-.015))
  keys.append((part,max(0,min(39,int(u*39))),int((theta+math.pi)/(2*math.pi)*64)%64))
 grids=np.zeros((3,40,64));counts=np.zeros_like(grids)
 for k,pad in zip(keys,padding):grids[k]+=pad;counts[k]+=1
 grids=np.divide(grids,counts,out=np.zeros_like(grids),where=counts>0)
 mask=(counts>0).astype(float)
 # Gaussian-like periodic angular diffusion spreads the same ease continuously.
 for _ in range(35):
  numerator=grids*mask*2;denominator=mask*2
  for axis in [1,2]:
   for step in [-1,1]:
    numerator+=np.roll(grids*mask,step,axis);denominator+=np.roll(mask,step,axis)
  grids=np.divide(numerator,denominator,out=grids.copy(),where=denominator>0)
  mask=np.clip(denominator,0,1)
 padding=np.array([grids[k] for k in keys])
 for i,pad in enumerate(padding):""")
s=s.replace("d=Vector(data['normals'][i]*pad)","""if 'Blazer' in o.name and data['points'][i,2]>1.38:pad=min(pad,.006)
  d=Vector(data['normals'][i]*pad)""")
f.write_text(s,encoding='utf-8')
f=p/'tailor_details_v03.py';s=f.read_text(encoding='utf-8')
s=s.replace("if h[0] is None:\n  h=tree.find_nearest(Vector((x,.13 if back else -.13,z)))\n return h[0]+h[1]*ease,h[1]","""if h[0] is None or (h[1].y<.03 if back else h[1].y>-.03):
  h=tree.find_nearest(Vector((x,.24 if back else -.24,z)))
 # Keep the authored cutline coordinates even when the ray passed the V opening.
 return Vector((x,h[0].y+(ease if back else -ease),z)),h[1]""")
s=s.replace("faces=[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]","faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]")
f.write_text(s,encoding='utf-8')
