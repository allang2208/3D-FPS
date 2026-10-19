"""Lower only the fitted resonance grip; carry its existing hand contact intact.

The native left arm is solved in component space, then written as sparse local
deltas. Fingers, shared sequences, right hand and weapon mechanisms are retained.
"""
import copy,gzip,json,sys,math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import trimesh
from scipy.spatial.transform import Rotation as Rot, Slerp

P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KResonance20261019'
for folder in ('Authoring','Profiles','Receipts','Before'):(O/folder).mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(P/'Tools/Saiga12KInspect'))
from pose_math import matrix,rotation,pack,world,apply
sys.path.insert(0,str(P/'SourceAssets/PKMLowpoly20260922/GripLayer56'))
import evaluate as arm_layer
AH=arm_layer.AH;arm=AH.BONES
code=(P/'Tools/Saiga12KInspect/author_profiles.py').read_text()
exec(code[code.index('def sparse_track'):code.index('\ntimes=np.asarray')])

grip=json.loads((O/'Inputs/grip.json').read_text());gv=np.array(grip['positions']);gt=np.array(grip['triangles']);gm=np.array(grip['materials'])
gun=json.loads((P/'SourceAssets/Saiga12KClosure20261018/Authoring/gun.json').read_text())
pv=np.array(gun['positions']);pt=np.array(gun['triangles']);parts=np.array(gun['parts'])
handguard=trimesh.Trimesh(pv,pt[parts=='Handguard'],process=False)
def underside(xs,y=30.):
 origins=np.array([[x,y,-20.] for x in xs]);hits,ids,_=handguard.ray.intersects_location(origins,np.tile([0.,0.,1.],(len(xs),1)),multiple_hits=True)
 return np.array([hits[ids==i,2].min() for i in range(len(xs))])

# Top of the actual donor rail is 2.90 cm; S12K underside is 1.075 cm.
# Keep 3.25 mm beneath the shell for a real, closed contour-matched saddle.
bottom=float(underside([.08])[0]);donor_top=float(gv[np.unique(gt[gm==0]),2].max())
delta=np.array([0.,0.,bottom-.325-donor_top])
xs=np.linspace(-1.05,1.21,17);top=underside(xs)+.045
floor=donor_top+delta[2]-.05
section=[(float(x),float(z)) for x,z in zip(xs,top)]+[(float(xs[-1]),floor+.04),(float(xs[-1]-.04),floor),(float(xs[0]+.04),floor),(float(xs[0]),floor+.04)]
# Inset end rings provide a small machining bevel without changing the fit.
center=np.array([.08,(floor+bottom)/2]);vertices=[];count=len(section)
for y,inset in ((26.55,.045),(26.595,0.),(33.405,0.),(33.45,.045)):
 for x,z in section:
  x+=inset*np.sign(center[0]-x);z+=inset*np.sign(center[1]-z)
  vertices.append([x,y,z])
faces=[]
for ring in range(3):
 for i in range(count):
  j=(i+1)%count;a=ring*count+i;b=ring*count+j;c=(ring+1)*count+j;d=(ring+1)*count+i
  faces.extend([[a,b,c],[a,c,d]])
for ring,reverse in ((0,False),(3,True)):
 # The saddle top is concave. A vertex-average center can lie above its
 # lowest surface, folding the cap; place its fan inside the bearing web.
 centerid=len(vertices);vertices.append([.08,vertices[ring*count][1],float((floor+bottom)/2)])
 for i in range(count):
  t=[centerid,ring*count+i,ring*count+(i+1)%count];faces.append(t[::-1] if reverse else t)
saddle=trimesh.Trimesh(vertices,faces,process=False);saddle.fix_normals()
normals=saddle.face_normals.tolist();uv=[]
for tri,n in zip(saddle.triangles,saddle.face_normals):
 axes=np.argsort(np.abs(n))[:2];uv.append((tri[:,axes]*.25).tolist())
geometry={'source':grip['path'],'offset_root_cm':delta.tolist(),'removed_material_slot':'Saiga12K_InterfaceMetal','saddle':{'positions':saddle.vertices.tolist(),'triangles':saddle.faces.tolist(),'normals':normals,'uv':uv,'material_id':1}}
(O/'Authoring/fit.json').write_text(json.dumps(geometry),encoding='utf8')

rig=json.loads((P/'SourceAssets/Saiga12KInspectClearance20261018/Inputs/runtime-source.json').read_text())
names=[b['name'] for b in rig['bones']];parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in rig['bones']}
rest={b['name']:matrix(b['world']) for b in rig['bones']};bind=SimpleNamespace(R=np.array([rotation(rest[n]) for n in arm]),st={},off={})
pos=np.array([rest[n][:3,3] for n in arm]);bind.U0=pos[4]-pos[1];bind.F0=pos[7]-pos[4];bind.FL0=AH.frame(bind.F0,np.cross(bind.U0,bind.F0))
for i,origin,axis in ((2,pos[1],bind.U0),(3,pos[1],bind.U0),(5,pos[4],bind.F0),(6,pos[4],bind.F0)):
 bind.st[i]=(pos[i]-origin)@axis/(axis@axis);bind.off[i]=pos[i]-origin-bind.st[i]*axis
profile=json.loads((O/'Inputs/profile.json').read_text());output=copy.deepcopy(profile)
motion=json.load(gzip.open(O/'Inputs/poses.json.gz','rt',encoding='utf8'))['clips']
idle=profile['clips'][0];f=motion[idle['base']]['frames'][0];w=world(apply({n:matrix(v) for n,v in f['local'].items()},idle,0.),parents);contact=np.linalg.inv(w['WPN_root'])@w['hand_l']
def smooth(x):
 t=float(np.clip(x,0,1));return t*t*t*(t*(t*6-15)+10)
report={'complete':False,'offset_root_cm':delta.tolist(),'grip_old_top_cm':donor_top,'handguard_bottom_cm':bottom,'grip_new_top_cm':donor_top+delta[2],'saddle_watertight':bool(saddle.is_watertight),'clips':[],'runtime_tested':False}
edited=list(arm)+['ik_hand_l']
for ci,clip in enumerate(profile['clips']):
 if clip.get('retained'):raise RuntimeError('Retained motion needs separate authoring')
 frames=motion[clip['base']]['frames'];times=np.array([f['time'] for f in frames]);keys={n:[] for n in edited};weights=[];shifts=[];contact_errors=[];segment_errors=[]
 for frame in frames:
  original={n:matrix(v) for n,v in frame['local'].items()};local=apply(original,clip,frame['time']);w=world(local,parents);old={n:m.copy() for n,m in w.items()}
  g=np.linalg.inv(w['WPN_root'])@w['hand_l'];distance=np.linalg.norm((g[:3,3]-contact[:3,3])*100)
  # Preserve the hand's existing release path while fading the installation
  # correction out before magazine/bolt handling, and back in on regrip.
  weight=1.-smooth((distance-.8)/7.2);weights.append(weight)
  if weight>1e-9:
   target=w['hand_l'].copy();target[:3,3]+=w['WPN_root'][:3,:3]@(delta*.01)*weight
   rotations=np.array([rotation(w[n]) for n in arm]);points=np.array([w[n][:3,3] for n in arm]);oldpoints=points.copy()
   limit=np.linalg.norm(points[4]-points[1])+np.linalg.norm(points[7]-points[4])-.3
   reach=target[:3,3]-points[1];shift=AH.unit(reach)*max(0.,np.linalg.norm(reach)-limit);points+=shift;shifts.append(float(np.linalg.norm(shift)))
   pole=points[4]-points[1]
   zr,zp,_=arm_layer.layer_arm(rotations,points,rotations[7],points[7],0.,pole,bind,0.)
   nr,np_,info=arm_layer.layer_arm(rotations,points,rotation(target),target[:3,3],0.,pole,bind,0.)
   if info['short']>.001:raise RuntimeError('Unreachable support hand')
   desired={}
   for i,n in enumerate(arm):
    correction=nr[i]@zr[i].T;m=w[n].copy();m[:3,:3]=correction@w[n][:3,:3];m[:3,3]=np_[i]+correction@(points[i]-zp[i]);desired[n]=m
   desired['hand_l']=target
   final={}
   for n in names:
    parent=parents[n]
    if n in desired:
     final[n]=desired[n];local[n]=np.linalg.inv(final[parent])@final[n] if parent else final[n]
    else:final[n]=final[parent]@local[n] if parent else local[n]
   if 'ik_hand_l' in final:
    final['ik_hand_l']=final['hand_l']@np.linalg.inv(old['hand_l'])@old['ik_hand_l'];local['ik_hand_l']=np.linalg.inv(final[parents['ik_hand_l']])@final['ik_hand_l']
   contact_errors.append(float(np.linalg.norm(final['hand_l'][:3,3]-target[:3,3])))
   for a,b in (('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')):
    segment_errors.append(abs(np.linalg.norm(final[b][:3,3]-final[a][:3,3])-np.linalg.norm(old[b][:3,3]-old[a][:3,3])))
  for n in keys:
   a,b=pack(original[n]),pack(local[n]);dq=(Rot.from_quat(b[3:7])*Rot.from_quat(a[3:7]).inv()).as_quat();keys[n].append(np.r_[b[:3]-a[:3],dq,b[7:]-a[7:]])
 if max(weights)<1e-9:
  report['clips'].append({'asset':clip['base'],'unchanged':True});continue
 tracks=[t for n,v in keys.items() if (t:=sparse_track(n,v,times)) is not None]
 output['clips'][ci]['tracks']=[t for t in clip['tracks'] if t['bone'] not in edited]+tracks
 row={'asset':clip['base'],'samples':len(frames),'offset_weight_range':[min(weights),max(weights)],'max_shoulder_shift_cm':max(shifts,default=0.),'max_hand_target_error_cm':max(contact_errors,default=0.),'max_segment_length_error_cm':max(segment_errors,default=0.),'other_tracks_retained':True}
 report['clips'].append(row);print('S12K_RESONANCE_AUTHORED',clip['base'].split('.')[-1],flush=True)
(O/'Profiles/DA_angled.json').write_text(json.dumps(output),encoding='utf8')
report['complete']=True
(O/'Receipts/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='clips'}),flush=True)
