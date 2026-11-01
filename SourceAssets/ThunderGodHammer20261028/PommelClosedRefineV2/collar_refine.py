# Replace only the coarse scanned braid strip; retain the native mounting socket and both lips.
bm=bmesh.new();bm.from_mesh(src);nl=bm.loops.layers.float_vector.new('PreservedCollarNormal');tag=bm.faces.layers.int.new('NewBand')
for f,p in zip(bm.faces,src.polygons):
 for l,li in zip(f.loops,p.loop_indices):l[nl]=src.corner_normals[li].vector
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
upper_z=-.0105;lower_z=-.0175
for z in [upper_z,lower_z]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,z),plane_no=(0,0,1),dist=1e-8,clear_inner=False,clear_outer=False)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if lower_z+1e-8<f.calc_center_median().z<upper_z-1e-8],context='FACES')
def az(v):return math.atan2(v.co.y-CY,v.co.x-CX)%(math.pi*2)
def cut_ring(z):
 return sorted(set(v for e in bm.edges if e.is_boundary and all(abs(v.co.z-z)<1e-7 for v in e.verts) for v in e.verts),key=az)
top=cut_ring(upper_z);bottom=cut_ring(lower_z)
if len(top)<8 or len(bottom)<8:raise RuntimeError('Cannot locate collar braid boundaries')
src.materials.append(steel);steel_index=len(src.materials)-1
def join_rings(a,b):
 ia=ib=0;na=len(a);nb=len(b)
 while ia<na or ib<nb:
  aa=az(a[(ia+1)%na])+(2*math.pi if ia+1>=na else 0) if ia<na else float('inf')
  ab=az(b[(ib+1)%nb])+(2*math.pi if ib+1>=nb else 0) if ib<nb else float('inf')
  if aa<ab:f=bm.faces.new((a[ia%na],b[ib%nb],a[(ia+1)%na]));ia+=1
  else:f=bm.faces.new((a[ia%na],b[ib%nb],b[(ib+1)%nb]));ib+=1
  f[tag]=1;f.material_index=steel_index
band_radius=.01755
loops=[]
for z in [upper_z-.00025,lower_z+.00025]:
 loops.append([bm.verts.new((CX+band_radius*math.cos(a*2*math.pi/192),CY+band_radius*math.sin(a*2*math.pi/192),z)) for a in range(192)])
join_rings(top,loops[0]);join_rings(loops[0],loops[1]);join_rings(loops[1],bottom)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));uv=bm.loops.layers.uv.active
for f in bm.faces:
 if not f[tag]:continue
 for l in f.loops:
  co=l.vert.co;a=math.atan2(co.y-CY,co.x-CX)
  l[uv].uv=(a/(math.pi*2),co.z*30)
  l[nl]=Vector((math.cos(a),math.sin(a),0)) if abs(f.normal.z)<.25 else f.normal
bmesh.ops.triangulate(bm,faces=list(bm.faces));normals=[tuple(l[nl].normalized()) for f in bm.faces for l in f.loops]
bm.to_mesh(src);bm.free()
for p in src.polygons:p.use_smooth=True
src.normals_split_custom_set(normals)
# Closed flat silver braids over a closed steel bed; they never cover an opening.
for strand in range(2):
 points=[];n=480;verts=[];faces=[]
 for j in range(n):
  a=j*2*math.pi/n;phase=a*12+strand*math.pi
  r=band_radius+.00026+.00013*math.cos(phase*2+strand*math.pi);z=-.014+.00195*math.sin(phase)
  points.append(Vector((CX+r*math.cos(a),CY+r*math.sin(a),z)))
 for j,p in enumerate(points):
  a=j*2*math.pi/n;normal=Vector((math.cos(a),math.sin(a),0));tangent=(points[(j+1)%n]-points[(j-1)%n]).normalized();side=normal.cross(tangent).normalized()*.00058
  verts.extend([p-side+normal*.00012,p+side+normal*.00012,p+side-normal*.00012,p-side-normal*.00012])
 for j in range(n):
  for k in range(4):faces.append((j*4+k,j*4+(k+1)%4,((j+1)%n)*4+(k+1)%4,((j+1)%n)*4+k))
 make('Precision interwoven collar silver band',verts,faces,silver,.000045)
