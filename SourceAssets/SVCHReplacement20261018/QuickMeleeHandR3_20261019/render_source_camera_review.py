"""Both bare V9 and glove surfaces, at the player view and a close hand view."""
from pathlib import Path
import sys,json,gzip,bpy,numpy as np
from mathutils import Vector
O=Path(__file__).resolve().parent
data=json.load(gzip.open(O/'review-source-camera-meshes.json.gz','rt'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=16
sc.render.resolution_x=1000;sc.render.resolution_y=560;sc.render.resolution_percentage=100
sc.world=bpy.data.worlds.new('World');sc.world.use_nodes=True;sc.world.node_tree.nodes.get('Background').inputs['Color'].default_value=(.25,.28,.31,1)
sc.world.node_tree.nodes.get('Background').inputs['Strength'].default_value=.8;sc.view_settings.view_transform='AgX'
def mat(n,col):
    m=bpy.data.materials.new(n);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*col,1);b.inputs['Roughness'].default_value=.5;return m
skin=mat('V9',(.62,.35,.22));mats={'coverage':skin,'bare':skin,'glove':mat('Glove',(.015,.035,.17)),'gun':mat('Gun',(.05,.06,.07))}
obs={}
for name,tris in data['triangles'].items():
    m=bpy.data.meshes.new(name);m.from_pydata(data['frames']['20']['R2'][name],[],[list(reversed(t)) for t in tris]);m.update()
    ob=bpy.data.objects.new(name,m);sc.collection.objects.link(ob);m.materials.append(mats[name]);obs[name]=ob
    for poly in m.polygons:poly.use_smooth=True
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);sc.collection.objects.link(cam);sc.camera=cam
camdata.lens_unit='FOV';camdata.sensor_fit='VERTICAL';camdata.clip_start=.05;camdata.clip_end=1000
for name,pos,e,size in [('Key',(0,-20,60),90000,60),('Fill',(-50,20,0),50000,50)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=e;d.shape='DISK';d.size=size;ob=bpy.data.objects.new(name,d);sc.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=(Vector((0,25,0))-ob.location).to_track_quat('-Z','Y').to_euler()
out=O/'SourceCameraReview';out.mkdir(exist_ok=True)
only=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['20','68']
def convert(v):
    a=np.array(v);return np.stack([a[...,0],10-a[...,1],a[...,2]-5],axis=-1)
for fi in only:
    rows=data['frames'][fi]
    for key,meshes in rows.items():
        if key=='R2':continue
        if key=='R2' and all((out/(fi+'-'+key+'-'+mode+'-'+view+'.png')).exists() for mode in ['bare','glove'] for view in ['player','hand']):continue
        for name in obs:obs[name].data.vertices.foreach_set('co',convert(meshes[name]).ravel());obs[name].data.update()
        for mode in ['bare','glove']:
            if fi=='70' and mode=='glove':continue
            obs['bare'].hide_render=mode!='bare';obs['coverage'].hide_render=obs['glove'].hide_render=mode!='glove'
            for view in (['elbow'] if fi=='70' else ['player','hand']):
                if view=='player':
                    cam.location=(0,0,0);cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler();camdata.angle=np.radians(data['camera_vertical_fov'])
                else:
                    h=Vector(convert(meshes['bones']['hand_r']));tip=Vector(convert(meshes['bones']['middle_03_r']));focus=(h+tip)*.5
                    if view=='elbow':focus=Vector(convert(meshes['bones']['lowerarm_r']))
                    cam.location=focus+Vector((16,-25,8));cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.angle=np.radians(35)
                if view=='elbow':
                    upper=Vector(convert(meshes['bones']['upperarm_r']));hand=Vector(convert(meshes['bones']['hand_r']))
                    a=(upper-focus).normalized();b=(hand-focus).normalized();normal=a.cross(b).normalized()
                    if normal.dot(-focus)<0:normal=-normal
                    cam.location=focus+normal*32+(a+b).normalized()*7
                    cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();camdata.angle=np.radians(55)
                sc.render.filepath=str(out/(fi+'-'+key+'-'+mode+'-'+view+'.png'));bpy.ops.render.render(write_still=True)
