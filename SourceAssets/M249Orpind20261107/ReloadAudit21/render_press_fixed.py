from pathlib import Path
import bpy,json,numpy as np
from mathutils import Vector
r=Path(__file__).resolve().parent;folder=r/'release/box_empty_base_right';meta=json.loads((folder/'geometry.json').read_text());j=json.loads((folder/'review.json').read_text());dom=np.fromfile(folder/'dominant.bin',np.uint32)
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('Review');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.25,.25,1)
def material(name,color):
 m=bpy.data.materials.new(name);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=.65;return m
skin=material('skin',(.6,.27,.13));metal=material('steel',(.1,.17,.24));optic=material('optic',(.2,.45,.6))
for source,side,title,slots in [(4.2,'r','feed_fixed',['M249_Factory_Cover','M249_Factory_Receiver','M249_OpticalHousing']),(4.5,'r','press_fixed',['M249_Factory_Cover','M249_Factory_Receiver','M249_OpticalHousing']),(4.8,'r','latch_fixed',['M249_Factory_Cover','M249_Factory_Receiver','M249_OpticalHousing'])]:
 for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
 row=min(j['frames'],key=lambda x:abs(x['source']-source));stem=folder/Path(row['file']).stem;v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);m=np.fromfile(stem.with_suffix('.materials'),np.uint32)
 hand=np.array([n.endswith('_'+side) and n.startswith(('hand','thumb','index','middle','ring','pinky')) for n in meta['bones']])[dom];hf=f[hand[f].all(1)];center=v[np.unique(hf)].mean(0)
 def mesh(name,faces,mat):
  ids,idx=np.unique(faces,return_inverse=True);data=bpy.data.meshes.new(name);data.from_pydata(v[ids].tolist(),[],idx.reshape(-1,3).tolist());data.materials.append(mat);ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
 mesh('hand',hf,skin)
 for slot in slots:mesh(slot,f[m==meta['slots'].index(slot)],optic if 'Optical' in slot else metal)
 for k,pos in enumerate([(15,-20,40),(-20,10,15)]):
  light=bpy.data.lights.new('light'+str(k),'AREA');light.energy=4500;light.shape='DISK';light.size=20;ob=bpy.data.objects.new('light'+str(k),light);scene.collection.objects.link(ob);ob.location=center+np.array(pos);ob.rotation_euler=(Vector(center)-ob.location).to_track_quat('-Z','Y').to_euler()
 cam=bpy.data.cameras.new('camera');ob=bpy.data.objects.new('camera',cam);scene.collection.objects.link(ob);ob.location=center+np.array([18,-24,18] if side=='r' else [-18,-24,18]);ob.rotation_euler=(Vector(center)-ob.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=20;scene.camera=ob;scene.render.filepath=str(r/(title+'_contact.png'));bpy.ops.render.render(write_still=True)
