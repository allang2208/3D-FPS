"""Targeted offline skin/contact inspection; no UE/editor launch."""
import bpy,json,sys,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
root=Path('D:/FPS3D/FPSGAME')
out=root/'SourceAssets/ThirdPersonStaffGripFacing20261009'
args=sys.argv[sys.argv.index('--')+1:]
label=args[0]
data=json.loads((root/args[1]).read_text())['variants']['false']
body_key=args[2] if len(args)>2 else None
target=json.loads((root/'SourceAssets/JasonPlayer20261003/Jason.json').read_text())
surface=json.loads((root/'SourceAssets/ApprenticeStaff20260927/BowBasedGripV12/grip-surfaces.json').read_text())
names=[b['name'] for b in target['bones']]
parent={b['name']:names[b['parent']] if b['parent']>=0 else None for b in target['bones']}
def m(q,p):
    t=np.eye(4);t[:3,:3]=q;t[:3,3]=p;return t
def rot(q):return np.array(Quaternion((q[3],*q[:3])).to_matrix())
rest={b['name']:m(np.array(b['axes']).T,b['position']) for b in target['bones']}
local={n:np.linalg.inv(rest[parent[n]])@rest[n] if parent[n] else rest[n] for n in names}
def below(n):
    while parent[n]:
        n=parent[n]
        if n=='hand_r':return True
    return False
children=[n for n in names if below(n)]
inv=np.linalg.inv(rest['hand_r']);native={n:inv@rest[n] for n in ['hand_r',*children]}
w={'hand_r':np.array(data['hand_in_grip'])}
for n in children:
    q=rot(data['rotations'][n]) if n in data['rotations'] else local[n][:3,:3]
    if '_half_' in n and parent[n] in data['rotations']:
        delta=Matrix(local[parent[n]][:3,:3].T@rot(data['rotations'][parent[n]])).to_quaternion()
        q=np.array(Quaternion().slerp(delta.inverted(),.5).to_matrix())@local[n][:3,:3]
    w[n]=w[parent[n]]@m(q,local[n][:3,3])
if body_key:
    body_pose=json.loads((out/'inspection-poses.json').read_text())[body_key]
    w={n:m(rot(t[3:7]),t[:3]) for n,t in body_pose['bones'].items()}
    staff_frame=w['hand_r']@np.linalg.inv(np.array(data['hand_in_grip']))
bpy.ops.wm.read_factory_settings(use_empty=True)
def mat(name,color):
    x=bpy.data.materials.new(name);x.diffuse_color=(*color,1);x.use_nodes=True
    b=x.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=.65
    return x
gray=mat('Steel glove neutral inspection',(.3,.42,.5));wood=mat('Actual shaft profile',(.26,.15,.065))
def mesh(name,p,t,material):
    # UE to Blender coordinate reflection, with winding reversed as well.
    p=np.array(p)*[1,-1,1];t=np.array(t)[:,::-1]
    me=bpy.data.meshes.new(name);me.from_pydata(p.tolist(),[],t.tolist());me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);me.materials.append(material)
    for f in me.polygons:f.use_smooth=True
    return ob
geo=json.loads((root/'SourceAssets/JasonPlayer20261003/ue_steel_gauntlets_fitted.json').read_text())
tri=json.loads((root/'SourceAssets/JasonPlayer20261003/ue_steel_gauntlets.json').read_text())['triangles']
p=np.asarray(geo['positions']);weights=geo['weights']
base=w['hand_r']@np.linalg.inv(rest['hand_r'])
missing=np.array([1-sum(v for b,v in ws if names[b] in native) for ws in weights])
posed=np.zeros_like(p) if body_key else (p@base[:3,:3].T+base[:3,3])*missing[:,None]
mask=np.array([sum(v for b,v in ws if names[b] in native)>.95 for ws in weights])
for b,n in enumerate(names):
    if n not in native:continue
    rows=[];wt=[]
    for i,ws in enumerate(weights):
        for j,v in ws:
            if j==b:rows.append(i);wt.append(v)
    if not rows:continue
    mm=w[n]@np.linalg.inv(rest[n]);posed[rows]+=(p[rows]@mm[:3,:3].T+mm[:3,3])*np.array(wt)[:,None]
t=np.asarray(tri);t=t[np.all(mask[t],axis=1)]
mesh('Actual skinned steel right hand',posed,t,gray)
if body_key:
    cloth=json.loads((root/'SourceAssets/JasonPlayer20261003/ue_chainmail_shirt_fitted.json').read_text())
    ct=json.loads((root/'SourceAssets/JasonPlayer20261003/ue_chainmail_shirt.json').read_text())['triangles']
    cp=np.array(cloth['positions']);pos=np.zeros_like(cp)
    for b,n in enumerate(names):
        rows=[];wt=[]
        for i,ws in enumerate(cloth['weights']):
            for j,v in ws:
                if j==b:rows.append(i);wt.append(v)
        if not rows:continue
        mm=w[n]@np.linalg.inv(rest[n]);pos[rows]+=(cp[rows]@mm[:3,:3].T+mm[:3,3])*np.array(wt)[:,None]
    mesh('Production fitted shirt arm context',pos,ct,mat('Shirt',(.2,.25,.28)))
r=np.array(surface['variants']['false']['radii']);z=np.array(surface['z'])-32
angles=-np.arange(r.shape[1])*2*np.pi/r.shape[1]
p=np.stack((r*np.cos(angles)[None,:],r*np.sin(angles)[None,:],np.broadcast_to(z[:,None],r.shape)),axis=-1).reshape(-1,3)
if body_key:p=p@staff_frame[:3,:3].T+staff_frame[:3,3]
N=r.shape[1];t=[]
for j in range(len(z)-1):
    for i in range(N):
        a=j*N+i;b=j*N+(i+1)%N;c=b+N;d=a+N;t.extend([(a,b,c),(a,c,d)])
mesh('Measured staff grip surface',p,t,wood)
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.eevee.taa_render_samples=32
s.render.resolution_x=640;s.render.resolution_y=640;s.render.resolution_percentage=100
s.world=bpy.data.worlds.new('Studio');s.world.color=(.28,.28,.28)
s.view_settings.view_transform='AgX'
center=Vector((0,0,-1))
if body_key:center=Vector(tuple((w['hand_r'][:3,3]*.65+w['upperarm_r'][:3,3]*.35)*[1,-1,1]))
for i,pos in enumerate([(10,-15,25),(-20,8,15),(0,20,8)]):
    d=bpy.data.lights.new('Area'+str(i),'AREA');d.energy=5000;d.size=15
    ob=bpy.data.objects.new(d.name,d);s.collection.objects.link(ob);ob.location=center+Vector(pos);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
cam=bpy.data.cameras.new('Contact camera');ob=bpy.data.objects.new('Contact camera',cam);s.collection.objects.link(ob);s.camera=ob
cam.type='ORTHO';cam.ortho_scale=22;cam.clip_start=.01;cam.clip_end=500
if body_key:cam.ortho_scale=62
for name,pos in [('front',(24,-30,12)),('palm',(-24,30,10)),('side',(30,22,10))]:
    ob.location=center+Vector(pos)* (3 if body_key else 1);ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
    s.render.filepath=str(out/(label+'-'+name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/(label+'.blend')))
