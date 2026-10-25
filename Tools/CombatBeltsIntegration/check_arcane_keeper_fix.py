"""Scoped offline regression for the reported floating keeper components."""
from combat_belts_common import *
root=P/'SourceAssets/ArcaneConduitBelt20261025/KeeperFixR2'
records=[]
for body in ('Jason','Kaitlin'):
    old=read(R/'arcane/Geometry'/f'{body}_LOD0.json')
    old_z=[min(p[2] for p in old['positions']),max(p[2] for p in old['positions'])];del old
    for lod in range(3):
        d=read(root/'arcane/Geometry'/f'{body}_LOD{lod}.json')
        z=[min(p[2] for p in d['positions']),max(p[2] for p in d['positions'])]
        empty=sum(not w for w in d['weights'])
        bad_sum=sum(abs(sum(v for _,v in w)-1)>1.e-5 for w in d['weights'])
        head=sum(any(('head' in d['bones'][b]['name'].lower() or 'neck' in d['bones'][b]['name'].lower()) and w>.001 for b,w in ws) for ws in d['weights'])
        if not (70<z[0]<z[1]<125) or empty or bad_sum or head:raise RuntimeError('Arcane waist or binding regression '+body+' '+str(lod))
        records.append(dict(body=body,lod=lod,old_lod0_z_cm=old_z,z_cm=z,empty_weights=empty,unnormalized_weights=bad_sum,head_neck_weights=head,passed=True))
        del d
write(root/'offline-checks.json',dict(completed=True,records=records,runtime_tested=False))
print('ARCANE_KEEPER_FIX_OFFLINE_CHECKS',json.dumps(records,ensure_ascii=False))
