from pathlib import Path
import json,numpy as np,hashlib,bisect
P=Path(__file__).resolve().parent;O=P/'Authored';O.mkdir(exist_ok=True)
bones=json.loads((P/'Inputs/bare.json').read_text())['bones'];data=json.loads((P/'Inputs/BarePalmV7_source.json').read_text());pos=np.array(data['positions']);weights=data['weights'];fore=['lowerarm_r','lowerarm_twist_02_r','lowerarm_twist_01_r','hand_r'];e=np.array(bones['lowerarm_r']['p']);axis=np.array(bones['hand_r']['p'])-e;stations=[(np.array(bones[n]['p'])-e)@axis/(axis@axis) for n in fore]
changed=0
for i,old in enumerate(weights):
 total=sum(old.get(n,0) for n in fore)
 if total<1e-9 or not any(old.get(n,0)>0 for n in fore[:-1]):continue
 t=(pos[i]-e)@axis/(axis@axis);j=max(0,min(2,bisect.bisect_right(stations,t)-1));a=float(np.clip((t-stations[j])/(stations[j+1]-stations[j]),0,1));new={n:w for n,w in old.items() if n not in fore}
 for n,w in [(fore[j],total*(1-a)),(fore[j+1],total*a)]:
  if w>1e-10:new[n]=w
 if sum(abs(new.get(n,0)-old.get(n,0)) for n in set(old)|set(new))>1e-8:changed+=1
 weights[i]=new
# Local topology relaxation only at already mixed right finger joints.
adj=[set() for _ in pos]
for a,b,c in data['triangles']:
 adj[a].update((b,c));adj[b].update((a,c));adj[c].update((a,b))
digits=['thumb','index','middle','ring','pinky'];labels=[]
for ws in weights:
 scores=[sum(w for n,w in ws.items() if n.startswith(d+'_') and n.endswith('_r')) for d in digits];labels.append(digits[int(np.argmax(scores))] if max(scores)>.35 else None)
finger_ids=set()
for _ in range(2):
 old=[w.copy() for w in weights]
 for i,digit in enumerate(labels):
  if digit is None:continue
  relevant={n:w for n,w in old[i].items() if n.startswith(digit+'_') and n.endswith('_r')}
  if len([w for w in relevant.values() if w>.08])<2:continue
  neighbors=[j for j in adj[i] if labels[j]==digit]
  if not neighbors:continue
  total=sum(relevant.values());target={n:sum(old[j].get(n,0) for j in neighbors)/len(neighbors) for n in relevant};den=sum(target.values())
  if den<1e-8:continue
  weights[i]={**old[i],**{n:.75*w+.25*target[n]*total/den for n,w in relevant.items()}};finger_ids.add(i)
data['right_hand_revision']='RightHand52';data['contract']+='; RightHand52: PKM-only right forearm/wrist station weights and local mixed-finger-joint relaxation; original geometry retained'
raw=json.dumps(data,separators=(',',':')).encode();(O/'BarePalmV7.json').write_bytes(raw)
for family in ['HuntFieldGlovesV1','FittedFieldGlovesV1']:
 d=json.loads((P/'Inputs'/f'{family}_source.json').read_text())
 for i,bi in enumerate(d['bare_vertex_ids']):
  if sum(w for n,w in weights[bi].items() if n.endswith('_r'))>.99:d['weights'][i]=weights[bi].copy()
 d['bare_authored_sha256']=hashlib.sha256(raw).hexdigest();d['right_hand_revision']='RightHand52';(O/(family+'.json')).write_text(json.dumps(d,separators=(',',':')))
(P/'weight_authoring.json').write_text(json.dumps(dict(forearm_vertices=changed,finger_joint_vertices=len(finger_ids),stations=list(map(float,stations)),scope='PKM right side only'),indent=2));print('WEIGHTS_AUTHORED',changed,len(finger_ids))
