"""Requested offline inspection of current/revised reload geometry. No UE launch."""
import sys,json,gzip
from pathlib import Path
import numpy as np
O=Path(__file__).parent;sys.path.insert(0,str(O.parent/'ClothReload44/Diagnostics'))
import diag_lib as D
S=json.loads((O/'source.json').read_text());L=json.loads((O/'layout.json').read_text())
T=D.load_tracks(O.parent/'ClothReload44/Tracks/base_tracks.json.gz');A={**T,**D.load_tracks(O/'Tracks/base_tracks.json.gz')}
frames=[209,222,458,489,526,574]
old=D.worlds(T,frames);new=D.worlds(A,frames)
rest={b['name']:D.mat(b['rest']) for b in S['bones']};idle={n:D.mat(v) for n,v in S['idle'].items()}
f=np.load(O/'feed.npz');bn={b['index']:b['name'] for b in S['bones']}
with gzip.open(O/'mesh_buffers.json.gz','rt') as h:buffers=json.load(h)
with gzip.open(O.parent/'BeltRebuild52/context.json.gz','rt') as h:context=json.load(h)
outdir=O/'Inspection';outdir.mkdir(exist_ok=True)
for version,poses in [('before',old),('after',new)]:
 for ni,fi in enumerate(frames):
  if version=='before' and fi!=209:continue
  W=poses[ni];t=fi/120;prefix='New_' if t>=2.8 else '';word='New' if prefix else 'Old';G=W[D.BI['WPN_root']];ig=np.linalg.inv(G);parts=[]
  def add(p,tr,role,bone):
   m=ig@W[D.BI[bone]]@np.linalg.inv(rest[bone]);parts.append({'p':(np.asarray(p)@m[:3,:3].T+m[:3,3]).tolist(),'t':np.asarray(tr).tolist(),'role':role})
  for mid in np.unique(f['mi']):
   name=S['slots'][mid]['name']
   if '__'+word+'Box' not in name and not (version=='before' and '__'+word+'Belt' in name):continue
   tris=f['tri'][f['mi']==mid]
   for bi in np.unique(f['dom'][tris]):
    bone=bn[bi]
    if version=='before' and bone.endswith('Belt_06'):continue
    ts=tris[np.all(f['dom'][tris]==bi,axis=1)]
    if not len(ts):continue
    ids=np.unique(ts);lookup=np.full(len(f['p']),-1);lookup[ids]=np.arange(len(ids))
    add(f['p'][ids],lookup[ts],'Cloth' if name.endswith('_Cloth') else 'Case' if '_Case' in name else 'Copper' if '_Copper' in name else 'Link',bone)
  if version=='after':
   for row in buffers:
    if ('__'+word+'Belt') not in row['slot'] or row['bone'].endswith('Belt_10') or row['bone'].endswith(('Link_12','Link_13')):continue
    add(row['p'],row['t'],row['role'],row['bone'])
  for si,s in enumerate(context['slots']):
   name=s['name']
   if any(a in name for a in ['Manny','Skin','Cloth33','Magazine','Glove','Sleeve']):continue
   ts=[r[:3] for r in context['triangles'] if r[3]==si and all(.07<float(context['positions_root_m'][str(v)][1])<.245 for v in r[:3])]
   if not ts:continue
   ids=sorted({v for r in ts for v in r});lookup={v:i for i,v in enumerate(ids)};p=np.array([context['positions_root_m'][str(i)] for i in ids])
   if any(a in name for a in ['R38_Interior','R38_Satin','G43_LidCoat']):
    m=ig@W[D.BI['LMG201_Cover']]@np.linalg.inv(idle['LMG201_Cover'])@idle['WPN_root'];p=p@m[:3,:3].T+m[:3,3]
   parts.append({'p':p.tolist(),'t':[[lookup[i] for i in r] for r in ts],'role':'Body'})
  with gzip.open(outdir/('%s_%d.json.gz'%(version,fi)),'wt') as h:json.dump(parts,h)
print('B53_INSPECTION_FRAMES',flush=True)
