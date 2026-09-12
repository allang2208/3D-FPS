import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.obj_import(filepath=str(O/'Source/model/Final test.obj'))
s=bpy.context.scene
meshes=[o for o in s.objects if o.type=='MESH']
report=[]
for o in meshes:
 for slot in o.material_slots:
  m=slot.material;m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
  prefix='Magazine_Material.001' if '001' in m.name else 'QBZ_DefaultMaterial'
  for kind,pin in [('BaseColor','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Normal','Normal')]:
   t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O/'Source/textures'/f'{prefix}_{kind}.png'))
   if kind!='BaseColor':t.image.colorspace_settings.name='Non-Color'
   if kind=='Normal':nm=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs[pin])
   else:l.new(t.outputs['Color'],bs.inputs[pin])
 adj=[set() for _ in o.data.vertices]
 for e in o.data.edges:
  a,b=e.vertices;adj[a].add(b);adj[b].add(a)
 seen=set();comps=[]
 for v in range(len(adj)):
  if v in seen:continue
  todo=[v];seen.add(v);ids=[]
  while todo:
   a=todo.pop();ids.append(a)
   for b in adj[a]:
    if b not in seen:seen.add(b);todo.append(b)
  pts=[o.matrix_world@o.data.vertices[i].co for i in ids]
  lo=[min(v[j] for v in pts) for j in range(3)];hi=[max(v[j] for v in pts) for j in range(3)]
  comps.append({'ids':ids,'vertices':len(ids),'min':lo,'max':hi})
 report.append({'name':o.name,'matrix':[list(row) for row in o.matrix_world],'materials':[x.name for x in o.data.materials],'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'components':comps})
(O/'components.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SourceInspect.blend'))
s.render.engine='CYCLES';s.cycles.samples=24;s.render.resolution_x=1400;s.render.resolution_y=700;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('World');s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.14,.16,.20,1)
pts=[o.matrix_world@v.co for o in meshes for v in o.data.vertices];center=sum(pts,Vector())/len(pts)
bpy.ops.object.camera_add(location=center+Vector((1.4,-.1,.25)));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.95;s.camera=cam
for loc,power,size in [((1,-.3,1.4),180,2),((-.8,-.2,.8),120,1.5),((.5,1,.4),80,1)]:
 bpy.ops.object.light_add(type='AREA',location=loc);li=bpy.context.object;li.data.energy=power;li.data.shape='DISK';li.data.size=size;li.rotation_euler=(center-li.location).to_track_quat('-Z','Y').to_euler()
s.render.filepath=str(O/'source-side.png');bpy.ops.render.render(write_still=True)
print('QBZ_INSPECT_COMPLETE',[(x['name'],x['vertices'],len(x['components'])) for x in report])
