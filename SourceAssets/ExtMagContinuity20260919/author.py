"""Local geometry continuity and tangent-aware UV seam crossfades."""
import bpy,bmesh,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).parent;S=O.parent;P=S/'ExtMagPattern20260919'
sys.path.insert(0,str(P));from export_tangents import export
params=json.loads((P/'parameters.json').read_text());report={}
for gun in ['AKM','M4','QBZ']:
 cfg=params[gun];cy,cz=cfg['center_yz'];R=cfg['radius_cm']/100;extension=cfg['extension_cm']/100;cut=cfg['cut_s_cm']/100;period=cfg['period_cm']/100
 bpy.ops.wm.open_mainfile(filepath=str(S/'ExtMagRebuild20260919'/(gun+'_ExtMag_Editable.blend')))
 factory=bpy.data.objects['Factory_'+gun];fp=[v.co.copy() for v in factory.data.vertices];xc=(min(v.x for v in fp)+max(v.x for v in fp))/2
 top=max(fp,key=lambda v:v.z);bottom=min(fp,key=lambda v:v.z);ttop=math.atan2(top.z-cz,top.y-cy);tb=math.atan2(bottom.z-cz,bottom.y-cy);direction=1 if math.atan2(math.sin(tb-ttop),math.cos(tb-ttop))>0 else -1
 def unroll(p):
  t=math.atan2(p.z-cz,p.y-cy);dt=math.atan2(math.sin(t-ttop),math.cos(t-ttop))
  return Vector((p.x-xc,math.hypot(p.y-cy,p.z-cz)-R,direction*dt*R))
 def roll(q):
  t=ttop+direction*q.z/R;r=R+q.y
  return Vector((q.x+xc,cy+r*math.cos(t),cz+r*math.sin(t)))
 if gun=='AKM':
  # Insert inside the straight run of the LONGITUDINAL ribs, not at their ends.
  cut=.140;period=.030;ob=factory.copy();ob.data=factory.data.copy();bpy.context.collection.objects.link(ob);ob.hide_set(False);ob.hide_render=False
  for other in list(bpy.context.scene.objects):
   if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
  mesh=ob.data;mesh.calc_loop_triangles();sourcepts=[unroll(v.co) for v in mesh.vertices];sourceuv=[x.uv.copy() for x in mesh.uv_layers.active.data];tris=list(mesh.loop_triangles)
  tree=BVHTree.FromPolygons(sourcepts,[tuple(t.vertices) for t in tris],all_triangles=True)
  source_triangles=[(tuple(t.vertices),tuple(t.loops)) for t in tris];source_normals=[n.vector.copy() for n in mesh.corner_normals]
  def uv_at(q):
   p,n,i,d=tree.find_nearest(q);t=tris[i]
   return barycentric_transform(p,*[sourcepts[v] for v in t.vertices],*[Vector((*sourceuv[l],0)) for l in t.loops]).xy
  bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active
  for v in bm.verts:v.co=unroll(v.co)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,cut),plane_no=(0,0,1),dist=1e-7)
  lower={f for f in bm.faces if f.calc_center_median().z>cut+1e-8}
  edges=[e for e in bm.edges if all(abs(v.co.z-cut)<2e-6 for v in e.verts) and any(f in lower for f in e.link_faces) and any(f not in lower for f in e.link_faces)]
  records=[]
  for e in edges:
   f=next(f for f in e.link_faces if f not in lower);l=next(l for l in f.loops if l.edge==e);records.append((l.vert,l.link_loop_next.vert))
  ring={v for a,b in records for v in (a,b)};endring={v:bm.verts.new(v.co+Vector((0,0,extension))) for v in ring}
  lowverts={v for f in lower for v in f.verts}
  for v in lowverts-ring:v.co.z+=extension
  for f in list(lower):
   if not any(v in ring for v in f.verts):continue
   verts=[endring.get(l.vert,l.vert) for l in f.loops];uvs=[l[uv].uv.copy() for l in f.loops];bm.faces.remove(f);nf=bm.faces.new(verts)
   for l,t in zip(nf.loops,uvs):l[uv].uv=t
  steps=40;rings=[{v:v for v in ring}]
  for k in range(1,steps):rings.append({v:bm.verts.new(v.co+Vector((0,0,extension*k/steps))) for v in ring})
  rings.append(endring)
  for k in range(steps):
   for a,b in records:
    f=bm.faces.new((rings[k][b],rings[k][a],rings[k+1][a],rings[k+1][b]));f.smooth=True
    # Reuse a middle rib surface, excluding its terminal bevel/wear band.
    mid_s=extension*(k+.5)/steps;repeat=math.floor(mid_s/period)
    for l in f.loops:
     q=l.vert.co.copy();q.z=cut-period+(q.z-cut-repeat*period);l[uv].uv=uv_at(q)
  for v in bm.verts:v.co=roll(v.co)
  bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
  # Carry the mouth completion from the latest accepted working revision.
  with bpy.data.libraries.load(str(S/'MagazineMouthFinish20260919/AKM_ExtMag_Mouth_Editable.blend'),link=False) as (a,b):b.objects=['SM_ExtMag_AKM40_Mouth']
  mouth=b.objects[0];bpy.context.collection.objects.link(mouth)
  mb=bmesh.new();mb.from_mesh(mouth.data);bmesh.ops.delete(mb,geom=[f for f in mb.faces if f.material_index!=1],context='FACES');mb.to_mesh(mouth.data);mb.free()
  bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);mouth.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.join()
  mesh=ob.data;bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bm.to_mesh(mesh);bm.free()
 else:
  bpy.ops.wm.open_mainfile(filepath=str(P/(gun+'_ExtMag_Editable.blend')));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');mesh=ob.data
 original_normals=[n.vector.copy() for n in mesh.corner_normals];original_coords=[v.co.copy() for v in mesh.vertices]
 if gun=='QBZ':
  # Remove only the longitudinal perimeter ripple of the repeated lower band.
  # The side panels/grooves and the rigid factory floorplate remain intact.
  qp=np.array([tuple(unroll(v.co)) for v in mesh.vertices]);es=np.array([tuple(e.vertices) for e in mesh.edges]);ea=qp[es[:,0]];eb=qp[es[:,1]]
  stations=np.linspace(cut,cut+extension,161);bounds=[]
  for s in stations:
   ok=(ea[:,2]-s)*(eb[:,2]-s)<0;aa=ea[ok];bb=eb[ok];t=(s-aa[:,2])/(bb[:,2]-aa[:,2]);hits=aa+(bb-aa)*t[:,None]
   bounds.append([float(hits[:,1].min()),float(hits[:,1].max())])
  bounds=np.array(bounds);target=(bounds[1]+bounds[-2])*.5
  for v,q in zip(mesh.vertices,qp):
   if not cut<q[2]<cut+extension:continue
   low,high=[float(np.interp(q[2],stations,bounds[:,i])) for i in (0,1)]
   ramp=min(1,(q[2]-cut)/.004,(cut+extension-q[2])/.004);ramp=ramp*ramp*(3-2*ramp)
   original_y=q[1]
   for i,edge in enumerate([low,high]):
    w=max(0,1-abs(original_y-edge)/.004);w=w*w*(3-2*w);q[1]+=(target[i]-edge)*w*ramp
   v.co=roll(Vector(q))
  report[gun]={'max_edge_adjustment_mm':max((v.co-p).length for v,p in zip(mesh.vertices,original_coords))*1000}
 # Rebuild only the lower shading from its actual final geometry. The prior
 # numerical deformation Jacobian produced inward-facing corner normals.
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
 # Geometry-based split normals keep sharp mechanical edges, and smooth ribs.
 for p in mesh.polygons:p.use_smooth=True
 mesh.set_sharp_from_angle(angle=math.radians(65));mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops));mesh.update()
 derived=[n.vector.copy() for n in mesh.corner_normals]
 if gun=='AKM':
  for p in mesh.polygons:
   if p.material_index!=0:continue
   for i in p.loop_indices:
    q=unroll(mesh.vertices[mesh.loops[i].vertex_index].co)
    if q.z>=cut-.004:continue
    point,n,idx,d=tree.find_nearest(q);vs,ls=source_triangles[idx]
    derived[i]=barycentric_transform(point,*[sourcepts[v] for v in vs],*[source_normals[l] for l in ls]).normalized()
 # Original upper geometry/normals remain unchanged (except AKM, whose source
 # topology was rebuilt and cannot reuse loop indices after the mouth join).
 if gun!='AKM' and len(original_normals)==len(derived):
  for p in mesh.polygons:
   for i in p.loop_indices:
    s=unroll(mesh.vertices[mesh.loops[i].vertex_index].co).z
    if s<cut-.004:derived[i]=original_normals[i]
 mesh.normals_split_custom_set(derived);mesh.update()
 if gun in ['M4','AKM']:
  # Refine only the texture transition strips so weights do not stretch across
  # large source triangles. Interpolate normals and UV0 through each cut.
  seams=[cut+k*period for k in range(round(extension/period)+1)];width=.004
  bm=bmesh.new();bm.from_mesh(mesh);nl=bm.loops.layers.float_vector.new('SavedNormal')
  for f in bm.faces:
   for l,i in zip(f.loops,mesh.polygons[f.index].loop_indices):l[nl]=mesh.corner_normals[i].vector
  for v in bm.verts:v.co=unroll(v.co)
  for seam in seams:
   for d in [-width,-.002,-.001,0,.001,.002,width]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,seam+d),plane_no=(0,0,1),dist=1e-7)
  for v in bm.verts:v.co=roll(v.co)
  bmesh.ops.triangulate(bm,faces=list(bm.faces));norm=[l[nl].normalized() for f in bm.faces for l in f.loops];bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(norm)
  mesh.calc_loop_triangles();mesh.calc_tangents(uvmap='UVMap');tris=list(mesh.loop_triangles);qpts=[unroll(v.co) for v in mesh.vertices];uv0=[l.uv.copy() for l in mesh.uv_layers[0].data]
  trees={}
  for seam in seams:
   for side in [-1,1]:
    ids=[i for i,t in enumerate(tris) if side*(sum(qpts[v].z for v in t.vertices)/3-seam)>1e-7 and abs(sum(qpts[v].z for v in t.vertices)/3-seam)<width*2 and t.material_index==0]
    trees[seam,side]=(BVHTree.FromPolygons(qpts,[tuple(tris[i].vertices) for i in ids],all_triangles=True),ids)
  alt=[];packs=[[] for _ in range(5)];identity=Matrix.Identity(3)
  loopface={i:p for p in mesh.polygons for i in p.loop_indices}
  def basis(li):
   l=mesh.loops[li];n=mesh.corner_normals[li].vector;t=l.tangent.copy()
   if t.length<.1:t=n.cross(Vector((0,1,0)))
   if t.length<.1:t=n.cross(Vector((1,0,0)))
   t.normalize();b=n.cross(t)*(l.bitangent_sign or 1)
   return Matrix((t,b,n)).transposed()
  bases=[basis(i) for i in range(len(mesh.loops))]
  for li,l in enumerate(mesh.loops):
   q=qpts[l.vertex_index];seam=min(seams,key=lambda s:abs(q.z-s));dist=abs(q.z-seam);weight=0.;value=uv0[li];rotation=identity
   if dist<width and loopface[li].material_index==0:
    face=loopface[li];fs=sum(qpts[v].z for v in face.vertices)/len(face.vertices);side=1 if fs>=seam else -1
    target=q.copy();target.z=seam-side*max(dist,.00002);tree,ids=trees[seam,-side];hit=tree.find_nearest(target)
    if hit[0] is not None:
     point,n,idx,d=hit;tri=tris[ids[idx]];coords=[qpts[v] for v in tri.vertices]
     weights=barycentric_transform(point,*coords,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
     value=sum((uv0[i]*w for i,w in zip(tri.loops,weights)),Vector((0,0)))
     other=sum((bases[i]*w for i,w in zip(tri.loops,weights)),Matrix(((0,0,0),(0,0,0),(0,0,0))))
     turn=Matrix.Rotation(direction*(q.z-point.z)/R,3,'X');rotation=bases[li].transposed()@turn@other
     x=dist/width;weight=.5*(1-x*x*(3-2*x))
   alt.append(tuple(value));v=[weight]+[rotation[i][j] for i in range(3) for j in range(3)]
   # UE FBX import flips V on every UV channel, including packed data.
   # Pre-encode the matrix components so its imported numeric values survive.
   for k in range(5):packs[k].append((v[2*k],1-v[2*k+1]))
  for name,values in [('SeamUV',alt)]+[('SeamBasis'+str(i),x) for i,x in enumerate(packs)]:
   layer=mesh.uv_layers.new(name=name)
   for l,v in zip(layer.data,values):l.uv=v
  mesh.uv_layers.active_index=0;mesh.uv_layers[0].active_render=True
  report.setdefault(gun,{}).update({'seams_m':seams,'blend_halfwidth_mm':width*1000,'normal_blend':'alternate tangent frame rotated into UV0 frame; matrix in UV2-6'})
 ob.name='SM_ExtMag_'+gun+'40_Continuous';bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 (O/'FBX').mkdir(exist_ok=True);export(mesh,O/'FBX'/(ob.name+'.fbx'));bpy.ops.wm.save_as_mainfile(filepath=str(O/(gun+'_ExtMag_Continuous_Editable.blend')))
 report.setdefault(gun,{}).update({'vertices':len(mesh.vertices),'triangles':len(mesh.polygons),'source':'latest mouth + factory longitudinal rib sweep' if gun=='AKM' else str(P/(gun+'_ExtMag_Editable.blend'))})
 (O/'authoring.json').write_text(json.dumps(report,indent=2));print('AUTHORED_CONTINUITY',gun,flush=True)
