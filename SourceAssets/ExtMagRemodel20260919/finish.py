import bpy,bmesh,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).parent;S=O.parent;P=S/'ExtMagPattern20260919'
sys.path.insert(0,str(P));from export_tangents import export
report={}
for gun in ['M4','QBZ']:
 cfg=json.loads(((O if gun=='M4' else P)/'parameters.json').read_text())[gun]
 cy,cz=cfg['center_yz'];R=cfg['radius_cm']/100;extension=cfg['extension_cm']/100;cut=cfg['cut_s_cm']/100;period=cfg['period_cm']/100
 file=O/'M4_ExtMag_Remodel_Editable.blend' if gun=='M4' else S/'ExtMagContinuity20260919/QBZ_ExtMag_Continuous_Editable.blend'
 bpy.ops.wm.open_mainfile(filepath=str(file));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');mesh=ob.data
 # Fixed factory feed reference, independent of the already extended bottom.
 with bpy.data.libraries.load(str(S/'ExtMagRebuild20260919'/(gun+'_ExtMag_Editable.blend')),link=False) as (a,b):b.objects=['Factory_'+gun]
 factory=b.objects[0];fp=[v.co.copy() for v in factory.data.vertices];xc=(min(v.x for v in fp)+max(v.x for v in fp))/2
 top=max(fp,key=lambda v:v.z);bottom=min(fp,key=lambda v:v.z);ttop=math.atan2(top.z-cz,top.y-cy);tb=math.atan2(bottom.z-cz,bottom.y-cy);direction=1 if math.atan2(math.sin(tb-ttop),math.cos(tb-ttop))>0 else -1
 def unroll(p):
  t=math.atan2(p.z-cz,p.y-cy);dt=math.atan2(math.sin(t-ttop),math.cos(t-ttop))
  return Vector((p.x-xc,math.hypot(p.y-cy,p.z-cz)-R,direction*dt*R))
 def roll(q):
  t=ttop+direction*q.z/R;r=R+q.y
  return Vector((q.x+xc,cy+r*math.cos(t),cz+r*math.sin(t)))
 oldnorm=[n.vector.copy() for n in mesh.corner_normals];oldpos=[v.co.copy() for v in mesh.vertices]
 if gun=='QBZ':
  # Replace the wavy rim by a C1 curve connected to the unchanged upper and
  # lower shell. The old fixed-radius strip left hard endpoints at the plate.
  qp=np.array([tuple(unroll(v.co)) for v in mesh.vertices]);es=np.array([tuple(e.vertices) for e in mesh.edges]);a=qp[es[:,0]];b=qp[es[:,1]]
  begin=cut-.010;end=cut+extension+.006
  def bounds(s):
   ok=(a[:,2]-s)*(b[:,2]-s)<0;aa=a[ok];bb=b[ok];hits=aa+(bb-aa)*((s-aa[:,2])/(bb[:,2]-aa[:,2]))[:,None]
   return np.array([hits[:,1].min(),hits[:,1].max()])
  stations=np.linspace(begin,end,401);current=np.array([bounds(s) for s in stations]);first=current[0];last=current[-1]
  d0=(bounds(begin+.0005)-bounds(begin-.0005))/.001;d1=(bounds(end+.0005)-bounds(end-.0005))/.001
  # Robust clamp excludes a transverse ridge/plate lip from longitudinal slope.
  d0=np.clip(d0,-.12,.12);d1=np.clip(d1,-.12,.12);length=end-begin
  for v,q in zip(mesh.vertices,qp):
   if not begin<q[2]<end:continue
   t=(q[2]-begin)/length;t2=t*t;t3=t2*t
   target=(2*t3-3*t2+1)*first+(t3-2*t2+t)*length*d0+(-2*t3+3*t2)*last+(t3-t2)*length*d1
   lo,hi=[np.interp(q[2],stations,current[:,i]) for i in (0,1)];y=q[1]
   for k,edge in enumerate((lo,hi)):
    w=max(0,1-abs(y-edge)/.008);w=w*w*(3-2*w);q[1]+=(target[k]-edge)*w
   v.co=roll(Vector(q))
  report[gun]=dict(start_m=begin,end_m=end,edge_method='Hermite end tangents; 8 mm rim blend; intact factory plate',max_displacement_mm=max((v.co-p).length for v,p in zip(mesh.vertices,oldpos))*1000)
 # Use actual surface normals on rebuilt regions; keep original feed/grip.
 for p in mesh.polygons:p.use_smooth=True
 mesh.set_sharp_from_angle(angle=math.radians(55));mesh.normals_split_custom_set([(0,0,0)]*len(mesh.loops));mesh.update();norm=[n.vector.copy() for n in mesh.corner_normals]
 for i,l in enumerate(mesh.loops):
  s=unroll(mesh.vertices[l.vertex_index].co).z
  if s<(cut if gun=='M4' else begin)-.00001 or (gun=='QBZ' and s>end):norm[i]=oldnorm[i]
 mesh.normals_split_custom_set(norm);mesh.update()
 if gun=='M4':
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

 ob.name='SM_ExtMag_'+gun+'40_Remodel';bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 (O/'FBX').mkdir(exist_ok=True);export(mesh,O/'FBX'/(ob.name+'.fbx'));bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/(gun+'_ExtMag_Remodel_Editable.blend')))
 report.setdefault(gun,{}).update(dict(vertices=len(mesh.vertices),tested=False));(O/'authoring.json').write_text(json.dumps(report,indent=2))
 print('REMODEL_AUTHORED',gun,flush=True)
