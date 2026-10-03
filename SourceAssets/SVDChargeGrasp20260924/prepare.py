import bpy,json,ast,math
from pathlib import Path
from collections import Counter,defaultdict
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent;prev=json.loads((S/'SVDChargeGrip20260924/authoring.json').read_text())
tree=ast.parse((S/'SVDCompletion20260923/author_svd.py').read_text(encoding='utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sample'],type_ignores=[]),'<sample>','exec'))
info=prev['base/reload_empty'];bpy.ops.wm.open_mainfile(filepath=info['blend'],use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions[info['action']];s=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
poses=[sample(r,a,f) for f in range(516)]
ob=bpy.data.objects['SK_Manny_Arms_Export'];X=r.matrix_world.inverted()@ob.matrix_world
verts=[list(X@v.co) for v in ob.data.vertices];weights=[{ob.vertex_groups[g.group].name:g.weight for g in v.groups} for v in ob.data.vertices]
faces=[list(p.vertices) for p in ob.data.polygons];edges=Counter(tuple(sorted((p[i],p[(i+1)%len(p)]))) for p in faces for i in range(len(p)))
adj=defaultdict(set)
for (i,j),count in edges.items():
 if count==1:adj[i].add(j);adj[j].add(i)
remaining=set(adj);rings=[]
while remaining:
 group={remaining.pop()};queue=list(group)
 while queue:
  for j in adj[queue.pop()]:
   if j in remaining:remaining.remove(j);group.add(j);queue.append(j)
 totals=Counter()
 for i in group:
  for n,w in weights[i].items():totals[n]+=w/len(group)
 rings.append({'vertices':sorted(group),'weights':dict(totals)})
sample(r,a,0);parts={}
for name in ['SM_SVD_ChargingHandle','SM_SVD_Body']:
 mesh=bpy.data.objects[name];ev=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());inv=(r.matrix_world@poses[0]['WPN_root']).inverted()
 parts[name]={'vertices':[list(inv@ev.matrix_world@v.co) for v in ev.data.vertices],'faces':[list(f.vertices) for f in ev.data.polygons]}
data={'rest':{n:list(map(list,m)) for n,m in rest.items()},'parents':parents,'poses':[{n:list(map(list,m)) for n,m in p.items()} for p in poses],
 'skin':{'vertices':verts,'weights':weights,'faces':faces,'boundaries':rings},'parts':parts,'rig_world':list(map(list,r.matrix_world))}
(O/'inputs.json').write_text(json.dumps(data))
print('SVD_GRASP_SOURCE',len(verts),'boundaries',[(len(x['vertices']),x['weights']) for x in rings],flush=True)
# Requested before views with visible backface culling: no double-sided fill.
for mesh in s.objects:
 if mesh.type=='MESH':
  mesh.hide_render=not any(m.type=='ARMATURE' and m.object==r for m in mesh.modifiers)
  mesh.color=(.55,.63,.70,1) if mesh==ob else (.20,.23,.27,1)
cam=bpy.data.objects.new('ChargeReview',bpy.data.cameras.new('ChargeReview'));s.collection.objects.link(cam);s.camera=cam
cam.location=(0,-.10,.05);cam.rotation_euler=(math.pi/2,0,0);cam.data.clip_start=.005
cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75/2)))
s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_backface_culling=True
s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD'
if not s.world:s.world=bpy.data.worlds.new('ReviewWorld')
s.world.color=(.055,.065,.08);s.render.resolution_x=880;s.render.resolution_y=495;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
out=O/'Review';out.mkdir(exist_ok=True)
for f in [268,288,310,330,344,360,396,432]:
 sample(r,a,f);s.render.filepath=str(out/f'before_fp_{f}.png');bpy.ops.render.render(write_still=True)
sample(r,a,330);target=r.matrix_world@r.pose.bones['hand_r'].matrix.translation
cam.location=target+Vector((.24,-.25,.16));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.36
s.render.filepath=str(out/'before_grasp_330.png');bpy.ops.render.render(write_still=True)
print('SVD_GRASP_BEFORE_READY',flush=True)
