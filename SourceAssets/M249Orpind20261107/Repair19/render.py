"""Diagnostic left-side views from actual native skin and saved magazine meshes."""
import bpy,sys,pickle,numpy as np
from pathlib import Path
from mathutils import Vector
r=Path(__file__).resolve().parent;label=next((s.split('=')[1] for s in sys.argv if s.startswith('--label=')),'before')
d=pickle.load(open(r/(label+'_surfaces.pkl'),'rb'));out=r/(label+'_views');out.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True
s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('Review');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs[0].default_value=(.18,.20,.23,1)
def mat(name,col):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*col,1);p.inputs['Roughness'].default_value=.65;return m
gun=mat('Gun',(.055,.065,.075));skin=mat('Skin',(.51,.27,.17));shell=mat('Magazine',(.23,.25,.26))
def mesh(name,vertices,faces,material):
    me=bpy.data.meshes.new(name);me.from_pydata(vertices,[],faces);me.update();ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material);return ob
sample=next(iter(d['samples'].values()));ob=mesh('NativeM249',sample['vertices'].tolist(),d['faces'].tolist(),gun);ob.data.materials.append(skin);ob.data.polygons.foreach_set('material_index',d['materials']);ob.data.polygons.foreach_set('use_smooth',np.ones(len(d['faces']),bool))
for loc,power,size in [((60,-30,60),180000,75),((0,45,60),100000,60),((-45,0,40),120000,60)]:
    ld=bpy.data.lights.new('softbox','AREA');ld.energy=power;ld.size=size;lo=bpy.data.objects.new('softbox',ld);bpy.context.collection.objects.link(lo);lo.location=loc;lo.rotation_euler=(Vector((10,7,0))-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('left');co=bpy.data.objects.new('left',cd);bpy.context.collection.objects.link(co);s.camera=co;cd.type='ORTHO';cd.ortho_scale=48;cd.clip_end=1000;co.location=(83,-33,29);co.rotation_euler=(Vector((10,7,-2))-co.location).to_track_quat('-Z','Y').to_euler()
parts=[]
for name,p in d['samples'].items():
    if name.startswith('30_') and name not in ('30_0.72','30_2.70'):continue
    if name.startswith('45_') and float(name.split('_')[1]) not in (0,.46,.60,.72,.93,1.84,2.22,2.55,2.70,2.85,2.98,3.18,3.42,3.62,3.8):continue
    ob.data.vertices.foreach_set('co',p['vertices'].astype(np.float32).ravel());ob.data.update()
    for part in parts:bpy.data.objects.remove(part,do_unlink=True)
    parts=[mesh(k,v['vertices'].tolist(),v['faces'].tolist(),shell) for k,v in p['parts'].items()]
    s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
print('SIDE_MAG_DIAGNOSTIC_VIEWS_SAVED',label,flush=True)
