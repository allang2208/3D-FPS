"""Factory-based extensions. Preserve cut EDGE connectivity and interpolate donor UVs.

The old arc builder angular-sorted vertices from multiple loops, connected unrelated
edges, and left every new loop UV at zero. This builds each actual cut edge, including
inner shells, with shared vertices and curved frames. The untouched upper/grip region
keeps its original geometry/UV and split normals.
"""
import bpy, bmesh, math, json
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
O=Path(__file__).parent; SA=O.parent
JOBS={
 'M4':('M4HK416Replica20260910/SK_M4_FoldingSights_HK416.fbx','M4_Magazine Light.003_Export',.030,.01212,5),
 'AKM':('PhantomRearGripIntegration20260913/AKM/SK_AKM_MannyNative.fbx','AKM_FactoryMagazine_Preview',.035,.015,4),
 'QBZ':('PhantomRearGripIntegration20260913/QBZ191/SK_QBZ191_Manny.fbx','QBZ_Magazine',.035,.00819,7),
}
(O/'FBX').mkdir(exist_ok=True)
reports={}
for gun,(src,objname,cutheight,pitch,repeats) in JOBS.items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(SA/src))
 ob=bpy.data.objects[objname];arm=next(x for x in bpy.context.scene.objects if x.type=='ARMATURE');arm.data.pose_position='REST';bpy.context.view_layer.update()
 world=ob.matrix_world.copy();ob.parent=None;ob.matrix_world=world
 ob.modifiers.clear();bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 # Extract only the factory magazine material; other faces on shared objects stay out.
 mesh=ob.data;slot=next(i for i,m in enumerate(mesh.materials) if m and 'magazine' in m.name.lower());mat=mesh.materials[slot]
 bm=bmesh.new();bm.from_mesh(mesh)
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=slot],context='FACES')
 for f in bm.faces:f.material_index=0
 bm.to_mesh(mesh);bm.free();mesh.materials.clear();mesh.materials.append(mat);mesh.update()
 for other in list(bpy.context.scene.objects):
  if other!=ob:bpy.data.objects.remove(other,do_unlink=True)
 factory=ob.copy();factory.data=mesh.copy();factory.name='Factory_'+gun;bpy.context.collection.objects.link(factory);factory.hide_render=True;factory.hide_set(True)
 # Donor triangles contain true original UVs and corner normals.
 mesh.calc_loop_triangles();triangles=[(tuple(t.vertices),tuple(t.loops)) for t in mesh.loop_triangles]
 pts=[v.co.copy() for v in mesh.vertices];faces=[t[0] for t in triangles]
 normals=[tuple(mesh.corner_normals[i].vector) for i in range(len(mesh.loops))]
 donor_uv=[tuple(x.uv) for x in mesh.uv_layers.active.data]
 tree=BVHTree.FromPolygons(pts,faces,all_triangles=True)
 def attributes(p):
  q,n,idx,d=tree.find_nearest(p);t=triangles[idx];a,b,c=[pts[i] for i in t[0]]
  uv=barycentric_transform(p,a,b,c,*[Vector((*donor_uv[i],0)) for i in t[1]])
  nn=barycentric_transform(q,a,b,c,*[Vector(normals[i]) for i in t[1]]).normalized()
  return uv,nn
 # Robust cross-section centres follow the main body, not the feed lips/baseplate.
 xyz=np.array([tuple(p) for p in pts]);lo=xyz.min(axis=0);hi=xyz.max(axis=0)
 # Intersect actual edges at uniform heights. Vertex-density centroids are
 # biased by rib/plate tessellation and can even reverse the extension bend.
 samples=[]
 for z in np.linspace(lo[2]+.012,hi[2]-.025,32):
  crossing=[]
  for edge in mesh.edges:
   a,b=[pts[i] for i in edge.vertices]
   if (a.z-z)*(b.z-z)<0:crossing.append(a+(b-a)*((z-a.z)/(b.z-a.z)))
  if crossing:samples.append((z,float((lo[0]+hi[0])*.5),(min(p.y for p in crossing)+max(p.y for p in crossing))*.5))
 samples=np.array(samples);cx=np.polyfit(samples[:,0],samples[:,1],2);cy=np.polyfit(samples[:,0],samples[:,2],2)
 def center(z):return Vector((float(np.polyval(cx,z)),float(np.polyval(cy,z)),z))
 def tangent(z):return Vector((float(np.polyval(np.polyder(cx),z)),float(np.polyval(np.polyder(cy),z)),1)).normalized()
 zcut=float(lo[2]+cutheight);origin=center(zcut);up=tangent(zcut)
 # Use the same source slice direction for the cut and donor sampling.
 length=pitch*repeats
 axis=up.cross(tangent(zcut+length));bend=up.angle(tangent(zcut+length))/length
 if axis.length<1e-5:axis=Vector((1,0,0));bend=0
 else:axis.normalize()
 bend=min(bend,8.)
 def frame(s):
  R=Matrix.Rotation(-bend*s,3,axis)
  if bend<1e-6:delta=-up*s
  else:delta=-up*(math.sin(bend*s)/bend)+axis.cross(up)*((1-math.cos(bend*s))/bend)
  return R,origin+delta
 def move(p,s):
  R,c=frame(s);return c+R@(p-origin)
 bm=bmesh.new();bm.from_mesh(mesh);uv=bm.loops.layers.uv.active
 preserved=bm.loops.layers.float_vector.new('FactoryCornerNormal')
 for f in bm.faces:
  for loop,li in zip(f.loops,mesh.polygons[f.index].loop_indices):loop[preserved]=normals[li]
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=origin,plane_no=up,dist=1e-7)
 lower={f for f in bm.faces if (f.calc_center_median()-origin).dot(up)<-1e-8}
 cutedges=[e for e in bm.edges if all(abs((v.co-origin).dot(up))<2e-6 for v in e.verts) and any(f in lower for f in e.link_faces) and any(f not in lower for f in e.link_faces)]
 if not cutedges:raise RuntimeError(gun+' has no cross-shell cut edges')
 # Retain oriented edge loops from the actual upper boundary (no polar sorting).
 edge_records=[]
 for e in cutedges:
  upper=next(f for f in e.link_faces if f not in lower)
  loop=next(l for l in upper.loops if l.edge==e)
  edge_records.append((loop.vert,loop.link_loop_next.vert))
 ringverts=set(v for pair in edge_records for v in pair)
 # Move the original lower faces using a shared vertex map; no duplicate shell.
 lowerverts=set(v for f in lower for v in f.verts);bottom={v:bm.verts.new(move(v.co,length)) for v in ringverts}
 Rbottom,_=frame(length)
 for f in lower:
  for l in f.loops:l[preserved]=Rbottom@l[preserved]
 for v in lowerverts-ringverts:v.co=move(v.co,length)
 # Rebuild only faces touching the cut to substitute the lower copy of the seam.
 touched=[f for f in lower if any(v in ringverts for v in f.verts)]
 for f in touched:
  corners=[bottom.get(l.vert,l.vert) for l in f.loops];uvs=[l[uv].uv.copy() for l in f.loops];ns=[l[preserved].copy() for l in f.loops];smooth=f.smooth
  bm.faces.remove(f);nf=bm.faces.new(corners);nf.smooth=smooth
  for l,t,n in zip(nf.loops,uvs,ns):l[uv].uv=t;l[preserved]=n
 # Periodic donor cross sections continue original moulded/stamped relief.
 # Each ray starts outside, so it samples the outer surface rather than cavity.
 stepcount=repeats*24
 rings=[{v:v for v in ringverts}];donor_positions={}
 for i in range(1,stepcount):
  s=length*i/stepcount;phase=(s/pitch)%1;donorz=zcut+pitch*(1-phase)
  dz=donorz-zcut;dc=center(donorz);donor_rot=up.rotation_difference(tangent(donorz)).to_matrix()
  R,c=frame(s);row={};envelope=min(1.,s/.004,(length-s)/.004)
  for v in ringverts:
   radial=v.co-origin;radial-=up*radial.dot(up);direction=radial.normalized()
   local=radial.copy()
   # Carry longitudinal factory relief exactly. Never ray-sample the baseplate
   # as repeated geometry (that creates flange-sized bulges). Polymer shells
   # receive shallow moulded cross-ribs; stamped AKM ribs continue lengthwise.
   if gun!='AKM':
    crest=max(0.,1.-abs(phase-.5)/.14)
    crest=crest*crest*(3.-2.*crest)
    local+=direction*(.00055*crest*envelope)
   row[v]=bm.verts.new(c+R@local)
  rings.append(row)
 rings.append(bottom)
 created=[]
 for i in range(stepcount):
  for a,b in edge_records:
   f=bm.faces.new((rings[i][b],rings[i][a],rings[i+1][a],rings[i+1][b]));f.smooth=True;created.append(f)
   # Every corner gets real UV; use the same period on both sides of a quad
   # to avoid interpolation across a repeated atlas strip.
   cycle=i//24
   for l,base,row in zip(f.loops,[b,a,a,b],[i,i,i+1,i+1]):
    phase=(row-cycle*24)/24
    dz=pitch*(1-phase)
    radial=base.co-origin
    dr=up.rotation_difference(tangent(zcut+dz)).to_matrix()@radial
    sample=center(zcut+dz)+dr
    l[uv].uv=attributes(sample)[0].xy
   coords=[l[uv].uv.copy() for l in f.loops]
   u=coords[1]-coords[0];v=coords[3]-coords[0]
   w=coords[2]-coords[0]
   if min(abs(u.x*w.y-u.y*w.x),abs(w.x*v.y-w.y*v.x))<1e-10:
    # Near an atlas seam, a nearest source face may collapse the projected UV
    # strip. Keep a finite, local texel footprint so tangent generation works.
    if u.length<1e-6:u=Vector((max((a.co-b.co).length,.0001)*2,0))
    v=Vector((-u.y,u.x)).normalized()*(length/stepcount)*2
    for l,t in zip(f.loops,[coords[0],coords[0]+u,coords[0]+u+v,coords[0]+v]):l[uv].uv=t
 bmesh.ops.recalc_face_normals(bm,faces=bm.faces[:])
 kept_normals=[l[preserved].copy() for f in bm.faces for l in f.loops]
 bm.to_mesh(mesh);bm.free();mesh.update()
 # Keep source corner normals above cut; use generated smooth normals below.
 custom=[]
 Rfinal,_=frame(length)
 for p in mesh.polygons:
  for li in p.loop_indices:
   co=mesh.vertices[mesh.loops[li].vertex_index].co
   if kept_normals[li].length>.5:nn=kept_normals[li].normalized()
   else:nn=mesh.corner_normals[li].vector.copy()
   custom.append(nn)
 for p in mesh.polygons:p.use_smooth=True
 mesh.normals_split_custom_set(custom)
 ob.name='SM_ExtMag_'+gun+'40';ob['factory_source']=src;ob['extension_cm']=length*100
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.export_scene.fbx(filepath=str(O/'FBX'/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(gun+'_ExtMag_Editable.blend')))
 reports[gun]={'source':src,'extension_cm':length*100,'cut_above_floor_cm':cutheight*100,'cut_normal':list(up),'bend_degrees':math.degrees(bend*length),'cut_edges':len(edge_records),'extension_faces':len(created),'uv':'factory per-corner donor interpolation, original upper UV retained','fbx':str(O/'FBX'/(ob.name+'.fbx'))}
 print('AUTHORED',gun,reports[gun],flush=True)
(O/'build_receipt.json').write_text(json.dumps(reports,indent=2))
