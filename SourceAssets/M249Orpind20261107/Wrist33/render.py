import bpy,pickle,numpy as np,sys
from pathlib import Path
from mathutils import Vector,Quaternion
r=Path(__file__).resolve().parent;label=sys.argv[-1]
g=pickle.load(open(r/'geometry.pkl','rb'));views=pickle.load(open(r/(label+'_views.pkl'),'rb'))
def mat(v):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*np.array(v[7:]);m[:3,3]=v[:3];return m
B=np.array([mat(v) for v in g['bind']]);ib=np.linalg.inv(B);ix={n:i for i,n in enumerate(g['names'])}
v=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections']);groups={}
for i,ws in enumerate(g['weights']):
    for b,w in ws:
        ids,points=groups.setdefault(b,([],[]));ids.append(i);points.append(np.r_[v[i],1]*w)
groups=[(b,np.array(ids),np.array(points)) for b,(ids,points) in groups.items()]
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.render.resolution_x=800;s.render.resolution_y=650;s.render.resolution_percentage=100
s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.world=bpy.data.worlds.new('Review');s.world.color=(.075,.075,.075)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
skin=material('Skin',(.58,.34,.22));metal=material('Gun',(.14,.19,.23))
keep=np.array([not any(k in n for k in ('NewBox','NewBelt','Glass','Reticle')) for n in g['slots']])[sections]
f=faces[keep];sec=sections[keep];colors=np.array([1 if n.startswith('Skin_') else 0 for n in g['slots']])[sec]
data=bpy.data.meshes.new('Actual skin');data.from_pydata(v.tolist(),[],f.tolist());data.materials.append(metal);data.materials.append(skin);data.polygons.foreach_set('material_index',colors);data.polygons.foreach_set('use_smooth',np.ones(len(f),bool));ob=bpy.data.objects.new('M249',data);s.collection.objects.link(ob)
cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);s.collection.objects.link(co);s.camera=co;cam.type='ORTHO';cam.ortho_scale=37;cam.clip_start=.1;cam.clip_end=1000
out=r/(label+'_views');out.mkdir(exist_ok=True)
for key,w in views.items():
    p=np.zeros_like(v);xf=w@ib
    for b,ids,pts in groups:p[ids]+=pts@xf[b,:3,:].T
    # One reflection maps UE handedness into Blender; preserve triangle order.
    p*=np.array([1,-1,1]);data.vertices.foreach_set('co',p.astype(np.float32).ravel());data.update()
    hand=w[ix['hand_l'],:3,3]*[1,-1,1];elbow=w[ix['lowerarm_l'],:3,3]*[1,-1,1];target=hand*.7+elbow*.3
    co.location=target+np.array([-50,5,22]);co.rotation_euler=(Vector(target)-co.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(out/(key+'.png'));bpy.ops.render.render(write_still=True)
