from pathlib import Path
import sys,json,gzip,bpy,numpy as np
from mathutils import Vector
O=Path(__file__).resolve().parent;data=json.load(gzip.open(O/'review-meshes.json.gz','rt'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=12
sc.render.resolution_x=1000;sc.render.resolution_y=560;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('World');sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.25,.28,.31,1)
sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.8;sc.view_settings.view_transform='AgX'
obs={}
for n,tris in data['triangles'].items():
    first=next(iter(next(iter(data['frames'].values())).values()))
    m=bpy.data.meshes.new(n);m.from_pydata(first[n],[],[list(reversed(t)) for t in tris]);m.update()
    ob=bpy.data.objects.new(n,m);sc.collection.objects.link(ob);obs[n]=ob
    mat=bpy.data.materials.new(n);mat.use_nodes=True;b=mat.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*((.62,.35,.22) if n=='bare' else (.05,.06,.07)),1);b.inputs['Roughness'].default_value=.5;m.materials.append(mat)
    for poly in m.polygons:poly.use_smooth=True
cd=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',cd);sc.collection.objects.link(cam);sc.camera=cam
cd.lens_unit='FOV';cd.sensor_fit='VERTICAL';cd.clip_start=.05;cd.clip_end=1000;cd.angle=np.radians(75)
cam.location=(0,0,0);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
for n,pos,e,size in [('Key',(0,-20,60),90000,60),('Fill',(-50,20,0),50000,50)]:
    d=bpy.data.lights.new(n,'AREA');d.energy=e;d.shape='DISK';d.size=size;ob=bpy.data.objects.new(n,d);sc.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,25,0))-ob.location).to_track_quat('-Z','Y').to_euler()
out=O/'Review';out.mkdir(exist_ok=True)
only=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['84','90','94','96','98','102','108']
for fi in only:
    for label,meshes in data['frames'][fi].items():
        for n,ob in obs.items():ob.data.vertices.foreach_set('co',np.array(meshes[n]).ravel());ob.data.update()
        sc.render.filepath=str(out/f'{fi}-{label}-player.png');bpy.ops.render.render(write_still=True)
