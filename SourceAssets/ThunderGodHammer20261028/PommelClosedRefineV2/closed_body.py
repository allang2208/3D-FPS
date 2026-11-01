# One sewn structural surface, including every recess, reveal and end cap.
# All new geometry shares vertices before normals/bevel; no isolated single-sided patches.
zcut=-.02465
verts=[];faces=[];mats=[]
def face(points,mat=0):
 idx=len(verts);verts.extend(points);faces.append(tuple(range(idx,idx+len(points))));mats.append(mat)
if KIND=='LeiXi':
 zt=-.032;zc=-.0465;zb=-.0618
 levels=sorted(set([z for z,r in profile if z<=-.0262]+[zt,zc,zb,-.0262]))
 def section(z):
  w=max(0,.64*((z-zb)/(zc-zb) if z<zc else (zt-z)/(zt-zc))) if zb<=z<=zt else 0
  d=.00125*min(1,w/.06)
  return [(-1,0),(-w,0),(-w,d),(0,d),(w,d),(w,0),(1,0)]
else:
 levels=sorted(set([z for z,r in profile if z<=-.0262]+[-.065,-.0644,-.0406,-.040,-.0262]))
 def section(z):
  d=.0008*min(1,max(0,(z+.065)/.0006),max(0,(-.040-z)/.0006))
  return [(-1,0),(-.84,0),(-.84,d),(0,d),(.84,d),(.84,0),(1,0)]
for i in range(8):
 for za,zb_ in zip(levels[:-1],levels[1:]):
  sa=section(za);sb=section(zb_)
  if i%2:sa=[(s,0) for s,d in sa];sb=[(s,0) for s,d in sb]
  for k in range(6):
   pts=[facepoint(i,sa[k][0],za,sa[k][1]),facepoint(i,sa[k+1][0],za,sa[k+1][1]),facepoint(i,sb[k+1][0],zb_,sb[k+1][1]),facepoint(i,sb[k][0],zb_,sb[k][1])]
   mat=2 if i%2==0 and k in [2,3] and KIND=='LeiXi' else 1 if i%2==0 and k in [1,4] else 0
   face(pts,mat)
body=make('Continuous structural body with closed relief wells',verts,faces,steel)
body.data.materials.append(bronze);body.data.materials.append(coremat)
# Assign by geometric face position after degenerate strips have been removed.
for p in body.data.polygons:
 center=p.center;a=math.atan2(center.y-CY,center.x-CX);i=int(round(a/(math.pi/4)))%8
 normal=Vector((math.cos(i*math.pi/4),math.sin(i*math.pi/4),0));depth=radius(center.z)*math.cos(math.pi/8)-(center-Vector((CX,CY,center.z))).dot(normal)
 if KIND=='LeiXi' and i%2==0 and depth>.00065:
  p.material_index=2
  for li in p.loop_indices:
   co=body.data.vertices[body.data.loops[li].vertex_index].co;tangent=Vector((-normal.y,normal.x,0));s=(co-Vector((CX,CY,co.z))).dot(tangent)/(radius(co.z)*math.sin(math.pi/8))
   body.data.uv_layers.active.data[li].uv=(.5+s/1.28,(co.z+ .0618)/(.0618-.032))
# The cut ring comes from real native boundary topology, not samples extrapolated by height.
bm=bmesh.new();bm.from_mesh(src);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
cut_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-zcut)<2e-7 for v in e.verts)]
cut_verts=set(v for e in cut_edges for v in e.verts)
native_ring=sorted([v.co.copy() for v in cut_verts],key=lambda p:math.atan2(p.y-CY,p.x-CX)%(math.pi*2));bm.free()
if len(native_ring)<8:raise RuntimeError('Native interface boundary unavailable')
bm=bmesh.new();bm.from_mesh(body.data)
top_verts=set(v for e in bm.edges if e.is_boundary and all(abs(v.co.z+.0262)<2e-7 for v in e.verts) for v in e.verts)
top=sorted(top_verts,key=lambda v:math.atan2(v.co.y-CY,v.co.x-CX)%(math.pi*2))
upper=[bm.verts.new(p) for p in native_ring]
def angle(v):return math.atan2(v.co.y-CY,v.co.x-CX)%(math.pi*2)
# Angular zipper joins arbitrary native triangle cuts to the regular forged profile.
ia=ib=0;na=len(upper);nb=len(top)
while ia<na or ib<nb:
 a=upper[ia%na];b=top[ib%nb]
 an=angle(upper[(ia+1)%na])+(2*math.pi if ia+1>=na else 0) if ia<na else float('inf')
 bn=angle(top[(ib+1)%nb])+(2*math.pi if ib+1>=nb else 0) if ib<nb else float('inf')
 if an<bn:bm.faces.new((a,b,upper[(ia+1)%na]));ia+=1
 else:bm.faces.new((a,b,top[(ib+1)%nb]));ib+=1
# Solid terminal cap shares the real bottom perimeter, including collinear panel vertices.
bottom=set(v for e in bm.edges if e.is_boundary and all(abs(v.co.z-levels[0])<2e-7 for v in e.verts) for v in e.verts)
bottom=sorted(bottom,key=angle);center=bm.verts.new((CX,CY,levels[0]))
for j,v in enumerate(bottom):bm.faces.new((center,bottom[(j+1)%len(bottom)],v))
uv=bm.loops.layers.uv.active
for f in bm.faces:
 if all(tuple(l[uv].uv)==(0.,0.) for l in f.loops):
  for l in f.loops:l[uv].uv=(l.vert.co.x*24,l.vert.co.y*24)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if bm.calc_volume(signed=True)<0:bmesh.ops.reverse_faces(bm,faces=list(bm.faces))
bm.to_mesh(body.data);bm.free();finish_bevel(body,.00016)
# Unequal native cut triangles must not create a scalloped highlight in the neck.
# Its shading follows the actual circular-to-octagonal ruled transition.
neck_normals=[tuple(n.vector) for n in body.data.corner_normals]
mean_cut_radius=sum(math.hypot(p.x-CX,p.y-CY) for p in native_ring)/len(native_ring)
for p in body.data.polygons:
 if all(-.02621<=body.data.vertices[body.data.loops[li].vertex_index].co.z<=zcut+1e-6 for li in p.loop_indices):
  for li in p.loop_indices:
   co=body.data.vertices[body.data.loops[li].vertex_index].co;a=math.atan2(co.y-CY,co.x-CX);face_angle=round(a/(math.pi/4))*math.pi/4
   bottom_radius=radius(-.0262)*math.cos(math.pi/8)/math.cos(a-face_angle);slope=(mean_cut_radius-bottom_radius)/(.0262-.02465)
   blend=max(0,min(1,(co.z+.0262)/(.0262-.02465)))
   outward=(Vector((math.cos(face_angle),math.sin(face_angle),0))*(1-blend)+Vector((math.cos(a),math.sin(a),0))*blend).normalized()
   neck_normals[li]=tuple(Vector((outward.x,outward.y,-slope)).normalized())
body.data.normals_split_custom_set(neck_normals)
