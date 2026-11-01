"""Current saved UE surface + data-model poses; no approximation from old V7 mesh."""
import bpy,json,math,sys,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parent;before='before' in sys.argv;O=P/('before-frames' if before else 'after-frames');O.mkdir(exist_ok=True)
mesh=json.loads((P/'native-mesh.json').read_text());clips=json.loads((P/('native-poses-before.json' if before else 'native-poses.json')).read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
C=np.diag([1.,-1.,1.,1.])
def matrix(t):
    q=Quaternion((t[6],t[3],t[4],t[5]));return np.array(Matrix.LocRotScale(Vector(t[:3]),q,Vector(t[7:10])))
names=clips['Charge']['names'];index={n:i for i,n in enumerate(names)}
ref=np.stack([matrix(mesh['bones'][n]['transform']) for n in names]);inv=np.linalg.inv(ref)
points=np.c_[np.array(mesh['positions']),np.ones(len(mesh['positions']))]
wi=np.zeros((len(points),8),dtype=int);wv=np.zeros((len(points),8))
for i,weights in enumerate(mesh['weights']):
    for j,(n,v) in enumerate(sorted(weights.items(),key=lambda p:-p[1])[:8]):wi[i,j]=index[n];wv[i,j]=v
wv/=np.maximum(wv.sum(axis=1,keepdims=True),1e-12)
def skin(poses):
    transforms=np.stack([matrix(t) for t in poses]);d=transforms@inv
    out=np.zeros((len(points),4))
    for j in range(8):out+=np.einsum('nij,nj->ni',d[wi[:,j]],points)*wv[:,j,None]
    return (out[:,:3]*[1,-1,1])*.01,transforms
verts,transforms=skin(clips['Charge']['frames'][0])
# Runtime masks the old embedded steel hammer section. Keep the actual skin
# sections here; otherwise its hidden geometry fills the review camera.
triangles=[list(reversed(t)) for t in mesh['triangles'] if all(any(n.endswith(('_l','_r')) for n in mesh['weights'][v]) for v in t)]
data=bpy.data.meshes.new('RuntimeV9Skin');data.from_pydata(verts,[],triangles);data.update()
arms=bpy.data.objects.new('SavedRuntimeV9Arms',data);bpy.context.collection.objects.link(arms)
for p in data.polygons:p.use_smooth=True
mat=bpy.data.materials.new('Review skin');mat.diffuse_color=(.56,.33,.23,1);mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.56,.33,.23,1);bsdf.inputs['Roughness'].default_value=.52
arms.data.materials.append(mat)
outfits=[]
for tag,color in [('sleeve',(.18,.095,.035,1)),('glove',(.055,.025,.012,1))]:
 cloth=json.loads((P/(tag+'-mesh.json')).read_text())
 cn=list(cloth['bones']);ci={n:i for i,n in enumerate(cn)}
 cp=np.c_[np.array(cloth['positions']),np.ones(len(cloth['positions']))]
 cinv=np.linalg.inv(np.stack([matrix(cloth['bones'][n]['transform']) for n in cn]))
 cw=np.zeros((len(cp),8));cx=np.zeros((len(cp),8),dtype=int)
 for i,weights in enumerate(cloth['weights']):
  for j,(n,v) in enumerate(sorted(weights.items(),key=lambda p:-p[1])[:8]):cx[i,j]=ci[n];cw[i,j]=v
 cw/=np.maximum(cw.sum(axis=1,keepdims=True),1e-12)
 cd=bpy.data.meshes.new(tag);cd.from_pydata(np.zeros((len(cp),3)),[],[list(reversed(t)) for t in cloth['triangles']]);cd.update()
 co=bpy.data.objects.new(tag,cd);bpy.context.collection.objects.link(co)
 cm=bpy.data.materials.new(tag);cm.diffuse_color=color;cm.use_nodes=True
 cb=cm.node_tree.nodes.get('Principled BSDF');cb.inputs['Base Color'].default_value=color;cb.inputs['Roughness'].default_value=.68
 co.data.materials.append(cm)
 for face in cd.polygons:face.use_smooth=True
 outfits.append((co,cn,cp,cinv,cx,cw))
arms.hide_render=True
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as (a,b):
    b.objects=[n for n in a.objects if n.startswith('SM_ThunderGodHammer_') and n.endswith('_factory')]
parts=[o for o in b.objects if o];mounts={o.name:Matrix.Translation(o.location.copy()) for o in parts}
for o in parts:bpy.context.collection.objects.link(o);o.parent=None;o.hide_render=False
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.resolution_x=960;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.world=bpy.data.worlds.new('Review world');scene.world.color=(.08,.08,.08)
bpy.ops.object.camera_add(location=(0,0,0));cam=bpy.context.object;cam.data.clip_start=.008;cam.data.clip_end=100;scene.camera=cam
for loc,power,size in [((-.8,.2,1.3),90,1.4),((.8,.5,.4),65,1.1),((0,-.2,.1),25,1)]:
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,.35,-.1))-o.location).to_track_quat('-Z','Y').to_euler()
shots=[('Charge',.65,'fp'),('Charge',1.0,'fp'),('Charge',2.,'fp'),('Charge',2.,'side'),('Release',.4,'fp')]
for j,(kind,t,view) in enumerate(shots):
    clip=clips[kind];frame=min(len(clip['frames'])-1,round(t*clip['fps']));verts,transforms=skin(clip['frames'][frame])
    arms.data.vertices.foreach_set('co',verts.astype(np.float32).ravel());arms.data.update()
    for co,cn,cp,cinv,cx,cw in outfits:
        ct=np.stack([transforms[index[n]] if n in index else np.linalg.inv(cinv[k]) for k,n in enumerate(cn)])@cinv
        cv=np.zeros((len(cp),4))
        for k in range(8):cv+=np.einsum('nij,nj->ni',ct[cx[:,k]],cp)*cw[:,k,None]
        co.data.vertices.foreach_set('co',((cv[:,:3]*[1,-1,1])*.01).astype(np.float32).ravel());co.data.update()
    w=C@transforms[index['WPN_root']]@C
    # The actual modular assembly uses bone_mount scale .01 to cancel the
    # native FBX bone's scale 100. Static Blender modules are already metres.
    w[:3,:3]*=.01;w[:3,3]*=.01;wpn=Matrix(w)
    for o in parts:o.matrix_world=wpn@mounts[o.name];o.hide_render=False
    if view=='fp':cam.location=(0,0,0);look=Vector((0,1,0));cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=32;cam.data.lens=32/(2*math.tan(math.radians(37.5)))
    else:cam.location=(.75,.65,.10);look=Vector((0,.30,-.08))-cam.location;cam.data.lens=28
    cam.rotation_euler=look.to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(O/f'{j:02d}_{kind}_{t:.3f}_{view}.png')
    bpy.ops.render.render(write_still=True)
(O/'render-receipt.json').write_text(json.dumps({'source':'current saved native V9 surface and data-model poses','frames':shots,'runtime_corrective_morphs':'not evaluated in offline surface review','gameplay_run':False},indent=2),encoding='utf-8')
print('THUNDER_NATIVE_SURFACE_REVIEW_RENDERED',flush=True)
