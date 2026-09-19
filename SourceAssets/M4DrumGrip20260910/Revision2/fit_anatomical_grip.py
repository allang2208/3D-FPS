import bpy, math, json, sys, numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent;sys.path.insert(0,str(OUT.parent))
from preview_setup import setup
r,s,drum=setup();a=bpy.data.actions['M4_HK416_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(95);bpy.context.view_layer.update()
snapshot={b.name:b.matrix_basis.copy() for b in r.pose.bones};r.animation_data.action=None
for n,m in snapshot.items():r.pose.bones[n].matrix_basis=m
bpy.context.view_layer.update()
data=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(data['source_to_component']);center=Vector(data['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
rest=r.data.bones;hm=bpy.data.objects['SK_Manny_Arms_Export'];digits=['index','middle','ring','pinky','thumb']
finger_names=[b.name for b in r.pose.bones if b.name.endswith('_l') and b.name.startswith(tuple(digits))]
forward=(rest['middle_01_l'].head_local-rest['hand_l'].head_local).normalized();across=(rest['pinky_01_l'].head_local-rest['index_01_l'].head_local).normalized();normal=forward.cross(across).normalized()
if normal.dot(rest['middle_01_l'].matrix_local.to_3x3().col[1])<0:normal.negate()
across=normal.cross(forward).normalized();src=Matrix((forward,across,normal)).transposed()
# Palm at the character's LEFT side of the drum, fingers over its rear edge.
f=Vector((0,-1,0));n=Vector((-1,0,0));dst=Matrix((f,n.cross(f),n)).transposed()
hand_rot=(dst@src.transposed()@rest['hand_l'].matrix_local.to_3x3()).to_quaternion()
local_rest={b.name:(b.parent.matrix_local.inverted()@b.matrix_local if b.parent else b.matrix_local.copy()) for b in rest}
inv_rest={b.name:np.array(b.matrix_local.inverted()) for b in rest}
groups={g.index:g.name for g in hm.vertex_groups}
vpos=np.array([list(hm.matrix_world@v.co)+[1] for v in hm.data.vertices])
weights={n:np.array([sum(g.weight for g in v.groups if groups[g.group]==n) for v in hm.data.vertices]) for n in ['hand_l']+finger_names}
selected=np.array([i for i in range(len(vpos)) if sum(w[i] for w in weights.values())>.99])
vpos=vpos[selected];weights={n:w[selected] for n,w in weights.items()}
def sdf(p):
 q=np.stack((np.sqrt(p[:,0]**2+(p[:,2]+.085)**2)-.071,np.abs(p[:,1])-.0365),axis=1)
 return np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.maximum(q[:,0],q[:,1]),0)
params={'wrist_x':.088,'wrist_y':.094,'wrist_z':-.108,'thumb_splay':15.0}
for digit,angles in {'index':[-23,52,12],'middle':[-32,55,14],'ring':[-32,55,14],'pinky':[-22,48,12],'thumb':[0,8,5]}.items():
 for j,angle in enumerate(angles,1):params[f'{digit}_{j}']=angle
limits={'wrist_x':(.080,.125),'wrist_y':(.070,.120),'wrist_z':(-.113,-.095),'thumb_splay':(-40,50)}
for digit in digits:
 for j in range(1,4):limits[f'{digit}_{j}']=((-45,45) if j==1 else (-10,80 if j==2 else 50)) if digit!='thumb' else ((-35,65) if j==1 else (-10,50))
def matrices(p):
 mats={'hand_l':Matrix.LocRotScale(Vector((p['wrist_x'],p['wrist_y'],p['wrist_z'])),hand_rot,Vector((1,1,1)))}
 for name in finger_names:
  b=rest[name];q=Quaternion()
  if 'metacarpal' not in name:
   digit,j,_=name.split('_');q=Quaternion((0,0,1),math.radians(p[f'{digit}_{int(j)}']))
   if name=='thumb_01_l':q=Quaternion((0,1,0),math.radians(p['thumb_splay']))@q
  mats[name]=mats[b.parent.name]@local_rest[name]@q.to_matrix().to_4x4()
 return mats
def evaluate(p,details=False):
 mats=matrices(p);posed=np.zeros((len(vpos),3))
 for name,w in weights.items():posed+=((np.array(mats[name])@inv_rest[name]@vpos.T).T[:,:3])*w[:,None]
 dist=sdf(posed);collision=np.maximum(.0015-dist,0)
 loss=30000*np.mean(collision**2)+500*np.max(collision)**2
 contacts={}
 for digit in digits:
  ids=weights[digit+'_03_l']>.75;points=posed[ids]
  # The opposition thumb contacts the near cap; four fingers curl over the far cap.
  face=.044 if digit=='thumb' else -.044
  face_err=np.mean(points[:,1])-face
  # Closest pad must approach the cap, with all vertices remaining outside the solid.
  contact=np.mean(np.sort(sdf(points))[:max(3,len(points)//8)])
  loss+=20*face_err**2+30*contact**2
  contacts[digit]={'pad_gap_mm':float(contact*1000),'mean_y':float(np.mean(points[:,1]))}
 # Keep the palm close enough to support the cylinder wall.
 palm=dist[weights['hand_l']>.9];loss+=8*np.mean(np.sort(palm)[:max(3,len(palm)//12)])**2
 if details:return mats,posed,{'loss':float(loss),'penetrating_vertices':int(np.sum(dist<-.001)),'deepest_mm':float(max(0,-dist.min())*1000),'contacts':contacts}
 return float(loss)
best=evaluate(params)
for step in [15,8,4,2,1,.5]:
 for sweep in range(12):
  changed=False
  for key in params:
   delta=step*.00035 if key.startswith('wrist') else step
   initial=params[key]
   for value in [max(limits[key][0],initial-delta),min(limits[key][1],initial+delta)]:
    trial=dict(params);trial[key]=value;cost=evaluate(trial)
    if cost<best-1e-10:params=trial;best=cost;changed=True
  if not changed:break
 print('FIT',step,best,flush=True)
mats,posed,report=evaluate(params,True)
r.pose.bones['hand_l'].matrix=D@mats['hand_l'];bpy.context.view_layer.update()
for name in finger_names:
 r.pose.bones[name].matrix=D@mats[name];bpy.context.view_layer.update()
result={'wrist_in_drum':[list(v) for v in mats['hand_l']],'fingers':{name:[list(v) for v in r.pose.bones[name].matrix_basis] for name in finger_names},'parameters':params,'contact':report}
(OUT/'anatomical_grip.json').write_text(json.dumps(result,indent=2))
# Diagnostic renders show the real mesh; wrist/arm are solved by the motion builder.
import bmesh
bm=bmesh.new();bm.from_mesh(hm.data);layer=bm.verts.layers.deform.active
left_groups={g.index for g in hm.vertex_groups if g.name in weights}
remove=[v for v in bm.verts if sum(w for g,w in v[layer].items() if g in left_groups)<.99]
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(hm.data);bm.free()
for ob in s.objects:
 if ob.type=='MESH' and ob not in [hm,drum]:ob.hide_render=True
s.render.resolution_x=900;s.render.resolution_y=800;s.camera.data.type='ORTHO';s.camera.data.ortho_scale=.34
focus=D@Vector((.02,0,-.085))
for name,offset in [('front',(.35,.5,.2)),('back',(.35,-.5,.2))]:
 s.camera.location=focus+D.to_3x3()@Vector(offset);s.camera.rotation_euler=(focus-s.camera.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(OUT/('grip_'+name+'.png'));bpy.ops.render.render(write_still=True)
print('ANATOMICAL_GRIP',json.dumps(result['contact']),params)
