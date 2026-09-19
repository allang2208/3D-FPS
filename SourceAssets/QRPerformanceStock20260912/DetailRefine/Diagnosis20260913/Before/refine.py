"""Rebuild the fused QR details to the accepted three-view silhouette.
Author coordinates are centimetres: +X toward the buttpad; front mount at zero.
Production authoring/export only; no validation or preview rendering.
"""
import bpy,bmesh,math,json,random
from pathlib import Path
from mathutils import Vector

R=Path(__file__).parent;P=R.parent
TOP=2.063809633255005;HEIGHT=13.313357591629028
parts=[];records={}

def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o

def apply(o,modifier):
 active(o);bpy.ops.object.modifier_apply(modifier=modifier.name)

def finish(o,width=.06,segments=4):
 if width:
  m=o.modifiers.new('Machined edge radius','BEVEL');m.width=width;m.segments=segments;apply(o,m)
 for face in o.data.polygons:face.use_smooth=True
 m=o.modifiers.new('Weighted planar normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50;apply(o,m)
 return o

def xy(points):
 return [((x-55)*18/709,TOP-(z-108)*HEIGHT/568) for x,z in points]

def prism(name,profile,width,material,y=0,edge=0):
 n=len(profile);verts=[(x,side,z) for side in [y-width/2,y+width/2] for x,z in profile]
 faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update()
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);mesh.materials.append(material);parts.append(o)
 return finish(o,edge) if edge else o

def block(name,location,size,mat,edge=.04):
 bpy.ops.mesh.primitive_cube_add(size=1,location=location);o=bpy.context.object;o.name=name;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);parts.append(o)
 return finish(o,edge) if edge else o

def cylinder(name,location,radius,depth,mat,axis='Y',segments=64,edge=0):
 rotation=(math.pi/2,0,0) if axis=='Y' else (0,math.pi/2,0) if axis=='X' else (0,0,0)
 bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=radius,depth=depth,location=location,rotation=rotation)
 o=bpy.context.object;o.name=name;o.data.materials.append(mat);parts.append(o)
 return finish(o,edge) if edge else o

def cut(target,cutter,name='Machined recess'):
 m=target.modifiers.new(name,'BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter;apply(target,m)
 parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)

def fastener(x,z,side,y=1.13,r=.21):
 o=cylinder('Separate_socket_head',(x,side*y,z),r,.14,metal,segments=48)
 tool=cylinder('Hex_socket_tool',(x,side*(y+.074),z),r*.45,.11,metal,segments=6)
 cut(o,tool,'Recessed hex socket');finish(o,.015,3)

def material(name,color,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;return m

def stipple(profile,side):
 # Small individual rounded grains on an independent inset pad. No generated
 # macro normal map is reused on the newly machined surfaces.
 def inside(x,z):
  hit=False
  for i,(ax,az) in enumerate(profile):
   bx,bz=profile[(i+1)%len(profile)]
   if (az>z)!=(bz>z) and x<(bx-ax)*(z-az)/(bz-az)+ax:hit=not hit
  return hit
 def border_distance(x,z):
  p=Vector((x,z));dist=100.0
  for i,a in enumerate(profile):
   a=Vector(a);b=Vector(profile[(i+1)%len(profile)]);v=b-a;t=max(0,min(1,(p-a).dot(v)/v.length_squared));dist=min(dist,(p-a-v*t).length)
  return dist
 rng=random.Random(91291);verts=[];faces=[];xmin=min(p[0] for p in profile);xmax=max(p[0] for p in profile);zmin=min(p[1] for p in profile);zmax=max(p[1] for p in profile)
 row=0;z=zmin+.1
 while z<zmax-.08:
  x=xmin+.1+(row%2)*.073
  while x<xmax-.08:
   xx=x+rng.uniform(-.026,.026);zz=z+rng.uniform(-.023,.023)
   if inside(xx,zz) and border_distance(xx,zz)>.105:
    radius=rng.uniform(.029,.047);b=len(verts);N=8
    for rr,yy in [(radius,2.245),(radius*.56,2.266)]:
     verts.extend((xx+rr*math.cos(k*2*math.pi/N),side*yy,zz+rr*math.sin(k*2*math.pi/N)) for k in range(N))
    faces.extend((b+k,b+(k+1)%N,b+N+(k+1)%N,b+N+k) for k in range(N));faces.append(tuple(b+N+k for k in range(N)));faces.append(tuple(b+k for k in reversed(range(N))))
   x+=.146
  z+=.139;row+=1
 mesh=bpy.data.meshes.new('Cheek_stipple_grains');mesh.from_pydata(verts,[],faces);mesh.update();mesh.materials.append(poly)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
 o=bpy.data.objects.new('Controlled_cheek_stipple',mesh);bpy.context.collection.objects.link(o);parts.append(o)
 for f in mesh.polygons:f.use_smooth=True

def map_uv(o,key):
 active(o);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 is_metal=o.data.materials[0]==metal
 if is_metal and key=='akm':
  bm=bmesh.new();bm.from_mesh(o.data)
  for axis,step in [(0,12),(1,2.5),(2,2.5)]:
   lo=min(v.co[axis] for v in bm.verts);hi=max(v.co[axis] for v in bm.verts)
   for n in range(math.floor(lo/step)+1,math.ceil(hi/step)):
    co=[0,0,0];co[axis]=n*step;normal=[0,0,0];normal[axis]=1
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,plane_co=co,plane_no=normal)
  bm.to_mesh(o.data);bm.free()
 for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
 uv=o.data.uv_layers.new(name='SurfaceUV0');box=(.54,.73,.655,.85) if key=='m4' else (.055,.053,.285,.092)
 for f in o.data.polygons:
  dominant=max(range(3),key=lambda i:abs(f.normal[i]));ua=2 if dominant==0 else 0;va=2 if dominant==1 else 1
  tu=math.floor(f.center[ua]/12);tv=math.floor(f.center[va]/2.5)
  for li in f.loop_indices:
   p=o.data.vertices[o.data.loops[li].vertex_index].co
   a=(p[ua]+.5)/19.5;b=(p[va]+11.5)/15.5
   if is_metal and key=='akm':a=p[ua]/12-tu;b=p[va]/2.5-tv
   if is_metal:uv.data[li].uv=(box[0]+(box[2]-box[0])*max(.005,min(.995,a)),box[1]+(box[3]-box[1])*max(.005,min(.995,b)))
   else:uv.data[li].uv=(a,b)
 uv.active_render=True

for key in ['m4','akm']:
 bpy.ops.wm.open_mainfile(filepath=str(P/key.upper()/'QRPerformanceStock_Editable.blend'))
 original=bpy.data.objects['SM_QRPerformanceStock'];metal=next(m for m in original.data.materials if m.name.startswith('StockMetal')).copy();metal.name='StockMetal_Refined'
 poly=material('StockPolymer_Refined',(.021,.024,.027),.58);rubber=material('StockRubber_Refined',(.008,.009,.010),.84)
 reference=bpy.data.collections.new('Original_5080_reference');bpy.context.scene.collection.children.link(reference)
 for o in list(bpy.context.scene.objects):
  for collection in list(o.users_collection):collection.objects.unlink(o)
  reference.objects.link(o);o.hide_render=True;o.hide_set(True);o.select_set(False)
 reference.hide_render=True;reference.hide_viewport=True;parts=[]

 # Three clean windows reproduce the reference's main triangular opening,
 # lower opening and small upper rear opening. The frame is machined as one
 # continuous piece; hardware, lever, cheek insert and pad remain separate.
 outline=xy([(75,244),(183,246),(250,291),(327,283),(635,283),(660,263),(688,266),(684,551),(666,598),(632,627),(487,668),(462,657),(276,429),(216,369),(153,348),(85,326)])
 frame=prism('Retopologized_QR_frame',outline,2.10,metal)
 windows=[[(332,302),(466,302),(507,366),(403,451),(337,370)],[(429,493),(548,408),(588,421),(589,547),(571,578),(494,602)],[(537,302),(625,302),(621,324),(566,343)]]
 for i,profile in enumerate(windows):cut(frame,prism('Window_tool',xy(profile),5,metal,edge=.18),'Through window %d'%i)
 # QD aperture with defined circular rim instead of a melted generation bump.
 qx,qz=xy([(594,352)])[0]
 cut(frame,cylinder('QD_bore',(qx,0,qz),.28,5,metal),'QD mounting bore')
 # An inset channel follows the long front diagonal on both sides.
 channel=xy([(304,424),(321,426),(474,616),(492,632),(506,629),(498,645),(478,648),(461,629)])
 for side in [-1,1]:cut(frame,prism('Diagonal_channel_tool',channel,.24,metal,y=side*1.04,edge=.045),'Diagonal relief channel')
 finish(frame,.08,4)

 # The housing steps up from the existing front mount. Its inner passage is
 # continuous and its cheek panels have separate seams and fine geometry.
 housing=prism('Rounded_cheek_housing',[(.28,-1.64),(.28,1.63),(1.08,TOP),(15.94,TOP),(16.48,TOP-.11),(16.59,TOP-.45),(16.58,-1.79),(16.18,-2.04),(6.91,-2.04),(4.86,-1.57),(3.75,-1.15),(1.3,-1.15)],4.34,poly)
 cut(housing,cylinder('Continuous_mount_passage',(8,0,0),1.22,18,poly,axis='X',segments=96),'Open buffer tube passage')
 finish(housing,.22,5)
 # Thin annular front coupling: a real opening and a small readable rim.
 collar=cylinder('Front_metal_coupling',(.27,0,0),1.46,.52,metal,axis='X',segments=96)
 cut(collar,cylinder('Collar_opening',(.27,0,0),1.22,1.3,metal,axis='X',segments=96),'Open mounting ring');finish(collar,.035,4)

 pad_profile=xy([(212,133),(644,133),(656,145),(654,220),(641,234),(332,234),(245,195),(219,181)])
 for side in [-1,1]:
  cut(housing,prism('Cheek_panel_recess',pad_profile,.20,poly,y=side*2.16,edge=.075),'Inset cheek panel seam')
  # Slightly inset edge leaves a narrow continuous shadow line around insert.
  cx=sum(p[0] for p in pad_profile)/len(pad_profile);cz=sum(p[1] for p in pad_profile)/len(pad_profile)
  inset=[(cx+(x-cx)*.987,cz+(z-cz)*.943) for x,z in pad_profile]
  prism('Separate_stippled_cheek_insert',inset,.095,poly,y=side*2.197,edge=.045)
  stipple(inset,side)

 # The adjustment paddle is separate from the diagonal frame. A small gap,
 # machined pivot and ridges clarify the release mechanism in side views.
 lever=prism('Adjustment_release_paddle',xy([(107,269),(181,270),(223,302),(276,336),(272,355),(255,368),(210,343),(162,329),(105,312)]),2.42,metal,edge=.055)
 for side in [-1,1]:
  for px,pz,y in [(249,343,1.28),(312,397,1.13),(657,555,1.13)]:
   x,z=xy([(px,pz)])[0];fastener(x,z,side,y)
  for i in range(4):
   x,z=xy([(122+i*10,296)])[0];block('Release_paddle_grip_ridge',(x,side*1.23,z),(.095,.075,.41),metal,.02)
  # Separate QD rim with a real central hole.
  rim=cylinder('QD_socket_rim',(qx,side*1.12,qz),.42,.18,metal,segments=64)
  cut(rim,cylinder('QD_rim_tool',(qx,side*1.12,qz),.28,.6,metal,segments=64),'QD ring aperture');finish(rim,.024,4)

 # Rear carrier and rubber pad meet along a uniform, visible seam.
 carrier=prism('Rear_buttpad_carrier',xy([(686,115),(705,118),(716,149),(715,545),(700,593),(679,615),(645,628),(638,611),(670,590),(683,550)]),2.93,metal,edge=.075)
 pad=prism('Separate_rubber_buttpad',xy([(719,117),(741,123),(757,151),(759,543),(748,589),(729,617),(691,641),(651,648),(649,635),(684,620),(706,592),(719,546)]),3.13,rubber,edge=.14)
 # Tread ribs follow the shoulder contact face, each with an individual edge.
 for i in range(25):
  z=TOP-.96-i*.404;block('Shoulder_pad_tread_%02d'%i,(17.83,0,z),(.20,2.82,.13),rubber,.045)

 if key=='akm':
  adapter=block('AKM_receiver_cover',(.16,0,-.25),(.50,4.10,3.80),metal,edge=0)
  cut(adapter,cylinder('AKM_cover_passage',(.16,0,0),1.35,1.5,metal,axis='X',segments=96),'AKM independent receiver passage');finish(adapter,.055,4)

 for o in parts:map_uv(o,key)
 out=R/key.upper();out.mkdir(parents=True,exist_ok=True)
 active(frame);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'QRStock_Refined_Parts.blend'))
 # Keep the parts file editable. The engine receives one component, three slots.
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=frame;bpy.ops.object.join();frame.name='SM_QRPerformanceStock_Refined'
 oldslots=list(frame.data.materials);slots=[metal,poly,rubber];assignment=[slots.index(oldslots[f.material_index]) for f in frame.data.polygons]
 frame.data.materials.clear()
 for mat in slots:frame.data.materials.append(mat)
 for f,i in zip(frame.data.polygons,assignment):f.material_index=i
 bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'QRStock_Refined_Editable.blend'))
 m=frame.modifiers.new('Export triangles','TRIANGULATE');m.keep_custom_normals=True;apply(frame,m)
 bpy.ops.export_scene.fbx(filepath=str(out/'SM_QRPerformanceStock.fbx'),use_selection=True,object_types={'MESH'},global_scale=.01,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 frame.data.calc_loop_triangles();records[key]={'triangles':len(frame.data.loop_triangles),'author_dimensions_cm':list(frame.dimensions),'source':'5080 reconstruction and model_views.png','method':'hard surface retopology; separate hardware, three windows, inset cheek panels and shoulder pad','testing':'not performed; user will test'}
 print('QR_REFINED_EXPORTED',key,json.dumps(records[key]),flush=True)
(R/'authoring.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
