"""Recess only the added dark cuff roll; preserve mail, lining and links."""
import json,sys
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailInsetBinding20260929';OLD=P/'SourceAssets/ChainmailInterlace20260929';SWAY=P/'SourceAssets/ChainmailSharedSway20260929'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def unit(v):return v/np.linalg.norm(v)
def bind(b):
 m=np.eye(4);m[:3,:3]=np.asarray(b['axes']).T;m[:3,3]=b['position'];return m

def main():
 c=read(P/'Content/ColdSteelData/modular_outfits.json');recipe=c['items']['ue_chainmail_shirt']
 if recipe['appearance_family']!='ChainmailSharedSway20260929':raise RuntimeError('Current chainmail changed')
 write(R/'before.json',recipe)
 master=read(OLD/'Authored/M4.json');ps=np.asarray(master['positions']);faces=master['triangles'];mats=master['triangle_materials']
 base=next(x for x in read(OLD/'manifest.json') if x['profile']=='M4')['details']['original_triangles']
 ids=sorted({v for i,f in enumerate(faces) if i>=base and mats[i]==2 for v in f})
 new_profile=np.array([[.08,-.10],[.10,-.04],[.28,-.04],[.30,-.10],[.28,-.16],[.10,-.16]])
 changes={};normals={}
 for side in ['l','r']:
  wrist=np.asarray(master['bones']['hand_'+side]['position']);elbow=np.asarray(master['bones']['lowerarm_'+side]['position']);axis=unit(wrist-elbow)
  selected=[i for i in ids if (ps[i,0]<0 if side=='l' else ps[i,0]>0)]
  if len(selected)!=576:raise RuntimeError('Unexpected authored binding topology')
  for k in range(96):
   group=selected[k*6:k*6+6];p=ps[group[0]];radial=unit(p-wrist-axis*np.dot(p-wrist,axis));point=p-radial*.01
   for j,vi in enumerate(group):
    axial,rise=new_profile[j];changes[vi]=point-axis*axial+radial*rise-ps[vi]
    dp=new_profile[(j+1)%6]-new_profile[(j-1)%6];normals[vi]=unit(radial*dp[0]+axis*dp[1])
 records=[]
 for entry in read(SWAY/'manifest.json'):
  name=entry['profile'];target=read(OLD/'Authored'/(name+'.json'))
  sides={s for s in ['l','r'] if any(sum(v for k,v in w.items() if k.endswith('_'+s))>.7 for w in target['weights'])}
  keep=[i for i,p in enumerate(ps) if len(sides)==2 or (p[0]<0 if 'l' in sides else p[0]>0)]
  if len(keep)!=len(target['positions']):raise RuntimeError('Native vertex mapping changed '+name)
  remap={v:i for i,v in enumerate(keep)};normal_changes={}
  names={n for vi in changes if vi in remap for n in master['weights'][vi]}
  transforms={n:bind(target['bones'][n])@np.linalg.inv(bind(master['bones'][n])) for n in names}
  for vi,delta in changes.items():
   if vi not in remap:continue
   out=remap[vi];matrix=sum(transforms[n]*w for n,w in master['weights'][vi].items())[:3,:3]
   target['positions'][out]=(np.asarray(target['positions'][out])+matrix@delta).tolist()
   normal_changes[out]=unit(np.linalg.inv(matrix).T@normals[vi]).tolist()
  for fi,f in enumerate(target['triangles']):
   for ci,vi in enumerate(f):
    if vi in normal_changes:target['normals'][fi][ci]=normal_changes[vi]
  target['contract']='Recessed 2.2 mm dark binding; mail/lining/steel links and native weights unchanged'
  write(R/'Authored'/(name+'.json'),target)
  records.append(dict(profile=name,changed_vertices=len(normal_changes),triangles=len(target['triangles']),mask=str(SWAY/'Masks'/(name+'.json'))))
 write(R/'manifest.json',records)
 write(R/'production.json',dict(profiles=len(records),binding_width_mm=2.2,outermost_binding_inset_mm=.4,tip_setback_mm=.8,
  unchanged=['mail','inner lining','steel links','weights','topology','UV','shared sway masks','wrist coverage'],runtime_tested=False))
 print('INSET_BINDING_AUTHORED',len(records),'profiles')
if __name__=='__main__':main()
