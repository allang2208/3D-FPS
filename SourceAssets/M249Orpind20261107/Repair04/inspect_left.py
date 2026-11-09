from pathlib import Path
import pickle
import bpy
import numpy as np
from mathutils import Quaternion,Vector
root=Path(__file__).resolve().parent
project=root.parents[2]
d=pickle.load(open(project/'Saved/M249ReloadReview/geometry.pkl','rb'))
def mat(t):
    m=np.eye(4);m[:3,:3]=np.asarray(Quaternion((t[6],*t[3:6])).to_matrix())*t[7:];m[:3,3]=t[:3];return m
bind=np.asarray([mat(t) for t in d['bind']]);vertices=np.asarray(d['vertices']);faces=np.asarray(d['faces'])
lookup=dict(zip(d['used'],range(len(d['names']))));indices={}
for i,row in enumerate(d['weights']):
    for b,w in row:indices.setdefault(lookup[b],[]).append((i,w))
skin=[]
for b,pairs in indices.items():
    ids,weight=np.asarray(pairs).T;ids=ids.astype(int)
    skin.append((b,ids,np.c_[vertices[ids],np.ones(len(ids))]*weight[:,None]))
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('Left contact');mesh.from_pydata(vertices.tolist(),[],faces.tolist())
obj=bpy.data.objects.new('Left contact',mesh);bpy.context.collection.objects.link(obj)
for name in d['slots']:
    m=bpy.data.materials.new(name);m.diffuse_color=(.52,.30,.18,1) if name.startswith('Skin') else (.1,.25,.32,1) if 'Belt' in name else (.18,.2,.22,1)
    mesh.materials.append(m)
mesh.polygons.foreach_set('material_index',d['sections']);mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),bool))
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=600;scene.render.resolution_y=600;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.background_type='WORLD';scene.world=bpy.data.worlds.new('World');scene.world.color=(.12,.12,.12)
data=bpy.data.cameras.new('Left');cam=bpy.data.objects.new('Left',data);bpy.context.collection.objects.link(cam);scene.camera=cam
data.type='ORTHO';data.ortho_scale=58;data.clip_end=1000
cam.location=(-80,-32,24);cam.rotation_euler=(Vector((0,-25,-5))-cam.location).to_track_quat('-Z','Y').to_euler()
import sys
stage='after' if '--after' in sys.argv else 'before'
folder=root if stage=='after' else root.parent/'Repair03'
for role,times in [('reload',(.40,.50,.60,2.05,2.20,2.35)),('reload_empty',(1.30,1.45,1.60))]:
    world=np.load(folder/(role+'_world.npz'))
    for t in times:
        i=round(t*120);transforms=np.asarray([world[n][i] for n in d['names']])@np.linalg.inv(bind)
        points=np.zeros_like(vertices)
        for b,ids,coords in skin:points[ids]+=coords@transforms[b,:3,:].T
        hidden=np.unique(faces[np.asarray(['__New' in d['slots'][m] for m in d['sections']])]);points[hidden]=[0,0,-1000]
        mesh.vertices.foreach_set('co',points.astype(np.float32).ravel());mesh.update()
        scene.render.filepath=str(root/f'{stage}_{role}_{t:.2f}.png');bpy.ops.render.render(write_still=True)
