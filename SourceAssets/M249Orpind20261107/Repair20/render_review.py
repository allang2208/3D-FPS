"""Actual native skin, hinge close views and camera-space idle framing."""
import bpy,pickle,numpy as np
from pathlib import Path
from mathutils import Vector,Quaternion,Matrix
r=Path(__file__).resolve().parent;g=pickle.load(open(r.parent/'Repair19/geometry.pkl','rb'));cache=pickle.load(open(r/'candidate_world.pkl','rb'));before=pickle.load(open(r.parent/'Repair19/saved_world.pkl','rb'));d=pickle.load(open(r/'native.pkl','rb'))
def matrix(v):
    a=np.eye(4);a[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*np.array(v[7:]);a[:3,3]=v[:3];return a
v=np.array(g['vertices']);f=np.array(g['faces']);sec=np.array(g['sections']);ib=np.linalg.inv(np.array([matrix(x) for x in g['bind']]));ix={n:i for i,n in enumerate(g['names'])};groups={}
for j,ws in enumerate(g['weights']):
    for b,w in ws:
        ids,pts=groups.setdefault(b,([],[]));ids.append(j);pts.append(np.r_[v[j],1]*w)
groups=[(b,np.array(ids),np.array(pts)) for b,(ids,pts) in groups.items()]
def skin(w):
    p=np.zeros_like(v);xf=w@ib
    for b,ids,pts in groups:p[ids]+=pts@xf[b,:3,:].T
    return p
def rot(a):return a[:3,:3]/np.linalg.norm(a[:3,:3],axis=0)
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=12;s.cycles.use_denoising=True;s.render.resolution_x=960;s.render.resolution_y=600;s.render.resolution_percentage=100;s.world=bpy.data.worlds.new('world');s.world.use_nodes=True;s.world.node_tree.nodes.get('Background').inputs[0].default_value=(.12,.14,.17,1)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);return m
metal=material('diagnostic gun',(.08,.09,.10));skinmat=material('native skin',(.48,.26,.18));poly=material('magazine',(.035,.036,.037))
def mesh(name,p,faces,materials=None,skin=False):
    data=bpy.data.meshes.new(name);data.from_pydata(p.tolist(),[],faces.tolist());data.update();ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    data.materials.append(metal if skin else poly)
    if skin:
        data.materials.append(skinmat);data.polygons.foreach_set('material_index',materials);data.polygons.foreach_set('use_smooth',np.ones(len(faces),bool))
    return ob
for loc,power in [((50,-35,60),180000),((-40,-20,45),130000),((0,60,45),100000)]:
    ld=bpy.data.lights.new('soft','AREA');ld.energy=power;ld.size=70;lo=bpy.data.objects.new('soft',ld);bpy.context.collection.objects.link(lo);lo.location=loc;lo.rotation_euler=(-lo.location).to_track_quat('-Z','Y').to_euler()
cd=bpy.data.cameras.new('review');co=bpy.data.objects.new('review',cd);bpy.context.collection.objects.link(co);s.camera=co;cd.clip_start=.01;cd.clip_end=1000;parts=[];out=r/'views';out.mkdir(exist_ok=True)
def draw(w,name,side=True,idle_anchor=None):
    global parts
    for ob in parts:bpy.data.objects.remove(ob,do_unlink=True)
    p=skin(w);root=w[ix['WPN_root']];q=rot(root)
    if idle_anchor is None:
        transform=lambda pts:(pts-root[:3,3])@q
        cd.type='ORTHO';cd.ortho_scale=54;co.location=(78,-38,30);co.rotation_euler=(Vector((7,5,-6))-co.location).to_track_quat('-Z','Y').to_euler()
    else:
        rotate=np.array([[0,-1,0],[1,0,0],[0,0,1]]);convert=np.array([[0,1,0],[0,0,1],[-1,0,0]])
        transform=lambda pts:((pts@rotate.T+np.array(idle_anchor))@convert.T)
        cd.type='PERSP';cd.sensor_fit='VERTICAL';cd.angle_y=np.radians(75);co.location=(0,0,0);co.rotation_euler=(0,0,0)
    keep=np.array([not any(k in n for k in (('Belt','Box','Glass','Reticle') if side else ('NewBelt','NewBox','Glass','Reticle'))) for n in g['slots']])[sec]
    parts=[mesh('skin',transform(p),f[keep],np.isin(sec[keep],[7,8,9]).astype(int),True)]
    if side:
        for key,part in g['parts'].items():
            if key.endswith('_30'):continue
            m=w[ix['WPN_root' if key.endswith('Port') else 'WPN_SOCKET_Magazine']];points=np.array(part['vertices'])@rot(m).T+m[:3,3];parts.append(mesh(key,transform(points),np.array(part['faces'])))
    s.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
for t in (.72,1.,1.275,1.84,2.70,3.18,3.60):
    for label,data in [('before',before['reload_base']),('after',cache['side_reload_base'])]:
        k=np.argmin(abs(data['times']-t));draw(data['world'][k],f'{label}_{t:.3f}')
for key,t in [('side_reload_empty_base',3.41),('box_reload_empty_base',5.36)]:
    data=cache[key];draw(data['world'][np.argmin(abs(data['times']-t))],key,side=key.startswith('side'))
idle=next(v for k,v in d['clips'].items() if k.split('.')[0].endswith('_idle'));w=np.array([matrix(x) for x in idle['frames'][0]])
for i,p in enumerate(d['parents']):
    if p>=0:w[i]=w[p]@w[i]
for forward in (9,15,18.5):draw(w,'idle_'+str(forward),side=False,idle_anchor=[forward,9,-11])
print('M249_HINGE_AND_IDLE_REVIEW_RENDERED',flush=True)
