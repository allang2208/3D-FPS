"""Source-mesh candidate views; final review also uses the runtime skin."""
import bpy,pickle,sys,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
ROOT=Path(__file__).resolve().parent
g=pickle.load(open(ROOT.parent/'Wrist33/geometry.pkl','rb'));names=g['names'];ix={n:i for i,n in enumerate(names)}
def matrix(v):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*v[7:];m[:3,3]=v[:3];return m
inv=np.linalg.inv(np.array([matrix(v) for v in g['bind']]))
v=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections']);dom=np.array([max(ws,key=lambda a:a[1])[0] for ws in g['weights']]);groups={}
for i,ws in enumerate(g['weights']):
    for b,weight in ws:
        ids,pts=groups.setdefault(b,([],[]));ids.append(i);pts.append(np.r_[v[i],1]*weight)
groups=[(b,np.array(ids),np.array(pts)) for b,(ids,pts) in groups.items()]
def skin(w):
    p=np.zeros_like(v);xf=w@inv
    for b,ids,pts in groups:p[ids]+=pts@xf[b,:3,:].T
    return p*np.array([1,-1,1])
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH'
scene.render.resolution_x=900;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('World');scene.world.color=(.075,.075,.075)
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True
def mat(name,col):
    m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);return m
skinmat=mat('Source skin',(.58,.34,.22));metal=mat('Gun',(.14,.19,.23));brass=mat('Belt',(.56,.38,.13))
def mesh(name,p,f,m):
    if not len(f):return
    ids,ind=np.unique(f,return_inverse=True);me=bpy.data.meshes.new(name);me.from_pydata(p[ids].tolist(),[],ind.reshape(-1,3).tolist());me.materials.append(m)
    for face in me.polygons:face.use_smooth=name=='Skin'
    ob=bpy.data.objects.new(name,me);scene.collection.objects.link(ob)
out=ROOT/'experiment_views';out.mkdir(exist_ok=True)
poses=pickle.load(open(ROOT/'experiment.pkl','rb'))
current=pickle.load(open(ROOT/'current_poses.pkl','rb'))
path=next(p for p in current['base'] if p.endswith('_reload'))
a=current['base'][path]
if 'right_belt' not in poses:poses['right_belt']=dict(before=a['world'][np.argmin(abs(a['times']-5.1))],time=5.1)
for name,data in poses.items():
    side='r' if name=='right_belt' else 'l';h=data['before'][ix['hand_'+side],:3,3]*[1,-1,1];e=data['before'][ix['lowerarm_'+side],:3,3]*[1,-1,1];center=h*.8+e*.2
    for state,w in data.items():
        if state=='time':continue
        p=skin(w)
        for angle,offset in [('side',[60,10,25]),('palm',[-60,-20,18])]:
            for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
            sk=np.array([s.startswith('Skin_') for s in g['slots']])[sections];sd=np.array([n.endswith('_'+side) for n in names])[dom]
            keep=np.array([not any(x in s for x in ('Glass','Reticle','NewBox','NewBelt')) for s in g['slots']])[sections]
            if name=='right_belt':keep=np.array([not any(x in s for x in ('Glass','Reticle','OldBox','OldBelt')) for s in g['slots']])[sections]
            belt=np.array(['Belt' in s for s in g['slots']])[sections]
            mesh('Skin',p,faces[sk&sd[faces].any(1)],skinmat);mesh('Gun',p,faces[~sk&keep&~belt],metal);mesh('Belt',p,faces[~sk&keep&belt],brass)
            cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);scene.collection.objects.link(co);scene.camera=co
            co.location=center+np.array(offset);co.rotation_euler=(Vector(center)-co.location).to_track_quat('-Z','Y').to_euler();cam.type='ORTHO';cam.ortho_scale=36;cam.clip_start=.1
            scene.render.filepath=str(out/f'{name}_{state}_{angle}.png');bpy.ops.render.render(write_still=True)
