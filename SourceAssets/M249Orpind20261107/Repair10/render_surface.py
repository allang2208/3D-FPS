"""Requested diagnostic views of the saved pose and both articulated legs."""
import bpy,pickle,numpy as np,sys
from pathlib import Path
from mathutils import Vector
r=Path(__file__).resolve().parent;label=next((a.split('=',1)[1] for a in sys.argv if a.startswith('--label=')),'before');g=pickle.load(open(r/'geometry.pkl','rb'));samples=pickle.load(open(r/(label+'_surface.pkl'),'rb'))
out=r/(label+'Views');out.mkdir(exist_ok=True);bpy.ops.wm.read_factory_settings(use_empty=True)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=16;s.cycles.use_denoising=True
s.render.resolution_x=1100;s.render.resolution_y=800;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs[0].default_value=(.13,.16,.21,1)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.55;return m
skin=material('V9 diagnostic skin',(.52,.27,.17));gun=material('Factory parts',(.07,.09,.11));metal=material('Articulated legs',(.15,.18,.21))
f=np.array(g['faces']);sec=np.array(g['sections']);keep=np.array([i!=10 and '__New' not in n for i,n in enumerate(g['slots'])])[sec]
mesh=bpy.data.meshes.new('Native skin');mesh.from_pydata(g['vertices'],[],f[keep].tolist());obj=bpy.data.objects.new('M249',mesh);bpy.context.collection.objects.link(obj)
mesh.materials.append(gun);mesh.materials.append(skin);mesh.polygons.foreach_set('material_index',np.isin(sec[keep],[7,8,9]).astype(int));mesh.polygons.foreach_set('use_smooth',np.ones(len(mesh.polygons),bool))
legs={}
for n,(v,fs) in next(iter(samples.values()))['legs'].items():
    me=bpy.data.meshes.new(n);me.from_pydata(v.tolist(),[],fs.tolist());ob=bpy.data.objects.new(n,me);bpy.context.collection.objects.link(ob);me.materials.append(metal);legs[n]=ob
for loc,energy,size in [((-60,-10,100),180000,90),((40,-90,35),120000,70),((60,60,50),140000,70)]:
    light=bpy.data.lights.new('softbox','AREA');light.energy=energy;light.shape='DISK';light.size=size;ob=bpy.data.objects.new('softbox',light);bpy.context.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(-ob.location).to_track_quat('-Z','Y').to_euler()
camdata=bpy.data.cameras.new('left review');cam=bpy.data.objects.new('left review',camdata);bpy.context.collection.objects.link(cam);s.camera=cam
camdata.type='ORTHO';camdata.ortho_scale=80;camdata.clip_end=1000;cam.location=(-80,-60,36);cam.rotation_euler=(Vector((0,-20,-15))-cam.location).to_track_quat('-Z','Y').to_euler()
for t in ((0,) if label=='hold' else (0,.116667,.216667,.3,.35,.433333)):
    k=min(samples,key=lambda k:abs(float(k)-t));p=samples[k];mesh.vertices.foreach_set('co',p['vertices'].astype(np.float32).ravel());mesh.update()
    for n,ob in legs.items():ob.data.vertices.foreach_set('co',p['legs'][n][0].astype(np.float32).ravel());ob.data.update()
    s.render.filepath=str(out/f'left_{float(k):.4f}.png');bpy.ops.render.render(write_still=True)
print('BIPOD_DIAGNOSTIC_VIEWS_SAVED',flush=True)
