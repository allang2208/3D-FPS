"""Focused geometric diagnosis of the user's pinky articulation complaint."""
import sys
from pathlib import Path
from collections import Counter
import numpy as np
from mathutils.bvhtree import BVHTree
from mathutils import Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P,read,write
from diagnose_steel_grip import matrix,tree
R=P/'SourceAssets/MetalGauntlet20260927/SteelGauntletV1'
OUT=R/'ArticulationSolve20260928'

def posed_groups(d):
 p=np.asarray(d['positions']);groups=[]
 for name in {b for ws in d['weights'] for b in ws}:
  ids=np.array([i for i,w in enumerate(d['weights']) if name in w]);weights=np.array([d['weights'][i][name] for i in ids])
  groups.append((name,ids,weights,np.linalg.inv(matrix(d['bones'][name]))))
 def deform(bones):
  out=np.zeros_like(p)
  for name,ids,weights,rest in groups:
   tr=matrix(bones[name])@rest
   out[ids]+=(p[ids]@tr[:3,:3].T+tr[:3,3])*weights[:,None]
  return out
 return deform

def intersections(p,ta,tb,a,b):
 pairs=a.overlap(b)
 if not pairs:return np.empty((0,2),int),np.array([])
 ids=np.asarray(pairs);va=p[ta[ids[:,0]]];vb=p[tb[ids[:,1]]]
 na=np.cross(va[:,1]-va[:,0],va[:,2]-va[:,0]);nb=np.cross(vb[:,1]-vb[:,0],vb[:,2]-vb[:,0])
 na/=np.maximum(np.linalg.norm(na,axis=1)[:,None],1e-14);nb/=np.maximum(np.linalg.norm(nb,axis=1)[:,None],1e-14)
 da=np.einsum('nki,ni->nk',va-vb[:,0,None,:],nb);db=np.einsum('nki,ni->nk',vb-va[:,0,None,:],na)
 depths=np.minimum.reduce([-da.min(1),da.max(1),-db.min(1),db.max(1)])
 valid=depths>.002
 return ids[valid],depths[valid]*10

def main():
 stage='temporal' if '--temporal' in sys.argv else 'corrected' if '--corrected' in sys.argv else 'after' if '--after' in sys.argv else 'before'
 root=OUT/'Candidate' if '--candidate' in sys.argv else R
 stride=1 if '--full' in sys.argv else 4
 parts=read(root/'parts.json');report={'stage':stage,'sample_hz':24/stride,'scope':'pinky versus liner and rigid plates; source animation geometry, not PIE','clips':[]};hits={}
 curve_file=OUT/('TemporalCandidate/runtime-pose-curves.json' if stage=='temporal' else 'runtime-pose-curves.json')
 curves={c['asset']:c for c in read(curve_file)['clips']} if stage in ('corrected','temporal') else {}
 for profile in ('M4','M1911','DW715'):
  d=read(root/'Authored'/f'{profile}.json');t=np.asarray(d['triangles']);deform=posed_groups(d)
  skin=t[np.array(d['triangle_materials'])==0]
  skin_labels=[]
  for face in skin:
   ws=Counter()
   for vi in face:ws.update(d['weights'][vi])
   skin_labels.append(ws.most_common(1)[0][0])
  skin_labels=np.asarray(skin_labels)
  plates=[p for p in parts if p['kind']=='steel_plate']
  pinkies=[q for q in plates if 'Pinky' in q['name'] or 'pinky' in q['name']]
  inputs=read(OUT/f'{profile}_motion.json')
  for clip in inputs['clips']:
   samples=clip['samples'];samples=samples if len(samples)<=3 else samples[::stride]+([samples[-1]] if (len(samples)-1)%stride else [])
   rows=[]
   for sample in samples:
    bones=sample['bones']
    if stage in ('corrected','temporal'):
     keys=curves[clip['asset']]['keys'];key=min(keys,key=lambda k:abs(k['time']-sample['time']))
     bones=dict(bones)
     basis=matrix(bones['hand_l'])[:3,:3];basis=basis/np.linalg.norm(basis,axis=0)
     offset=basis@np.asarray(key.get('left_hand_offset_cm',[0.,0.,0.]))
     for n,b in list(bones.items()):
      if n.endswith('_l') and n.startswith(('hand_','pinky_','ring_','index_','middle_','thumb_')):
       bones[n]=dict(b,position=(np.asarray(b['position'])+offset).tolist())
     old={n:matrix(b) for n,b in bones.items()};current={}
     for side_i,side in enumerate(('r','l')):
      for segment in (1,2,3):
       n=f'pinky_{segment:02d}_{side}';q=key['quaternions'][side_i*3+segment-1]
       delta=np.eye(4);delta[:3,:3]=np.asarray(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())
       base=old[n] if segment==1 else current[f'pinky_{segment-1:02d}_{side}']@np.linalg.inv(old[f'pinky_{segment-1:02d}_{side}'])@old[n]
       current[n]=base@delta;bones[n]=dict(position=current[n][:3,3].tolist(),axes=current[n][:3,:3].T.tolist())
    p=deform(bones);skin_tree=tree(p,skin);contacts=[]
    for q in pinkies:
     first=q['first_triangle'];faces=t[first:first+q['triangles']];parttree=tree(p,faces)
     ids,depth=intersections(p,faces,skin,parttree,skin_tree)
     if len(ids):
      hits.setdefault(q['name'],set()).update(ids[:,0].tolist())
      for label in np.unique(skin_labels[ids[:,1]]):
       chosen=skin_labels[ids[:,1]]==label
       contacts.append(dict(part=q['name'],other='liner:'+label,pairs=int(chosen.sum()),plane_cross_mm=float(depth[chosen].max())))
     otherparts=[other for other in plates if other is not q]
     otherfaces=np.concatenate([t[o['first_triangle']:o['first_triangle']+o['triangles']] for o in otherparts])
     labels=np.concatenate([np.full(o['triangles'],i) for i,o in enumerate(otherparts)])
     ids,depth=intersections(p,faces,otherfaces,parttree,tree(p,otherfaces))
     if len(ids):
      hits.setdefault(q['name'],set()).update(ids[:,0].tolist())
      offsets=np.cumsum([0]+[o['triangles'] for o in otherparts])
      for index in np.unique(labels[ids[:,1]]):
       selection=labels[ids[:,1]]==index
       if otherparts[index]['name'].startswith('Plate_Ring_'):
        hits.setdefault(otherparts[index]['name'],set()).update((ids[selection,1]-offsets[index]).tolist())
       contacts.append(dict(part=q['name'],other=otherparts[index]['name'],pairs=int(selection.sum()),plane_cross_mm=float(depth[selection].max())))
    rows.append(dict(time=sample['time'],contacts=contacts))
   worst=sorted([dict(c,time=row['time']) for row in rows for c in row['contacts']],key=lambda r:r['plane_cross_mm'],reverse=True)[:10]
   report['clips'].append(dict(profile=profile,label=clip['label'],asset=clip['asset'],samples=rows,worst=worst))
   print('PINKY_CONTACTS',profile,clip['label'],'poses',len(rows),'contact_poses',sum(bool(row['contacts']) for row in rows),'worst',worst[:3],flush=True)
   write(OUT/f'pinky-contacts-{stage}.json',report)
   write(OUT/f'contour-hits-{stage}.json',{name:sorted(values) for name,values in hits.items()})
 print('PINKY_CONTACTS_SAVED',stage,flush=True)
if __name__=='__main__':main()
