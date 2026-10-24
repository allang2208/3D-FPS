"""Original mounted billboard structures; no scene/acceptance render."""
import bpy,bmesh,math,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
out=ROOT/'Meshes';out.mkdir(exist_ok=True);parts=[]
mats={}
for name in ['MountMetal','CyanTrim','AmberTrim','Display']:
 mats[name]=bpy.data.materials.new(name)
def box(p,d,mat='MountMetal',bevel=.06):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=o.modifiers.new('Manufactured edge','BEVEL');mod.width=bevel;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
 o.data.materials.append(mats[mat]);parts.append(o);return o
for i,b in enumerate(BOARDS):
 x,y,z=b['p'];w,h,depth=b['w'],b['h'],b['depth'];trim='AmberTrim' if i%2 else 'CyanTrim'
 # Recessed display, real rear enclosure and anchored rails; 15 cm front separation.
 box((x,y+.70,z),(w+.90,1.10,h+.90))
 for s in [-1,1]:
  box((x+s*(w/2+.38),y+.10,z),(.62,1.20,h+1.30))
  box((x,y+.10,z+s*(h/2+.38)),(w+.90,1.20,.62))
  box((x+s*(w/2+.72),y-.12,z),(.09,.14,h+.9),trim,.02)
 # Wall-anchored steel standoffs and diagonal braces at three heights.
 for zz in [-h*.39,0,h*.39]:
  box((x,y+1.8,z+zz),(w*.94,.35,.45))
  for sx in [-1,1]:
   xx=x+sx*w*.39;box((xx,y+depth/2+1,z+zz),(.55,depth,.65))
   box((xx,y+depth,z+zz),(1.8,.40,2.2))
   a=Vector((xx,y+1.5,z+zz));c=Vector((xx,y+depth,z+zz+2.4));v=c-a
   o=box((a+c)/2,(.22,.22,v.length),bevel=.025);o.rotation_euler=v.to_track_quat('Z','Y').to_euler()
 # Attached maintenance catwalk, grating and protection rail.
 deck=z-h/2-1.1
 for sx in [-1,1]:box((x+sx*(w/2+.4),y-.8,deck),(.35,2.5,.35))
 for j in range(max(3,int(w/1.2))):box((x-w/2+j*1.2,y-.8,deck),(.14,2.5,.18),bevel=.015)
 box((x,y-2.05,deck+1.15),(w+.8,.12,.12),bevel=.02)
 for j in range(5):box((x-w/2+j*w/4,y-2.05,deck+.56),(.12,.12,1.12),bevel=.02)
 # Weatherproof junction enclosure and service conduits on the enclosure back.
 box((x+w*.32,y+1.5,z-h*.25),(1.5,.65,2.4))
 box((x+w*.32,y+1.52,z),( .14,.15,h*.5))
bpy.ops.object.select_all(action='DESELECT')
for p in parts:p.select_set(True)
bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();frame=bpy.context.object;frame.name='SM_AP8_MountedFrames'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
uv=frame.data.uv_layers.active or frame.data.uv_layers.new(name='UVMap')
for f in frame.data.polygons:
 axes=[a for a in range(3) if a!=max(range(3),key=lambda j:abs(f.normal[j]))]
 points=[frame.data.vertices[i].co for i in f.vertices];lo=[min(p[a] for p in points) for a in axes];span=[max(p[a] for p in points)-lo[i] for i,a in enumerate(axes)]
 for li in f.loop_indices:
  p=frame.data.vertices[frame.data.loops[li].vertex_index].co;uv.data[li].uv=tuple((p[a]-lo[i])/max(span[i],1e-8) for i,a in enumerate(axes))
# Resolve bevel micro-slivers before the ray-tracing/normal-map export. Each
# structural triangle gets a non-degenerate local tangent plane, independent
# of kilometre-scale city coordinates and inherited cube UV layers.
bm=bmesh.new();bm.from_mesh(frame.data)
bmesh.ops.dissolve_degenerate(bm,dist=.0001,edges=list(bm.edges))
bmesh.ops.triangulate(bm,faces=list(bm.faces))
tiny=[f for f in bm.faces if f.calc_area()<1e-8]
if tiny:bmesh.ops.delete(bm,geom=tiny,context='FACES')
bm.to_mesh(frame.data);bm.free();frame.data.update()
uv=frame.data.uv_layers.active
for f in frame.data.polygons:
 points=[frame.data.vertices[i].co for i in f.vertices];o=points[0];e=(points[1]-o).normalized();n=(points[1]-o).cross(points[2]-o).normalized();v=n.cross(e)
 coords=[((p-o).dot(e),(p-o).dot(v)) for p in points]
 lo=[min(c[i] for c in coords) for i in range(2)];span=[max(c[i] for c in coords)-lo[i] for i in range(2)]
 for li,co in zip(f.loop_indices,coords):uv.data[li].uv=tuple((co[i]-lo[i])/max(span[i],1e-10) for i in range(2))
# Shared one-metre display, front faces south, UV top stays at image top after FBX import.
mesh=bpy.data.meshes.new('Screen');mesh.from_pydata([(-.5,0,-.5),(.5,0,-.5),(.5,0,.5),(-.5,0,.5)],[],[(0,1,2,3)]);mesh.update()
screen=bpy.data.objects.new('SM_AP8_Display',mesh);bpy.context.collection.objects.link(screen);mesh.materials.append(mats['Display']);uv=mesh.uv_layers.new(name='UVMap')
for li,co in zip(mesh.polygons[0].loop_indices,[(0,0),(1,0),(1,1),(0,1)]):uv.data[li].uv=co
records=[]
for ob,world in [(frame,True),(screen,False)]:
 copy=ob.copy();copy.data=ob.data.copy();bpy.context.collection.objects.link(copy)
 for v in copy.data.vertices:v.co=(-v.co.x+(10 if world else 0),-v.co.y,v.co.z-(90 if world else 0))
 bpy.ops.object.select_all(action='DESELECT');copy.select_set(True);bpy.context.view_layer.objects.active=copy
 mod=copy.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 path=out/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE')
 records.append(dict(name=ob.name,fbx=str(path),triangles=len(copy.data.polygons)));bpy.data.objects.remove(copy,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Billboards_Source.blend'))
(ROOT/'assembly.json').write_text(json.dumps(dict(meshes=records,boards=BOARDS),indent=2),encoding='utf8')
print('AP8_GEOMETRY_AUTHORED',flush=True)
