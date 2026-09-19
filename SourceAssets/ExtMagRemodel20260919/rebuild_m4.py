"""Factory surface continuation in cylindrical coordinates; no procedural ribs."""
import bpy,bmesh,math,json,sys
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'ExtMagPattern20260919'))
from export_tangents import export
OLD=O.parent/'ExtMagRebuild20260919'
JOBS={'M4':(.030,.0125)}
reports={}
for gun,(cutheight,period) in JOBS.items():
 bpy.ops.wm.open_mainfile(filepath=str(OLD/(gun+'_ExtMag_Editable.blend')))
 factory=bpy.data.objects['Factory_'+gun]
 ob=factory.copy();ob.data=factory.data.copy();bpy.context.collection.objects.link(ob)
 ob.hide_set(False);ob.hide_render=False;ob.name='SM_ExtMag_'+gun+'40_Remodel'
 for obj in list(bpy.context.scene.objects):
  if obj!=ob:bpy.data.objects.remove(obj,do_unlink=True)
 mesh=ob.data;pts=[v.co.copy() for v in mesh.vertices]
 xyz=np.array([tuple(p) for p in pts]);lo=xyz.min(axis=0);hi=xyz.max(axis=0)
 rows=[];rhs=[];samples=[]
 # Fit the two longitudinal edges to concentric arcs. Separate radii prevent
 # front/back width from contaminating the centre of curvature.
 for z in np.linspace(lo[2]+.055,hi[2]-.065,64):
  hits=[]
  for edge in mesh.edges:
   a,b=[pts[i] for i in edge.vertices]
   if (a.z-z)*(b.z-z)<0:hits.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
  if not hits:continue
  for side,y in enumerate([min(p.y for p in hits),max(p.y for p in hits)]):
   rows.append([2*y,2*z,float(side==0),float(side==1)]);rhs.append(y*y+z*z)
   samples.append([side,y,z])
 A=np.array(rows);B=np.array(rhs);fit=np.linalg.lstsq(A,B,rcond=None)[0]
 for _ in range(5):
  err=np.abs(A@fit-B);scale=max(float(np.median(err))*2,1e-7);w=1/np.maximum(1,err/scale)
  fit=np.linalg.lstsq(A*w[:,None],B*w,rcond=None)[0]
 cy,cz=fit[:2];radii=[math.sqrt(max(1e-8,fit[i]+cy*cy+cz*cz)) for i in (2,3)]
 radius=sum(radii)/2;xc=(lo[0]+hi[0])/2
 angles=np.unwrap(np.arctan2(xyz[:,2]-cz,xyz[:,1]-cy));ref=float(np.median(angles))
 def theta(p):
  t=math.atan2(p.z-cz,p.y-cy)
  return ref+math.atan2(math.sin(t-ref),math.cos(t-ref))
 # q runs from feed end towards floorplate, measured in physical arc length.
 top=pts[int(np.argmax(xyz[:,2]))];bottom=pts[int(np.argmin(xyz[:,2]))]
 direction=1 if theta(bottom)>theta(top) else -1
 ttop=theta(top)
 def unroll(p):return Vector((p.x-xc,math.hypot(p.y-cy,p.z-cz)-radius,direction*(theta(p)-ttop)*radius))
 def roll(q):
  t=ttop+direction*q.z/radius;r=radius+q.y
  return Vector((q.x+xc,cy+r*math.cos(t),cz+r*math.sin(t)))
 qpts=[unroll(p) for p in pts];end=max(p.z for p in qpts);cut=end-cutheight
 mesh.calc_loop_triangles();tris=[tuple(t.vertices) for t in mesh.loop_triangles]
 tree=BVHTree.FromPolygons(qpts,tris,all_triangles=True)
 step=.00025;ss=np.arange(.065,end-.015,step);signal=[]
 for s in ss:
  values=[]
  for y in [-.025,-.015,0,.015,.025]:
   hit=tree.ray_cast(Vector((.1,y,s)),Vector((-1,0,0)),.2)[0]
   values.append(hit.x if hit else 0)
  signal.append(values)
 sig=np.array(signal);smooth=np.stack([np.convolve(sig[:,i],np.ones(21)/21,'same') for i in range(5)],axis=1);detail=sig-smooth
 scores=[]
 for lag in range(32,min(180,len(ss)//2)):
  a=detail[12:-lag-12];b=detail[lag+12:-12]
  score=float(np.sum(a*b)/max(1e-15,math.sqrt(np.sum(a*a)*np.sum(b*b))))
  scores.append((score,lag*step))
 (O/(gun+'_profile.json')).write_text(json.dumps({'samples':[[float(s),*map(float,v)] for s,v in zip(ss,sig)],'period_candidates':sorted(scores,reverse=True)[:12]}))
 reports[gun]={'center_yz':[cy,cz],'radius_cm':radius*100,'edge_radii_cm':[r*100 for r in radii],'length_cm':end*100,'cut_s_cm':cut*100,'period_cm':period*100}
 print('PARAMETERS',gun,json.dumps(reports[gun]),flush=True)
 # Cut through matching quiet phases rather than through a ridge crest.
 # Source periods above are measured in the unrolled surface, not world Z.
 repeats={'M4':5,'AKM':2,'QBZ':2}[gun];extension=period*repeats
 candidates=np.arange(cut-.005,cut+.005,.00025)
 def section(s):
  v=[]
  for phi in np.linspace(0,2*math.pi,96,endpoint=False):
   d=Vector((math.cos(phi),math.sin(phi),0))
   hit=tree.ray_cast(Vector((0,0,s))+d*.12,-d,.12)[0]
   v.append(hit if hit else Vector((0,0,s)))
  return v
 costs=[]
 for c in candidates:
  a=section(c-period);b=section(c)
  costs.append(sum((Vector((p.x,p.y))-Vector((q.x,q.y))).length_squared for p,q in zip(a,b)))
 cut=float(candidates[int(np.argmin(costs))]);cut={'M4':.132,'AKM':cut,'QBZ':cut}[gun];start=cut-period
 bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active
 nlayer=bm.loops.layers.float_vector.new('SourceNormal')
 mesh.update();normals=[x.vector.copy() for x in mesh.corner_normals]
 for face in bm.faces:
  for loop,li in zip(face.loops,mesh.polygons[face.index].loop_indices):loop[nlayer]=normals[li]
 for v in bm.verts:v.co=unroll(v.co)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7)
 bmesh.ops.triangulate(bm,faces=list(bm.faces))
 for s in [start,cut]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,s),plane_no=(0,0,1),dist=1e-7)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
 def loops_at(s):
  edges={e for e in bm.edges if all(abs(v.co.z-s)<2e-6 for v in e.verts) and any(f.calc_center_median().z<s-1e-7 for f in e.link_faces) and any(f.calc_center_median().z>s+1e-7 for f in e.link_faces)}
  rings=[]
  while edges:
   e=edges.pop();chain=[e.verts[0],e.verts[1]]
   while chain[-1]!=chain[0]:
    nextedge=next((x for x in chain[-1].link_edges if x in edges),None)
    if nextedge is None:
     point=chain[-1].co
     print('OPEN_SECTION',s,'chain',len(chain),'point',list(point),'nearest',sorted([(round((v.co-point).length,8),list(v.co)) for e in edges for v in e.verts],key=lambda x:x[0])[:3],flush=True)
     raise RuntimeError(gun+' cut does not form a closed contour')
    edges.remove(nextedge);chain.append(nextedge.other_vert(chain[-1]))
   rings.append(chain[:-1])
  return sorted(rings,key=lambda vs:sum((vs[(i+1)%len(vs)].co-v.co).length for i,v in enumerate(vs)),reverse=True)
 arings=loops_at(start);brings=loops_at(cut)
 print('CONTOURS',gun,[[[round(min(v.co[k] for v in ring),5),round(max(v.co[k] for v in ring),5)] for k in (0,1)] for ring in arings],flush=True)
 if len(arings)!=len(brings):raise RuntimeError(gun+' donor crosses a change in shell topology')
 def angle(v):return math.atan2(v.co.y,v.co.x)%(2*math.pi)
 def contour(vs):return [v.co.copy() for v in vs]
 def at(cont,phi):
  d=Vector((math.cos(phi),math.sin(phi)));hits=[]
  for i,p in enumerate(cont):
   q=cont[(i+1)%len(cont)];e=Vector((q.x-p.x,q.y-p.y));p2=Vector((p.x,p.y));den=e.x*d.y-e.y*d.x
   if abs(den)<1e-12:continue
   f=-(p2.x*d.y-p2.y*d.x)/den
   if -1e-7<=f<=1+1e-7:
    hit=p.lerp(q,min(1,max(0,f)))
    if hit.x*d.x+hit.y*d.y>0:hits.append(hit)
  if not hits:raise RuntimeError('Cut contour is not star shaped; needs a different section')
  return max(hits,key=lambda p:p.x*d.x+p.y*d.y)
 ac=[contour(vs) for vs in arings];bc=[contour(vs) for vs in brings]
 # Insert the union of boundary angular knots on BOTH original sections. This
 # gives shared seam topology without a fan, collapsed strips, or hard pinning.
 for av,bv in zip(arings,brings):
  angles=sorted({round(angle(v),9) for v in av+bv})
  for vs in [av,bv]:
   for i,v0 in enumerate(vs):
    v1=vs[(i+1)%len(vs)];edge=next(e for e in v0.link_edges if e.other_vert(v0)==v1)
    p=v0.co.copy();q=v1.co.copy();e=q-p;fractions=[]
    for phi in angles:
     d=Vector((math.cos(phi),math.sin(phi)));den=e.x*d.y-e.y*d.x
     if abs(den)<1e-12:continue
     f=-(p.x*d.y-p.y*d.x)/den;point=p+e*f
     if 1e-5<f<1-1e-5 and point.x*d.x+point.y*d.y>0:fractions.append(f)
    current=v0;previous=0
    for f in sorted(set(fractions)):
     edge=next(e for e in current.link_edges if e.other_vert(current)==v1)
     _,new=bmesh.utils.edge_split(edge,current,(f-previous)/(1-previous));current=new;previous=f
 # Each shell is a disconnected surface inside the donor band. Keep its
 # contour identity through the whole band instead of choosing nearest radius.
 band={f for f in bm.faces if start+1e-8<f.calc_center_median().z<cut-1e-8}
 shell_for={};seen=set()
 for seed in list(band):
  if seed in seen:continue
  stack=[seed];seen.add(seed);group=[]
  while stack:
   face=stack.pop();group.append(face)
   for edge in face.edges:
    for other in edge.link_faces:
     if other in band and other not in seen:seen.add(other);stack.append(other)
  verts={v for face in group for v in face.verts}
  shell=max(range(len(arings)),key=lambda k:len(verts.intersection(arings[k])))
  for v in verts:shell_for[v]=shell
 def mapped(q,mode,shell=0):
  p=q.copy()
  if mode==-1:p.z+=extension
  elif mode>=1:
   t=min(1,max(0,(p.z-start)/period));phi=math.atan2(p.y,p.x)
   a=at(ac[shell],phi);b=at(bc[shell],phi);weight=1-t*t*(3-2*t)
   p.x+=(b.x-a.x)*weight;p.y+=(b.y-a.y)*weight;p.z+=mode*period
  return roll(p)
 out=bmesh.new();ouv=out.loops.layers.uv.new('UVMap');on=out.loops.layers.float_vector.new('AuthoredNormal')
 vcache={};ncache={};coordcache={}
 def dst(v,mode):
  key=(v,mode)
  if key not in vcache:
   p=mapped(v.co,mode,shell_for.get(v,0));weld=tuple(round(x,7) for x in p)
   if weld not in coordcache:coordcache[weld]=out.verts.new(p)
   vcache[key]=coordcache[weld]
  return vcache[key]
 def normal(v,n,mode):
  if mode==0:return n.normalized()
  key=(v,mode)
  if key not in ncache:
   original=roll(v.co);delta=1e-5;base=mapped(v.co,mode,shell_for.get(v,0));cols=[]
   for axis in range(3):
    p=original.copy();p[axis]+=delta;cols.append((mapped(unroll(p),mode,shell_for.get(v,0))-base)/delta)
   J=Matrix(cols).transposed();ncache[key]=J.inverted_safe().transposed()
  return (ncache[key]@n).normalized()
 def copyface(f,mode):
  verts=[dst(l.vert,mode) for l in f.loops]
  if len(set(verts))!=len(verts):return
  nf=out.faces.new(verts);nf.smooth=f.smooth
  for new,old in zip(nf.loops,f.loops):new[ouv].uv=old[uv].uv;new[on]=normal(old.vert,old[nlayer],mode)
 for f in bm.faces:
  z=f.calc_center_median().z
  copyface(f,0 if z<cut else -1)
  if start<z<cut:
   for i in range(1,repeats+1):copyface(f,i)
 # Explicit triangles keep FBX/UE on the same interpolation and tangent basis.
 bmesh.ops.remove_doubles(out,verts=list(out.verts),dist=1e-5)
 bmesh.ops.triangulate(out,faces=list(out.faces))
 bmesh.ops.dissolve_degenerate(out,dist=1e-6,edges=list(out.edges))
 bmesh.ops.triangulate(out,faces=list(out.faces))
 cn=[l[on].copy() for f in out.faces for l in f.loops]
 newmesh=bpy.data.meshes.new(gun+'_ExtendedFactorySurface');out.to_mesh(newmesh);out.free();bm.free()
 newmesh.materials.append(mesh.materials[0]);newmesh.update()
 cn=[n if n.length>.5 else newmesh.corner_normals[i].vector.copy() for i,n in enumerate(cn)]
 newmesh.normals_split_custom_set(cn);ob.data=newmesh
 newmesh.calc_tangents(uvmap='UVMap')
 zero=[l.index for l in newmesh.loops if l.tangent.length<.5]
 badfaces=[p for p in newmesh.polygons if any(i in zero for i in p.loop_indices)]
 (O/(gun+'_tangent_work.json')).write_text(json.dumps([{'area':p.area,'uv':[list(newmesh.uv_layers.active.data[i].uv) for i in p.loop_indices],'coords':[list(newmesh.vertices[i].co) for i in p.vertices]} for p in badfaces],indent=2))
 print('TANGENT_AUTHORING',gun,'zero',len(zero),'loops',len(newmesh.loops),'uv',[(tuple(newmesh.uv_layers.active.data[i].uv)) for i in zero[:3]],flush=True)
 ob.name='SM_ExtMag_'+gun+'40_Remodel'
 reports[gun].update({'cut_s_cm':cut*100,'donor_start_cm':start*100,'extension_cm':extension*100,'repeats':repeats,'source_contours':len(arings),'surface':'original clipped faces and per-corner UV, cylindrical continuation','vertices':len(newmesh.vertices)})
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 (O/'FBX').mkdir(exist_ok=True)
 bpy.context.preferences.filepaths.save_version=0
 reports[gun]['adjacent_basis_corners']=export(newmesh,O/'FBX'/('SM_ExtMag_'+gun+'40_Remodel.fbx'))
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(gun+'_ExtMag_Remodel_Editable.blend')))
 print('AUTHORED',gun,json.dumps(reports[gun]),flush=True)
(O/'parameters.json').write_text(json.dumps(reports,indent=2))
