"""Visual-only game prop: authored hard-surface refinement of the generated candidate.
No fabrication dimensions or mechanically functional interface are supplied.
"""
import bpy, math, json, bmesh
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
S=bpy.context.scene
source='D:/FPS3D/FPSGAME/SourceAssets/M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend'
with bpy.data.libraries.load(source,link=False) as (a,b):
 b.materials=['Body.001','Grip Default.001']
metal=bpy.data.materials['Body.001'];poly=bpy.data.materials['Grip Default.001']
for m in [metal,poly]:
 for n in m.node_tree.nodes:
  if n.type=='TEX_IMAGE' and n.image:
   n.image.filepath='D:/FPS3D/FPSGAME/Content/M4NoSkel.fbm/'+Path(n.image.filepath.replace('\\','/')).name
   n.image.reload()
dark=bpy.data.materials.new('Recess shadow');dark.diffuse_color=(.008,.009,.011,1);dark.use_nodes=True
dark.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.65
dark.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(.008,.009,.011,1)
parts=[]
def finish(o,name,mat,bevel=.018):
 o.name=name;o.data.materials.clear();o.data.materials.append(mat);parts.append(o)
 bpy.context.view_layer.objects.active=o
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  mod=o.modifiers.new('Edge highlight bevel','BEVEL');mod.width=bevel;mod.segments=3;mod.harden_normals=True
  mod=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=30
 for f in o.data.polygons:f.use_smooth=True
 bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35),keep_sharp_edges=True)
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True)
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.025);bpy.ops.object.mode_set(mode='OBJECT')
 if mat in [metal,poly]:
  origin,size=((.53,.79),(.12,.05)) if mat==metal else ((.57,.16),(.12,.22))
  for l in o.data.uv_layers.active.data:l.uv=(origin[0]+l.uv.x*size[0],origin[1]+l.uv.y*size[1])
 return o
def box(name,loc,scale,mat=metal,bevel=.018):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.scale=scale;return finish(o,name,mat,bevel)
outer=[(-1,.48),(.7,.48),(.96,.38),(.96,.06),(.68,-.11),(.30,-.61),(-.03,-.65),(-.30,-.48),(-.61,.06),(-1,.12)]
inner=[(-.40,.26),(.65,.26),(.73,.22),(.72,.13),(.51,-.02),(.18,-.43),(.10,-.43),(-.04,-.25),(-.29,.10),(-.38,.18)]
verts=[(x,y,z) for y in [-.135,.135] for loop in [outer,inner] for x,z in loop];faces=[];N=len(outer)
for i in range(N):
 j=(i+1)%N
 faces.extend([(i,j,N+j,N+i),(2*N+i,3*N+i,3*N+j,2*N+j),(i,2*N+i,2*N+j,j),(N+i,N+j,3*N+j,3*N+i)])
mesh=bpy.data.meshes.new('Clean continuous open frame');mesh.from_pydata(verts,[],faces);mesh.update()
o=bpy.data.objects.new('Frame',mesh);S.collection.objects.link(o)
bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free();finish(o,'FG_Frame_M4Body',metal,.028)
box('FG_TopHousing',(-.10,0,.49),(1.77,.29,.13),metal,.025)
for x in [-.77,.57]:
 for y in [-.12,.12]:box('FG_VisualTopLip',(x,y,.57),(.32,.075,.05),metal,.009)
for side in [-1,1]:
 # Inset grasp surface and restrained tactile ribs, all independent editable objects.
 pad=box('FG_GripInlay',(-.35,side*.145,-.225),(.16,.026,.48),poly,.014);pad.rotation_euler.y=math.radians(-31)
 for i in range(7):
  t=i/6;x=-.445+t*.205;z=-.057-t*.35
  rib=box('FG_GripRib',(x,side*.164,z),(.15,.018,.023),poly,.007);rib.rotation_euler.y=math.radians(-31)
 for x,z,r in [(-.77,.27,.053),(-.48,.365,.038),(.59,.365,.038),(.84,.24,.033),(.115,-.53,.037)]:
  bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=r,depth=.018,location=(x,side*.15,z),rotation=(math.pi/2,0,0));finish(bpy.context.object,'FG_DecorativeFastener',metal,.004)
  bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=r*.40,depth=.003,location=(x,side*.161,z),rotation=(math.pi/2,0,0));finish(bpy.context.object,'FG_FastenerInset',dark,.001)
 # Chamfered accent on the forward diagonal support.
 bar=box('FG_SupportInset',(.49,side*.143,-.27),(.045,.014,.29),poly,.005);bar.rotation_euler.y=math.radians(39)
refcol=bpy.data.collections.new('5080_RAW_REFERENCE');S.collection.children.link(refcol)
if (P/'foregrip_raw.glb').exists():
 bpy.ops.import_scene.gltf(filepath=str(P/'foregrip_raw.glb'))
 for raw in list(bpy.context.selected_objects):
  for c in list(raw.users_collection):c.objects.unlink(raw)
  refcol.objects.link(raw)
 refcol.hide_render=True;refcol.hide_viewport=True
S.world=bpy.data.worlds.new('Neutral studio');S.world.use_nodes=True;S.world.node_tree.nodes['Background'].inputs[0].default_value=(.12,.14,.17,1);S.world.node_tree.nodes['Background'].inputs[1].default_value=.65
target=Vector((0,0,-.025))
def aim(o):o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(2.1,-4,1.65));cam=bpy.context.object;cam.name='PresentationCamera';cam.data.type='ORTHO';cam.data.ortho_scale=2.85;aim(cam);S.camera=cam
for name,loc,power,size in [('Key',(-2,-3,4),450,4),('Fill',(3,-1,1),240,3),('Rim',(1,3,3),650,3)]:
 bpy.ops.object.light_add(type='AREA',location=loc);l=bpy.context.object;l.name=name;l.data.energy=power;l.data.shape='DISK';l.data.size=size;aim(l)
S.render.engine='CYCLES';S.cycles.samples=32;S.cycles.use_denoising=True
S.render.resolution_x=1500;S.render.resolution_y=1000;S.render.resolution_percentage=100
S.view_settings.view_transform='AgX';S.render.image_settings.file_format='PNG';S.render.film_transparent=False
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AngledForegrip_M4_Editable.blend'))
bpy.ops.export_scene.fbx(filepath=str(P/'AngledForegrip_M4.fbx'),use_selection=True,object_types={'MESH'},add_leaf_bones=False,bake_anim=False,path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(P/'AngledForegrip_M4.glb'),use_selection=True,export_apply=True)
deps=bpy.context.evaluated_depsgraph_get();counts={}
for o in parts:
 ev=o.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();counts[o.name]=len(me.loop_triangles);ev.to_mesh_clear()
(P/'refinement_report.json').write_text(json.dumps({'triangles':sum(counts.values()),'objects':len(parts),'materials':[metal.name,poly.name],'source':source,'method':'5080 candidate retained; clean hard-surface frame rebuilt from concept silhouette, editable bevels and separate detail parts','counts':counts},indent=2))
for name,pos,scale in [('beauty',(2.1,-4,1.65),2.85),('side',(0,-5,0),2.5),('front',(-5,0,0),1.55),('top',(0,0,5),2.5)]:
 cam.location=pos;cam.data.ortho_scale=scale;aim(cam);S.render.filepath=str(P/(name+'.png'));bpy.ops.render.render(write_still=True)
print('FOREGRIP_REFINED_OK')
