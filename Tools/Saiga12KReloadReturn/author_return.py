"""Replace only the empty-reload regrip's inherited wrist/digit return curves.

Author in native local rotations: hold the accepted release and grasp endpoints,
preserve all bone translations/scales and keep the magazine/bolt source clock.
"""
import json,gzip,sys,copy
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as Rot,Slerp
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KReloadReturn20261018'
sys.path.insert(0,str(P/'Tools/Saiga12KInspect'))
from pose_math import matrix,rotation,pack,world,apply
code=(P/'Tools/Saiga12KInspect/author_profiles.py').read_text();exec(code[code.index('def sparse_track'):code.index('\ntimes=np.asarray')])
data=json.load(gzip.open(O/'Inputs/reload-source-scoped.json.gz','rt',encoding='utf8'))
START=380./120.;END=440./120.
report={'complete':False,'changed_roles':['reload_empty','drum_reload_empty'],'changed_families':['vertical','canted','prism'],'source_window_seconds':[START,END],'runtime_tested':False,'families':{},'method':'Native local quaternion curves between existing release and accepted grasp; thumb closes after the four fingers; matching smooth wrist and forearm helper return. No contact retiming or bone translation/scale changes.'}
for family in report['changed_families']:
 profile=copy.deepcopy(data['profiles'][family]);rows=[]
 for role in report['changed_roles']:
  source=data['clips'][role];clip=next(c for c in profile['clips'] if c['base']==source['asset'])
  times=np.array([f['time'] for f in source['frames']]);start=int(np.argmin(abs(times-START)));end=int(np.argmin(abs(times-END)))
  original=[{n:matrix(v) for n,v in f['local'].items()} for f in source['frames']]
  layered=[apply(p,clip,float(t)) for p,t in zip(original,times)]
  fingers=[n for n in layered[0] if n.endswith('_l') and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))]
  edited=['hand_l','lowerarm_twist_01_l','lowerarm_twist_02_l']+fingers
  rotations={n:Slerp([0.,1.],Rot.from_matrix(np.array([rotation(layered[start][n]),rotation(layered[end][n])]))) for n in edited}
  keys={n:[] for n in edited}
  for i,t in enumerate(times):
   for n in edited:
    value=pack(layered[i][n])
    if START<t<END:
     if n.startswith('thumb_'):a,b=START+.08,END
     elif n in fingers:a,b=START+.06,END-.025
     else:a,b=START,END
     f=float(np.clip((t-a)/(b-a),0,1));f=f*f*f*(f*(f*6.-15.)+10.)
     value[3:7]=rotations[n]([f]).as_quat()[0]
    base=pack(original[i][n]);dq=(Rot.from_quat(value[3:7])*Rot.from_quat(base[3:7]).inv()).as_quat()
    keys[n].append(np.r_[value[:3]-base[:3],dq,value[7:]-base[7:]])
  newtracks=[t for n,v in keys.items() if (t:=sparse_track(n,v,times)) is not None]
  clip['tracks']=[t for t in clip['tracks'] if t['bone'] not in edited]+newtracks
  rows.append({'role':role,'clip':source['asset'],'duration':source['duration'],'edited_bones':edited,'release_source_frame120':380,'grasp_source_frame120':440,'start_thumb_to_grasp_degrees':float(np.rad2deg((Rot.from_matrix(rotation(layered[start]['thumb_01_l'])).inv()*Rot.from_matrix(rotation(layered[end]['thumb_01_l']))).magnitude()))})
 profile['family']=family
 (O/'Profiles'/('DA_'+family+'.json')).write_text(json.dumps(profile),encoding='utf8')
 report['families'][family]={'clips':len(profile['clips']),'edited':rows,'other_clips_retained':len(profile['clips'])-2}
 print('SAIGA_EMPTY_RETURN_AUTHORED',family,len(rows),flush=True)
report['complete']=True;(O/'Receipts/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
