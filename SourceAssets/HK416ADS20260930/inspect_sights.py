"""User-requested sight diagnosis: source landmarks and current ADS sight picture."""
import bpy,json,math,ast
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930';A=json.loads((S/'authoring.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(S/'HK416_Gameplay_Editable.blend'))
transform=Matrix(A['source_to_weapon_root']).inverted()@Matrix(A['root_matrix']).inverted()
objects=[]
for ob in list(bpy.context.scene.objects):
    if ob.type!='MESH' or ob.name not in A['source_parts'] or A['source_parts'][ob.name]['role']!='body':
        bpy.data.objects.remove(ob,do_unlink=True);continue
    ob.modifiers.clear();ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.data.transform(transform)
    ob.hide_render=False;ob.hide_set(False);objects.append(ob)
sight=bpy.data.objects['ironsight_low'];mesh=sight.data
adj=[set() for _ in mesh.vertices]
for e in mesh.edges:
    a,b=e.vertices;adj[a].add(b);adj[b].add(a)
left=set(range(len(mesh.vertices)));components=[]
while left:
    seed=next(iter(left));ids={seed};todo=[seed];left.remove(seed)
    while todo:
        for j in adj[todo.pop()]&left:left.remove(j);ids.add(j);todo.append(j)
    pts=[mesh.vertices[i].co for i in ids];lo=[min(p[a] for p in pts) for a in range(3)];hi=[max(p[a] for p in pts) for a in range(3)]
    components.append({'seed':seed,'vertices':len(ids),'min':lo,'max':hi})
components.sort(key=lambda x:x['min'][1])
(O/'sight_geometry.json').write_text(json.dumps({'components':components,'vertices':[list(v.co) for v in mesh.vertices],'triangles':[list(f.vertices) for f in mesh.polygons]},indent=2))
print('SIGHT_COMPONENTS',json.dumps(components),flush=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world=bpy.data.worlds.new('DiagnosticBackdrop');scene.world.use_nodes=True
bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs[0].default_value=(.45,.5,.56,1);bg.inputs[1].default_value=.8
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=.5
for name,p in [('Left',(-.1,-.035,.14)),('Right',(.09,.035,.1))]:
    light=bpy.data.lights.new(name,'AREA');light.energy=4;light.shape='DISK';light.size=.09
    ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=p;ob.rotation_euler=(Vector((0,0,.025))-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.objects.new('SightCamera',bpy.data.cameras.new('SightCamera'));scene.collection.objects.link(cam);scene.camera=cam
cam.data.clip_start=.00001;cam.data.clip_end=5;cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=12/math.tan(math.radians(55)/2)
cam.location=(0,-.0246-.18/4,.03455);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'ads_before.png');bpy.ops.render.render(write_still=True)
for ob in objects:ob.hide_render=ob!=sight
cam.data.type='ORTHO';cam.data.ortho_scale=.025;cam.location=(0,-.07,.029);scene.render.filepath=str(O/'rear_front_elevation.png');bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'Sight_Diagnosis.blend'))
