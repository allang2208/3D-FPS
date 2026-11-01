"""Fit the original gesture against the entire assembled rifle, keeping fingers native."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
exec(compile((O/'author_candidate.py').read_text().split("roles=('fire'")[0],'candidate_setup','exec'))
data=json.loads((O/'candidate_poses.json').read_text())
clips={role:[{n:Matrix(m) for n,m in row.items()} for row in rows] for role,rows in data.items()}
names=list(rest);ids={n:i for i,n in enumerate(names)}
verts=np.array([list(v.co)+[1] for v in skin.data.vertices]);weights=np.zeros((len(verts),len(names)))
for v in skin.data.vertices:
 for g in v.groups:
  n=skin.vertex_groups[g.group].name
  if n in ids:weights[v.index,ids[n]]=g.weight
right=weights[:,[ids[n] for n in names if under(n,'upperarm_r')]].sum(1)>.75
hand=weights[:,[ids[n] for n in names if under(n,'hand_r')]].sum(1)>.75
selected=np.where(right)[0];W=np.einsum('vk,kij,vj->kvi',weights[selected],np.array([np.array(rest[n].inverted()) for n in names]),verts[selected],optimize=True)
hm=hand[selected];dominant=weights[selected].argmax(1)
digit_masks={f:np.isin(dominant,[ids[n] for n in names if n.startswith(f+'_') and n.endswith('_r')]) for f in ('thumb','index','middle','ring','pinky')}

def points(row):return np.einsum('kij,kvj->vi',np.array([np.array(row[n]) for n in names]),W,optimize=True)[:,:3]

hulls=[]
for ob in s.objects:
 if ob.type!='MESH' or ob==skin or len(ob.data.vertices)<4:continue
 # Rigid original gun parts each have a single mechanical bone assignment.
 totals={}
 for v in ob.data.vertices:
  for g in v.groups:
   n=ob.vertex_groups[g.group].name;totals[n]=totals.get(n,0)+g.weight
 if not totals:continue
 bone=max(totals,key=totals.get)
 if bone not in rest:continue
 bm=bmesh.new()
 for v in ob.data.vertices:bm.verts.new(v.co)
 bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False);bm.normal_update()
 center=sum((v.co for v in bm.verts),Vector())/len(bm.verts);ns=[];ds=[]
 for face in bm.faces:
  normal=face.normal.copy()
  if normal.dot(face.calc_center_median()-center)<0:normal=-normal
  ns.append(list(normal));ds.append(normal.dot(face.verts[0].co))
 bm.free();hulls.append((ob.name,bone,np.array(ns),np.array(ds)))

def distances(row,P,include_bolt=False):
 result={}
 for name,bone,N,D in hulls:
  if bone=='WPN_BoltHandle' and not include_bolt:continue
  inv=np.array(rest[bone]@row[bone].inverted());Q=P@inv[:3,:3].T+inv[:3,3]
  # Convex envelopes are conservative around curved stock/trigger cutouts.
  result[name]=np.max(Q@N.T-D,axis=1)
 return result

report={'metric':'conservative_part_convex_envelopes_not_final_surface_acceptance','before':{},'after':{}}
for role,rows in clips.items():
 report['before'][role]=[]
 for f,row in enumerate(rows):
  shift={'fire':0,'cycle':4,'reload_empty':52,'reload_empty_mag10':52}[role];t=f-shift
  if not 8<=t<=50:continue
  P=points(row);ds=distances(row,P,True)
  bad={n:{'max_penetration_mm':float(max(0,-d.min())*1000),'hand_penetration_mm':float(max(0,-d[hm].min())*1000)} for n,d in ds.items() if d.min()<-.001}
  report['before'][role].append({'frame':f,'parts':bad})
 print(role,'BEFORE',sorted([(max((v['hand_penetration_mm'] for v in x['parts'].values()),default=0),x['frame']) for x in report['before'][role]],reverse=True)[:6],flush=True)
(O/'collision_before.json').write_text(json.dumps(report,indent=2))
print('FULL_ASSEMBLY_ENVELOPES_RECORDED',[(n,b,len(N)) for n,b,N,D in hulls],flush=True)
