"""Joint-only candidate comparison, plain skinning; final UE morph review remains required."""
import bpy,pickle,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion
r=Path(__file__).resolve().parent;s=r.parent/'Wrist33'
g=pickle.load(open(s/'geometry.pkl','rb'));poses=pickle.load(open(r/'hold_poses.pkl','rb'))
def matrix(v):
    m=np.eye(4);m[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*np.array(v[7:]);m[:3,3]=v[:3];return m
B=np.array([matrix(v) for v in g['bind']]);ib=np.linalg.inv(B);ix={n:i for i,n in enumerate(g['names'])}
v=np.array(g['vertices']);faces=np.array(g['faces']);sections=np.array(g['sections']);groups={}
for i,ws in enumerate(g['weights']):
    for b,w in ws:
        ids,points=groups.setdefault(b,([],[]));ids.append(i);points.append(np.r_[v[i],1]*w)
groups=[(b,np.array(ids),np.array(points)) for b,(ids,points) in groups.items()]
dominant=np.array([max(ws,key=lambda p:p[1])[0] for ws in g['weights']]);left=np.array([n.endswith('_l') for n in g['names']])[dominant]
bpy.ops.wm.read_factory_settings(use_empty=True);scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_x=900;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.world=bpy.data.worlds.new('Review');scene.world.color=(.075,.075,.075)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
skin=material('Skin',(.58,.34,.22));metal=material('Gun',(.14,.19,.23))
def mesh(name,pts,f,mat):
    ids,ind=np.unique(f,return_inverse=True);m=bpy.data.meshes.new(name);m.from_pydata(pts[ids].tolist(),[],ind.reshape(-1,3).tolist());m.materials.append(mat)
    for p in m.polygons:p.use_smooth=name=='Skin'
    ob=bpy.data.objects.new(name,m);scene.collection.objects.link(ob)
out=r/'views';out.mkdir(exist_ok=True)
for key,w in poses.items():
    family=key.split('_')[0];p=np.zeros_like(v);xf=w@ib
    for b,ids,pts in groups:p[ids]+=pts@xf[b,:3,:].T
    p*=np.array([1,-1,1])
    for ob in list(scene.objects):bpy.data.objects.remove(ob,do_unlink=True)
    skinmask=np.array([n.startswith('Skin_') for n in g['slots']])[sections];keep=np.array([not any(k in n for k in ('NewBox','NewBelt','Glass','Reticle')) and (family=='base' or n!='M249_Factory_Foregrip') for n in g['slots']])[sections]
    mesh('Skin',p,faces[skinmask&left[faces].any(1)],skin);mesh('Gun',p,faces[~skinmask&keep],metal)
    folder=s/'Followup/geometry_final'/('box_normal_'+family)
    for part in folder.glob('frame_0023_*.vertices'):
        mesh(part.stem,np.fromfile(part,np.float32).reshape(-1,3)*[1,-1,1],np.fromfile(part.with_suffix('.indices'),np.uint32).reshape(-1,3),metal)
    h=w[ix['hand_l'],:3,3]*[1,-1,1];e=w[ix['lowerarm_l'],:3,3]*[1,-1,1];target=h*.75+e*.25
    for label,offset in [('wrist',[-60,16,24]),('palm',[40,20,12])]:
        cam=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',cam);scene.collection.objects.link(co);scene.camera=co;cam.type='ORTHO';cam.ortho_scale=37;cam.clip_start=.1
        co.location=target+np.array(offset);co.rotation_euler=(Vector(target)-co.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/(key+'_'+label+'.png'));bpy.ops.render.render(write_still=True)
