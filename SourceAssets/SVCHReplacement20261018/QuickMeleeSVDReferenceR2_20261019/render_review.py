"""Read-only diagnostic frames in the rifle action camera, without running UE."""
from pathlib import Path
import json,gzip,sys
import bpy,numpy as np
from mathutils import Vector
O=Path(__file__).resolve().parent
data=json.load(gzip.open(O/'review-meshes.json.gz','rt'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16
sc.render.resolution_x=1000;sc.render.resolution_y=420;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('World');sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.3,.3,.3,1)
sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.8
sc.view_settings.view_transform='AgX'
def mat(name,col,rough):
    m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=rough;return m
mats={'coverage':mat('V9',(.62,.34,.2),.54),'glove':mat('Blue glove',(.015,.035,.2),.45),'gun':mat('Gun',(.045,.055,.07),.4)}
obs={}
for name,tris in data['triangles'].items():
    coords=data['frames']['20']['rejected'][name];m=bpy.data.meshes.new(name);m.from_pydata(coords,[],[list(reversed(t)) for t in tris]);m.update()
    ob=bpy.data.objects.new(name,m);sc.collection.objects.link(ob);m.materials.append(mats[name]);obs[name]=ob
    for poly in m.polygons:poly.use_smooth=True
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);sc.collection.objects.link(cam);sc.camera=cam
cam.location=(0,0,0);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();camdata.lens_unit='FOV';camdata.sensor_fit='VERTICAL';camdata.angle=np.radians(75);camdata.clip_start=.1;camdata.clip_end=1000
for name,pos,e,size in [('Key',(0,-20,60),90000,60),('Fill',(-50,20,0),40000,50)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=e;d.shape='DISK';d.size=size;ob=bpy.data.objects.new(name,d);sc.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,25,0))-ob.location).to_track_quat('-Z','Y').to_euler()
out=O/'Review';out.mkdir(exist_ok=True)
only=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
for fi,rows in data['frames'].items():
    if only and fi not in only:continue
    for key,meshes in rows.items():
        for name,v in meshes.items():
            # UE mesh -> camera: yaw +90, action translation (10,0,-5).
            # Blender camera axes: +X right, +Y forward, +Z up.
            vv=np.array(v);vv=np.c_[vv[:,0],10-vv[:,1],vv[:,2]-5]
            obs[name].data.vertices.foreach_set('co',vv.ravel());obs[name].data.update()
        sc.render.filepath=str(out/(fi+'-'+key+'.png'));bpy.ops.render.render(write_still=True)
