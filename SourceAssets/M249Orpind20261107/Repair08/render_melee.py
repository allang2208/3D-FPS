"""Requested right-arm diagnostic: native saved surface and original/corrected poses."""
import bpy,pickle,numpy as np,sys
import math
from pathlib import Path
from mathutils import Quaternion,Vector
r=Path(__file__).resolve().parent;out=r/'MeleeReview';out.mkdir(exist_ok=True)
def mat(t):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((t[6],*t[3:6])).to_matrix())*t[7:];m[:3,3]=t[:3];return m
g=pickle.load(open(r.parent/'Repair06/geometry.pkl','rb'));vertices=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections'])
bind=np.array([mat(t) for t in g['bind']]);indices={}
for i,weights in enumerate(g['weights']):
    for bone,weight in weights:indices.setdefault(bone,[]).append((i,weight))
groups=[]
for b,rows in indices.items():
    ids,w=np.array(rows).T;ids=ids.astype(int);groups.append((b,ids,np.c_[vertices[ids],np.ones(len(ids))]*w[:,None]))
bpy.ops.wm.read_factory_settings(use_empty=True)
mesh=bpy.data.meshes.new('Native M249 V9 surface');mesh.from_pydata(vertices.tolist(),[],faces.tolist());obj=bpy.data.objects.new('Native M249 V9 surface',mesh);bpy.context.collection.objects.link(obj)
for i,name in enumerate(g['slots']):
    material=bpy.data.materials.new(name);material.use_nodes=True;p=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(.5,.28,.18,1) if i in (7,8,9) else (.065,.075,.085,1)
    p.inputs['Roughness'].default_value=.62;mesh.materials.append(material)
mesh.polygons.foreach_set('material_index',sections);mesh.polygons.foreach_set('use_smooth',np.ones(len(faces),dtype=bool))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=16;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=760;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Review studio');scene.world.use_nodes=True
next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND').inputs[0].default_value=(.2,.2,.2,1)
for pos,power in (((75,40,100),230000),((-80,-20,50),160000)):
    data=bpy.data.lights.new('Light','AREA');data.energy=power;data.size=100
    light=bpy.data.objects.new('Light',data);bpy.context.collection.objects.link(light);light.location=pos;light.rotation_euler=(-light.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Right arm');cam=bpy.data.objects.new('Right arm',data);bpy.context.collection.objects.link(cam);scene.camera=cam;data.type='ORTHO';data.ortho_scale=82;data.clip_end=1000
cam.location=(85,30,35);cam.rotation_euler=(Vector((0,0,-8))-cam.location).to_track_quat('-Z','Y').to_euler()
player='--player' in sys.argv
if player:
    data.type='PERSP';data.angle=math.radians(107.5);data.clip_start=1.
    cam.location=(-9,9,11);cam.rotation_euler=Vector((0,-1,0)).to_track_quat('-Z','Y').to_euler()
    scene.render.resolution_x=1280;scene.render.resolution_y=720
for label,file in [('before','COMPRESSED_quick_melee.pkl'),('candidate','candidate_world.pkl')]:
    src=pickle.load(open(r/file,'rb'));lookup={n:i for i,n in enumerate(src['names'])}
    for t in (.1125,.17,.34,.72):
        row=src['frames'][round(t*src['fps'])];world=np.array([mat(row[lookup[n]]) for n in g['names']]);xf=world@np.linalg.inv(bind)
        points=np.zeros_like(vertices)
        for bone,ids,co in groups:points[ids]+=co@xf[bone,:3,:].T
        hidden=np.unique(faces[np.array(['__New' in n for n in g['slots']])[sections]])
        points[hidden]=[0,0,-1000];mesh.vertices.foreach_set('co',points.astype(np.float32).ravel());mesh.update()
        scene.render.filepath=str(out/(f'{label}_{round(t*10000)}'+('_player' if player else '')+'.png'));bpy.ops.render.render(write_still=True)
print('M249_RIGHT_ARM_REVIEW_RENDERED',flush=True)
