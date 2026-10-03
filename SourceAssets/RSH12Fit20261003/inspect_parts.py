import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;B=O.parent/'RSH12Integration20261003'
raw=json.loads((B/'canonical_parts.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
colors={'4_l':(.2,.7,.2,1),'5_l':(.8,.35,.05,1),'6_l':(.25,.4,.8,1),'12_l':(.85,.05,.1,1),'13_l':(.9,.8,.1,1),'14_l':(.8,.1,.8,1)}
report={}
for part in raw:
 if part['name']=='10_l':continue
 verts=[Vector(v) for v in part['verts']]
 # Weld UV seams before identifying independent mechanical shells.
 lut={};groups=[];vmap={}
 for i,v in enumerate(verts):
  k=tuple(round(x,6) for x in v)
  if k not in lut:lut[k]=len(groups);groups.append([])
  j=lut[k];groups[j].append(i);vmap[i]=j
 adj=[set() for _ in groups]
 for f in part['faces']:
  ids=[vmap[i] for i in f]
  for i in ids:adj[i].update(ids)
 seen=set();shells=[]
 for i in range(len(groups)):
  if i in seen:continue
  stack=[i];seen.add(i);ids=[]
  while stack:
   j=stack.pop();ids.extend(groups[j])
   for k in adj[j]:
    if k not in seen:seen.add(k);stack.append(k)
  vv=[verts[k] for k in ids]
  shells.append(dict(ids=ids,min=[min(v[a] for v in vv) for a in range(3)],max=[max(v[a] for v in vv) for a in range(3)]))
 report[part['name']]=shells
 mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(verts,[],part['faces']);mesh.update()
 ob=bpy.data.objects.new(part['name'],mesh);bpy.context.collection.objects.link(ob)
 mat=bpy.data.materials.new(part['name']);mat.diffuse_color=colors.get(part['name'],(.38,.38,.38,1));mesh.materials.append(mat)
 for p in mesh.polygons:p.use_smooth=True
(O/'part_shells.json').write_text(json.dumps(report,indent=2))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=1000;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_cavity=True
scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('DiagnosticWorld');scene.world.color=(.15,.15,.15)
camdata=bpy.data.cameras.new('Diagnostic');cam=bpy.data.objects.new('Diagnostic',camdata);bpy.context.collection.objects.link(cam);scene.camera=cam
camdata.type='ORTHO';camdata.ortho_scale=.16
target=Vector((0,.065,.045))
for name,pos in [('right',( .38,.28,.14)),('rear',(.06,.45,.11)),('left',(-.38,.24,.13))]:
 cam.location=pos;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
 scene.render.filepath=str(O/(name+'_parts.png'));bpy.ops.render.render(write_still=True)
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_render=ob.name not in colors
cam.location=(.38,.25,.14);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'mechanical_parts.png');bpy.ops.render.render(write_still=True)
