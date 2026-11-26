import json,numpy as np
from pathlib import Path
S=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
for rig in ['Jason','Kaitlin']:
    d=read(S/'CombatShirtR2/Authored'/f'shirt_cloth_{rig}.json');p=np.array(d['positions']);f=np.array(d['triangles']);count=len(p)//2;f=f[(f<count).all(1)];edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1);e,c=np.unique(edges,axis=0,return_counts=True);e=e[c==1];adj={}
    for a,b in e:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    unseen=set(adj)
    while unseen:
        group={next(iter(unseen))};stack=list(group)
        while stack:
            for b in adj[stack.pop()]:
                if b not in group:group.add(b);stack.append(b)
        unseen-=group;q=p[list(group)]
        print('BOUNDARY',rig,len(group),'mean',q.mean(0).round(2).tolist(),'min',q.min(0).round(2).tolist(),'max',q.max(0).round(2).tolist())
        if q[:,2].mean()>130:print('NECK_SAMPLES',q[::max(1,len(q)//20)].round(2).tolist())
    cfg=read(S/'CombatShirtR1/Inputs/modular_outfits.json');cfg=cfg if rig=='Jason' else cfg['body_variants']['kaitlin'];path=cfg['items']['ue_st6_sleeves']['owner_body_meshes'][rig];row=next(r for r in read(S/'CombatShirtR1/plan.json')['rows'] if r['source']==path);g=read(S/'CombatShirtR1/Inputs'/row['file']);pp=np.array(g['positions']);ff=np.array(g['triangles']);ids=np.unique(ff[pp[ff,2].mean(1)>120]);q=pp[ids];print('OLD_COLLAR',rig,len(q),q.min(0).round(2).tolist(),q.max(0).round(2).tolist())
