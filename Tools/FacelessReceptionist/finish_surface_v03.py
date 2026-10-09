from pathlib import Path
p=Path(r'D:\FPS3D\FPSGAME\Tools\FacelessReceptionist\tailor_details_v03.py')
s=p.read_text(encoding='utf-8-sig')
anchor='# Straighten the sewn jacket hem without flattening the full lower panel.'
s=s.replace(anchor,'''# Relax voxel-cut cloth surfaces with a volume-preserving Taubin pass.
# Body geometry and skin weights stay intact; move both sides of each shell equally.
for garment in [jacket,bpy.data.objects['Receptionist_Shirt_Continuous']]:
 count=len(garment.data.vertices)//2
 source=np.array([v.co[:] for v in garment.data.vertices[:count]])
 edge_use={}
 for face in garment.data.polygons:
  ids=list(face.vertices)
  if not all(i<count for i in ids):continue
  for a,b in zip(ids,ids[1:]+ids[:1]):
   key=tuple(sorted((a,b)));edge_use[key]=edge_use.get(key,0)+1
 border_edges=[e for e,n in edge_use.items() if n==1]
 border={i for edge in border_edges for i in edge}
 a=[];b=[]
 for i,j in edge_use:
  if i not in border or (i,j) in border_edges:a.append(i);b.append(j)
  if j not in border or (i,j) in border_edges:a.append(j);b.append(i)
 a=np.array(a);b=np.array(b);degree=np.bincount(a,minlength=count)
 points=source.copy()
 for iteration in range(32):
  for factor in [.47,-.49]:
   sums=np.zeros_like(points);np.add.at(sums,a,points[b])
   means=np.divide(sums,degree[:,None],out=points.copy(),where=degree[:,None]>0)
   points+=(means-points)*factor
 delta=points-source
 limit=np.where(source[:,2]>1.37,.020,.012)
 lengths=np.linalg.norm(delta,axis=1)
 delta*=np.minimum(1,limit/np.maximum(lengths,1e-8))[:,None]
 for i,d in enumerate(delta):
  garment.data.vertices[i].co+=Vector(d);garment.data.vertices[i+count].co+=Vector(d)
 # A clean V-cut replaces the stair steps left by trimming dense source triangles.
 if garment==jacket:
  for i in border:
   v=garment.data.vertices[i];q=v.co.copy()
   if 1.161<q.z<1.526 and abs(q.x)<.125 and q.y<-.034:
    target=np.interp(q.z,[1.16,1.30,1.42,1.49,1.526],[.002,.038,.072,.080,.065])
    dx=math.copysign(target,q.x)-q.x
    v.co.x+=dx;garment.data.vertices[i+count].co.x+=dx
 garment.data.update()
 garment.data.normals_split_custom_set([(0,0,0)]*len(garment.data.loops))
''' + anchor)
start=s.index(" count=len(old.data.vertices)//2;rows=count//7")
end=s.index(" left=[Vector(verts[j*7])",start)
s=s[:start]+''' rows=48;verts=[];faces=[]
 for j,z in enumerate(np.linspace(1.162,1.526,rows)):
  x=float(np.interp(z,[1.16,1.30,1.42,1.49,1.526],[.002,.038,.072,.080,.065]))
  width=float(np.interp(z,[1.162,1.30,1.44,1.475,1.486,1.526],[.002,.027,.035,.028,.019,.026]))
  for k in range(7):
   f=k/6
   point,normal=facepoint(sign*(x+width*f),float(z),ease=.003+.0045*math.sin(math.pi*f))
   verts.append(tuple(point))
  if j<rows-1:
   for k in range(6):a=j*7+k;faces.append((a,a+1,a+8,a+7))
 # Smooth depth along each strip while keeping the designed cutline intact.
 for _ in range(10):
  oldverts=[Vector(v) for v in verts]
  for j in range(1,rows-1):
   for k in range(7):
    i=j*7+k;p=oldverts[i].copy()
    p.y=.5*p.y+.25*(oldverts[i-7].y+oldverts[i+7].y);verts[i]=tuple(p)
''' + s[end:]
start=s.index("hem_path=[jacket.data.vertices[i].co.copy() for i in hem]")
end=s.index("tube('Receptionist_Blazer_HemFinish'",start)
s=s[:start]+'''hem_vertices=[jacket.data.vertices[i].co.copy() for i in hem]
angles=np.array([math.atan2(p.x,-(p.y-.027)) for p in hem_vertices])
radii=np.array([math.hypot(p.x,p.y-.027) for p in hem_vertices])
order=np.argsort(angles);angles=angles[order];radii=radii[order]
theta=np.linspace(-math.pi,math.pi,192,endpoint=False)
radius=np.interp(theta,angles,radii,period=2*math.pi)
for _ in range(8):radius=(2*radius+np.roll(radius,1)+np.roll(radius,-1))/4
hem_path=[Vector((r*math.sin(t),.027-r*math.cos(t),hem_z+.001)) for r,t in zip(radius+.0018,theta)]
hem_path.append(hem_path[0].copy())
''' +s[end:]
p.write_text(s,encoding='utf-8')
