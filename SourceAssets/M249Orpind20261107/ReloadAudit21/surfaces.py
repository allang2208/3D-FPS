"""Native UE skinned surfaces including runtime joint morphs; no asset writes."""
from pathlib import Path
import json,pickle,numpy as np,sys
from mathutils.bvhtree import BVHTree
r=Path(__file__).resolve().parent
results={}
label=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'completed'
for folder in sorted((r/label).iterdir()):
 if not (folder/'review.json').exists() or not list(folder.glob('frame_????.vertices')):continue
 j=json.loads((folder/'review.json').read_text());meta=json.loads((folder/'geometry.json').read_text());slots=meta['slots'];ns=meta['bones'];dom=np.fromfile(folder/'dominant.bin',np.uint32);bone_arm=np.array([n.endswith(('_l','_r')) and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')) for n in ns]);side=np.array([n.endswith('_l') for n in ns])[dom];hits=[]
 for frame in j['frames']:
  stem=folder/Path(frame['file']).stem
  if not stem.with_suffix('.vertices').exists():continue
  v=np.fromfile(stem.with_suffix('.vertices'),np.float32).reshape(-1,3);f=np.fromfile(stem.with_suffix('.indices'),np.uint32).reshape(-1,3);m=np.fromfile(stem.with_suffix('.materials'),np.uint32)
  visible=set(frame['visible_materials']);arm_face=bone_arm[dom[f]].all(1);ar=f[arm_face];left=side[ar].all(1);part={}
  for which,af in [('l',ar[left]),('r',ar[~left])]:
   arm=BVHTree.FromPolygons(v.tolist(),af.tolist(),all_triangles=True);obstacles=[]
   for si,slot in enumerate(slots):
    if si not in visible or 'Skin' in slot or any(x in slot for x in ['Belt','Bullet','Glass','Reticle']):continue
    obs=f[(m==si)&~arm_face]
    if len(obs):obstacles.append((slot,v,obs))
   for p in folder.glob(stem.name+'_*.vertices'):
    obstacles.append((p.stem,np.fromfile(p,np.float32).reshape(-1,3),np.fromfile(p.with_suffix('.indices'),np.uint32).reshape(-1,3)))
   for name,p,ff in obstacles:
    tree=BVHTree.FromPolygons(p.tolist(),ff.tolist(),all_triangles=True);pairs=arm.overlap(tree)
    if pairs:
     ids=np.unique([a for a,b in pairs]);bones=sorted(set(ns[i] for i in dom[af[ids]].ravel()));part[which+':'+name]=dict(triangles=len(ids),bones=bones)
  if part:hits.append(dict(source=frame['source'],runtime=frame['runtime'],contacts=part))
 results[folder.name]=hits;print(folder.name,'contact frames',len(hits),flush=True)
(r/('surface_contacts_'+label+'.json')).write_text(json.dumps(results,indent=2))
