import bpy,math,json,bmesh,numpy as np
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(O.parent/'vertical_grip_raw_00001_.glb'))
raw=bpy.context.selected_objects[0];raw.name='5080_Raw_Preserved'
v=np.array([tuple(raw.matrix_world@v.co) for v in raw.data.vertices]);lo=v.min(axis=0);hi=v.max(axis=0)
# Preserve the generated body's axial silhouette, replacing noisy radial topology.
height=.14;factor=height/(hi[2]-lo[2]);v=(v-(lo+hi)/2)*factor;v[:,2]-=height/2
raw.hide_render=True;raw.hide_set(True)
with bpy.data.libraries.load('D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend',link=False) as (a,b):b.materials=['Body.001','Grip Default.001']
metal=bpy.data.materials['Body.001'];poly=bpy.data.materials['Grip Default.001']
for m in [metal,poly]:
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE' and n.image:
   n.image.filepath='D:/FPS3D/FPSGAME/Content/M4NoSkel.fbm/'+Path(n.image.filepath.replace('\\','/')).name;n.image.reload()
parts=[]
def finish(o,mat,bevel=0):
 o.data.materials.clear();o.data.materials.append(mat);parts.append(o);bpy.context.view_layer.objects.active=o
 if bevel:
  m=o.modifiers.new('Machined edge highlights','BEVEL');m.width=bevel;m.segments=3
  bpy.ops.object.modifier_apply(modifier=m.name)
 for f in o.data.polygons:f.use_smooth=True
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 origin,size=((.53,.79),(.12,.05)) if mat==metal else ((.57,.16),(.12,.22))
 for uv in o.data.uv_layers.active.data:uv.uv=(origin[0]+uv.uv.x*size[0],origin[1]+uv.uv.y*size[1])
 return o
def lathe(profile,name,mat):
 vertices=[];faces=[];n=96
 for z,r in profile:
  vertices.extend([(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for i in range(n)])
 for k in range(len(profile)-1):
  for i in range(n):j=(i+1)%n;faces.append((k*n+i,k*n+j,(k+1)*n+j,(k+1)*n+i))
 faces.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(o)
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();return finish(o,mat)
profile=[]
for z in np.linspace(-.121,-.024,100):
 band=v[np.abs(v[:,2]-z)<.001]
 radius=float(np.median(np.linalg.norm(band[:,:2],axis=1))) if len(band) else .014
 profile.append((float(z),radius))
# Suppress only narrow generation noise; retain the broader generated profile.
rs=np.array([r for z,r in profile]);rs=np.convolve(np.pad(rs,(2,2),mode='edge'),np.ones(5)/5,mode='valid')
profile=[(z,float(r)) for (z,_),r in zip(profile,rs)]
lathe(profile,'VG_GeneratedProfile_Retopology',poly)
lathe([(-.138,.009),(-.137,.012),(-.133,.013),(-.123,.013),(-.121,.014)],'VG_BaseCap',poly)
lathe([(-.028,.012),(-.024,.015),(-.020,.020),(-.017,.022),(-.014,.022)],'VG_Neck',poly)
def box(name,loc,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);finish(o,metal,.0008)
# Continuous rounded top silhouette; cosmetic fasteners only.
outline=[(-.020,-.018),(.020,-.018),(.020,0),(.013,0),(.013,-.010),(-.013,-.010),(-.013,0),(-.020,0)]
vv=[(x,y,z) for x in [-.024,.024] for y,z in outline];nn=len(outline)
ff=[tuple(reversed(range(nn))),tuple(nn+i for i in range(nn))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
me=bpy.data.meshes.new('Rounded saddle');me.from_pydata(vv,[],ff);me.update();ob=bpy.data.objects.new('VG_ContinuousMount',me);bpy.context.scene.collection.objects.link(ob)
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free();finish(ob,metal,.0018)
for side in [-1,1]:
 bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=.0033,depth=.0009,location=(0,side*.0203,-.010),rotation=(math.pi/2,0,0));finish(bpy.context.object,metal,.0003)
# Subtle broad fluting on the retained lower cap, matching reference identity.
cap=next(o for o in parts if o.name=='VG_BaseCap')
for vertex in cap.data.vertices:
 c=vertex.co
 if -.137<c.z<-.121:
  a=math.atan2(c.y,c.x);q=1+.025*math.cos(a*12);c.x*=q;c.y*=q
for z in [-.085,-.092,-.099,-.106,-.113]:
 r=float(np.interp(z,[x[0] for x in profile],[x[1] for x in profile]))
 lathe([(z-.0010,r-.0002),(z-.0006,r+.00045),(z+.0006,r+.00045),(z+.001,r-.0002)],'VG_Ring',poly)
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();grip=bpy.context.object;grip.name='SM_VerticalForegrip'
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'VerticalForegrip_Refined.blend'))
bpy.ops.export_scene.fbx(filepath=str(O/'SM_VerticalForegrip.fbx'),use_selection=True,object_types={'MESH'},bake_anim=False,axis_forward='-Y',axis_up='Z',path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(O/'VerticalForegrip_Refined.glb'),use_selection=True,export_apply=True)
grip.data.calc_loop_triangles();(O/'model_report.json').write_text(json.dumps({'triangles':len(grip.data.loop_triangles),'dimensions_m':list(grip.dimensions),'method':'Generated body radial-profile retopology; mount and detail cleanup authored separately; raw retained unchanged','materials':[m.name for m in grip.data.materials]},indent=2))
