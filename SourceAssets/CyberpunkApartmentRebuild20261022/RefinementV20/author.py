"""Retain the calibrated front rail; replace privacy screens with matching side returns."""
import bpy,bmesh,math,json
from pathlib import Path
R=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(R.parent/'RefinementV7/BalconyRail_Source.blend'),link=False) as (source,target):target.objects=['SM_AP7_BalconyRail']
front=target.objects[0];bpy.context.collection.objects.link(front);front.hide_set(False);front.hide_render=False;front.name='SM_AP20_FrontRail'
front.location=(0,0,0);front.rotation_euler=(0,0,0);front.scale=(1,1,1)
bm=bmesh.new();bm.from_mesh(front.data)
# The two privacy-screen cap strips are the only front-asset geometry above 1.3 m.
caps=[v for v in bm.verts if v.co.z>1.3];removed=len(caps);bmesh.ops.delete(bm,geom=caps,context='VERTS');bm.to_mesh(front.data);bm.free();front.data.update()
materials={k:bpy.data.materials.get(k) or bpy.data.materials.new(k) for k in ('AP_Steel','AP_Dark','AP_Glass','AP_Collision')};parts={}
def box(key,p,d,role,bevel=0):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p);o=bpy.context.object;o.scale=d;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(materials[role])
 if bevel:
  m=o.modifiers.new('Matching post edge','BEVEL');m.width=bevel;m.segments=4;bpy.ops.object.modifier_apply(modifier=m.name)
 parts.setdefault(key,[]).append(o);return o
def handrail(key,x,y0,y1):
 # Matches the front rail's calibrated elliptical tube after its actor scale.
 n=24;rings=[[(x+math.cos(i*math.tau/n)*.027,yy,1.10*2/3+math.sin(i*math.tau/n)*.018) for i in range(n)] for yy in (y0,y1)]
 vs=rings[0]+rings[1];faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
 faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 me=bpy.data.meshes.new('SideHandrail');me.from_pydata(vs,[],faces);me.update();o=bpy.data.objects.new('SideHandrail',me);bpy.context.collection.objects.link(o);me.materials.append(materials['AP_Steel'])
 for p in me.polygons:p.use_smooth=p.index>1
 parts.setdefault(key,[]).append(o)
y0=-.04;y1=-3.43;spacing=(y1-y0)/3
for side,x in [('Left',5.10),('Right',14.0)]:
 for j in range(3):
  y=y0+j*spacing
  # The existing front corner post remains the fourth support.
  box('SideFrames',(x,y,.54*2/3),(.06,.05,1.08*2/3),'AP_Steel',.0045)
  box('SideFrames',(x,y,.015*2/3),(.14,.15,.03*2/3),'AP_Dark')
 handrail('SideFrames',x,y0,y1)
 for j in range(3):box('SideGlass',(x,y0+(j+.5)*spacing,.56),(.018,abs(spacing)-.065,.94),'AP_Glass')
 box('SideCollision',(x,y1/2,.55),(.08,abs(y1),1.1),'AP_Collision')
records=[];out=R/'Meshes';out.mkdir(exist_ok=True)
objects={'FrontRail':front}
for key,items in parts.items():
 bpy.ops.object.select_all(action='DESELECT')
 for ob in items:ob.select_set(True)
 bpy.context.view_layer.objects.active=items[0];bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_AP20_'+key;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);objects[key]=ob
 uv=ob.data.uv_layers.active or ob.data.uv_layers.new(name='SurfaceUV')
 for face in ob.data.polygons:
  axes=[a for a in range(3) if a!=max(range(3),key=lambda j:abs(face.normal[j]))]
  for li in face.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
for key,ob in objects.items():
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Production triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 hulls=[]
 if key=='SideCollision':
  for i,x in enumerate((5.10,14.0)):
   hull=box('Hull',(x,y1/2,.55),(.08,abs(y1),1.1),'AP_Collision');hull.name='UCX_'+ob.name+'_'+str(i);hulls.append(hull)
  bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
  for hull in hulls:hull.select_set(True)
  bpy.context.view_layer.objects.active=ob
 file=out/(ob.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=key,name=ob.name,fbx=str(file),triangles=len(ob.data.polygons),simple_boxes=len(hulls)))
 for hull in hulls:bpy.data.objects.remove(hull,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'BalconyGlassReturns_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,removed_cap_vertices=removed,side_panels=6,side_posts=6,front_corner_posts_reused=True,front_height_m=1.1),indent=2),encoding='utf8');print('AP20_BALCONY_AUTHORED',flush=True)
