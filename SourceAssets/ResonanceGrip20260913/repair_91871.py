import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME/SourceAssets/ResonanceGrip20260913/Repaired91871');P.mkdir(exist_ok=True);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P.parent/'seed_91871/textured_master_00001_.glb'));ob=next(o for o in bpy.context.scene.objects if o.type=='MESH');ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
if ob.dimensions.x>ob.dimensions.y:ob.data.transform(Matrix.Rotation(math.pi/2,4,'Z'))
# Merge coincident GLTF seam vertices; loop UV coordinates stay independent.
bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
seen=set();filled=0
for e in list(bm.edges):
 if not e.is_boundary or e in seen:continue
 todo=[e];group=[];verts=set()
 while todo:
  edge=todo.pop()
  if edge in seen:continue
  seen.add(edge);group.append(edge);verts.update(edge.verts)
  for v in edge.verts:todo.extend(x for x in v.link_edges if x.is_boundary and x not in seen)
 if verts and max(max(v.co[i] for v in verts)-min(v.co[i] for v in verts) for i in range(3))<.018:
  bmesh.ops.holes_fill(bm,edges=group,sides=0);filled+=1
lo=Vector([min(v.co[i] for v in bm.verts) for i in range(3)]);hi=Vector([max(v.co[i] for v in bm.verts) for i in range(3)]);w=hi.y-lo.y;h=hi.z-lo.z
# Local fairing on the distorted rear strut; keep the outer silhouette and main opening.
region=[v for v in bm.verts if .70<(hi.y-v.co.y)/w<.92 and .26<(v.co.z-lo.z)/h<.62 and not v.is_boundary and all(e.calc_face_angle(0)<.55 for e in v.link_edges)]
for _ in range(3):bmesh.ops.smooth_vert(bm,verts=region,factor=.22,use_axis_x=True,use_axis_y=False,use_axis_z=False)
centers=[(.264,.953),(.712,.954),(.954,.884),(.409,.803),(.410,.534),(.842,.463),(.740,.134),(.581,.129)]
# Flatten only old screw disks, then overlay regular recessed screw geometry.
for u,v in centers:
 y=hi.y-u*w;z=lo.z+v*h;radius=.029*w
 ring=[q.co for q in bm.verts if radius*.9<math.hypot(q.co.y-y,q.co.z-z)<radius*1.15]
 for sign in [-1,1]:
  surface=[p.x for p in ring if p.x*sign>0]
  if not surface:continue
  depth=sorted(surface)[len(surface)//2]
  for q in bm.verts:
   if q.co.x*sign>0 and math.hypot(q.co.y-y,q.co.z-z)<radius*.9:
    q.co.x=depth
bm.to_mesh(ob.data);bm.free();ob.data.update();parts=[ob]
mat=bpy.data.materials.new('Repaired_ScrewMetal');mat.use_nodes=True;bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(.045,.048,.052,1);bs.inputs['Metallic'].default_value=.8;bs.inputs['Roughness'].default_value=.36
for u,v in centers:
 y=hi.y-u*w;z=lo.z+v*h
 ring=[q.co for q in ob.data.vertices if .026*w<math.hypot(q.co.y-y,q.co.z-z)<.033*w]
 for sign in [-1,1]:
  vals=sorted(p.x for p in ring if p.x*sign>0)
  if not vals:continue
  x=vals[len(vals)//2];verts=[];faces=[];N=48
  for rad,dep in [(.027,0),(.025,.003),(.021,.004),(.010,.004),(.010,-.002)]:
   for k in range(N):
    a=2*math.pi*k/N
    rr=rad*w
    if rad==.010:rr/=math.cos((a%(math.pi/3))-math.pi/6)
    verts.append((x+sign*dep*w,y+math.cos(a)*rr,z+math.sin(a)*rr))
  for j in range(4):
   for k in range(N):faces.append((j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k))
  faces.append(tuple(range(4*N,5*N)))
  if sign<0:faces=[tuple(reversed(f)) for f in faces]
  me=bpy.data.meshes.new('RecessedHexScrew');me.from_pydata(verts,[],faces);me.materials.append(mat);o=bpy.data.objects.new('RecessedHexScrew',me);bpy.context.collection.objects.link(o);parts.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=ob;bpy.ops.object.join();ob.name='Resonance91871_RepairedMaster'
bpy.ops.wm.save_as_mainfile(filepath=str(P/'RepairedMaster.blend'));bpy.ops.export_scene.gltf(filepath=str(P/'RepairedMaster.glb'),use_selection=True,export_format='GLB')
(P/'repair.json').write_text(json.dumps({'small_boundary_loops_filled':filled,'local_fairing_vertices':len(region),'regular_recessed_screws':len(parts)-1,'selected_seed':91871},indent=2))
