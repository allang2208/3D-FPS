"""Relieve the ulnar palm contact pocket without changing accepted finger poses."""
import json,hashlib,os
from pathlib import Path
import numpy as np
from author_fingerless_hunt_v2 import unit,normals,smooth
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';FULL=R/'FullShell'
depth=float(os.environ.get('FINGERLESS_PALM_CUP_CM','0'))
manifest=[]
for e in json.loads((R/'manifest.json').read_text()):
    # The author refreshes this full shell on every coverage edit. Historical
    # clearance backups must never replace the newly authored cut boundary.
    path=Path(e['authored']);source=FULL/path.name
    d=json.loads(source.read_text());p=np.array(d['positions']);t=np.array(d['triangles']);uv2=np.array(d['uv2']);outer=(uv2[:,:,1]==0).all(1)
    fields=np.zeros((len(p),2));n=np.zeros_like(p)
    for k in range(3):fields[t[outer,k]]=np.array(d['uv1'])[outer,k];n[t[outer,k]]=np.array(d['normals'])[outer,k]
    ulnar=np.array([sum(v for bn,v in w.items() if bn.startswith(('pinky_metacarpal','ring_metacarpal'))) for w in d['weights']])
    cup=depth*fields[:,0]*smooth(.5,1.1,fields[:,1])*smooth(.06,.36,ulnar)
    p-=n*cup[:,None]
    # A worn glove is the outer leather surface joined to the skin opening.
    # The separately authored empty pickup retains its inner shell.
    if d['profile']=='M4':(R/'PresentationM4.json').write_text(json.dumps(d,separators=(',',':')))
    faces=t[outer];used=np.unique(faces);mapping=np.full(len(p),-1,dtype=int);mapping[used]=np.arange(len(used))
    d['positions']=p[used].tolist();d['weights']=[d['weights'][i] for i in used];d['triangles']=mapping[faces].tolist()
    d['normals']=normals(p[used],np.array(d['triangles']))[np.array(d['triangles'])].tolist()
    for key in ('uv','uv1','uv2'):d[key]=np.array(d[key])[outer].tolist()
    d['triangle_materials']=[0]*len(faces);d['palm_cup_max_cm']=depth
    path.write_text(json.dumps(d,separators=(',',':')))
    manifest.append(dict(profile=d['profile'],authored=str(path),vertices=len(used),triangles=len(faces),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
(R/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('FINGERLESS_PALM_CUP',depth,len(manifest))
