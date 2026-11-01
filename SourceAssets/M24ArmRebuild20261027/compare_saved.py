import json,math,bisect
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
O=Path(__file__).resolve().parent;source=json.loads((O/'source_before.json').read_text());ue=json.loads((O/'ue_before.json').read_text())
names=list(source['rest']);parents=source['parents'];K=Matrix.Diagonal((1,-1,1,1))
def unpack(v):return Vector(v[:3]),Quaternion((v[6],*v[3:6])),Vector(v[7:10])
def sample(track,time):
 ts=track['times'];i=max(0,min(len(ts)-2,bisect.bisect_right(ts,time)-1));v=track['values']
 a=unpack(v[i*10:i*10+10])
 if len(ts)==1:return a
 b=unpack(v[(i+1)*10:(i+2)*10]);w=max(0,min(1,(time-ts[i])/(ts[i+1]-ts[i])))
 return a[0].lerp(b[0],w),a[1].slerp(b[1],w),a[2].lerp(b[2],w)
report={}
for role,data in ue['clips'].items():
 layer=next(c for c in ue['profiles']['base'] if c['base']==data['path']);tracks={t['bone']:t for t in layer['tracks']};rows=[]
 for f,raw in data['poses'].items():
  comp={};expected=source['clips'][role]['poses'][int(f)];errors={}
  for n,v in zip(names,raw):
   p,q,sc=unpack(v)
   if n in tracks:
    dp,dq,ds=sample(tracks[n],int(f)/data['fps']);p+=dp;q=dq@q;sc+=ds
   loc=Matrix.LocRotScale(p,q,sc);comp[n]=comp[parents[n]]@loc if parents[n] else loc
   errors[n]=100*(comp[n].translation-K@Matrix(expected[n]).translation).length
  rows.append({'frame':int(f),'max_error_cm':max(errors.values()),'worst':max(errors,key=errors.get),'hands_cm':{side:errors['hand_'+side] for side in ('l','r')}})
 report[role]=rows
 print(role,rows,flush=True)
(O/'saved_source_comparison.json').write_text(json.dumps(report,indent=2))
