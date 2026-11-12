"""Offline candidate only. Final acceptance uses the native rendered game."""
import bpy,pickle,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
root=Path(__file__).resolve().parent;g=pickle.load(open(root.parent/'Wrist33/geometry.pkl','rb'));poses=pickle.load(open(root/'preview_poses.pkl','rb'))
def matrix(v):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*np.array(v[7:]);m[:3,3]=v[:3];return m
inverse=np.linalg.inv(np.array([matrix(v) for v in g['bind']]));vertices=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections']);groups={}
for i,ws in enumerate(g['weights']):
    for b,w in ws:
        ids,pts=groups.setdefault(b,([],[]));ids.append(i);pts.append(np.r_[vertices[i],1]*w)
groups=[(b,np.array(ids),np.array(pts)) for b,(ids,pts) in groups.items()]
left=np.array([max(ws,key=lambda x:x[1])[0] for ws in g['weights']]);left=np.array([n.endswith('_l') for n in g['names']])[left]
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=960;scene.render.resolution_y=540;scene.render.resolution_percentage=100;scene.world=bpy.data.worlds.new('World');scene.world.color=(.16,.16,.16)
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
def mat(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
skin=mat('Source skin',(.58,.34,.22));metal=mat('Gun',(.12,.17,.20))
def mesh(name,p,f,m):
    ids,ind=np.unique(f,return_inverse=True);data=bpy.data.meshes.new(name);data.from_pydata(p[ids].tolist(),[],ind.reshape(-1,3).tolist());data.materials.append(m)
    for face in data.polygons:face.use_smooth=name=='Skin'
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob)
out=root/'preview';out.mkdir(exist_ok=True)
for path,data in poses.items():
    empty=path.endswith('_empty')
    for time in ([1.75,3.,4.85] if empty else [2.6,3.,5.95]):
        k=np.argmin(abs(data['times']-time))
        for state in ['before','after']:
            w=data[state][k];p=np.zeros_like(vertices);xf=w@inverse
            for b,ids,pts in groups:p[ids]+=pts@xf[b,:3,:].T
            eye=data['cameras'][k];p=(p@eye[:3,:3].T+eye[:3,3])*[1,-1,1]
            for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
            sk=np.array([n.startswith('Skin_') for n in g['slots']])[sections]
            keep=np.array([not any(s in n for s in ('NewBox','NewBelt','Glass','Reticle','Factory_Foregrip')) for n in g['slots']])[sections]
            mesh('Skin',p,faces[sk&left[faces].any(1)],skin);mesh('Gun',p,faces[~sk&keep],metal)
            cam=bpy.data.cameras.new('Player');obj=bpy.data.objects.new('Player',cam);scene.collection.objects.link(obj);scene.camera=obj
            obj.rotation_euler=Vector((1,0,0)).to_track_quat('-Z','Y').to_euler();cam.type='PERSP';cam.sensor_fit='HORIZONTAL';cam.angle=np.radians(107.512367);cam.clip_start=1
            scene.render.filepath=str(out/f'{"empty" if empty else "normal"}_{time:.2f}_{state}.png');bpy.ops.render.render(write_still=True)
