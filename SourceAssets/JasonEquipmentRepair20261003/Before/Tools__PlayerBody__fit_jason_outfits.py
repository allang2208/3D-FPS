"""Offline garment fitting; preserves authored garment topology and UV vertex order.

Uses common bind bones first, then a smooth body-surface displacement field.
Outputs positions and Jason-native skin weights for the Unreal authoring stage.
"""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003')
def read(key):return json.loads((ROOT/(key+'.json')).read_text(encoding='utf-8'))
target=read('Jason');skin=read('NativeSkin')
tv=np.array(target['positions']);tt=np.array(target['triangles'],dtype=int)
tb=target['bones'];target_by_name={b['name']:b for b in tb}

def dominant_groups(d):
    bones=d['bones'];groups=[]
    for bone in bones:
        name=bone['name'];i=bone['index'];group='torso'
        while i>=0:
            n=bones[i]['name']
            if n in ['head','neck_01','neck_02']:group='neck';break
            if n in [p+'_'+s for p in ['hand','lowerarm','upperarm','thigh','calf','foot','ball'] for s in ['l','r']]:
                group=n;break
            if any(n.startswith(p) for p in ['thumb_','index_','middle_','ring_','pinky_']):
                group=n.split('_')[0]+'_'+n[-1];break
            i=bones[i]['parent']
        groups.append(group)
    result=[]
    for ws in d['weights']:
        sums={}
        for b,w in ws:sums[groups[b]]=sums.get(groups[b],0)+w
        result.append(max(sums,key=sums.get) if sums else 'torso')
    return np.array(result)

def bind_warp(d):
    pos=np.array(d['positions']);out=np.zeros_like(pos);bones=d['bones']
    rows={i:[] for i in range(len(bones))}
    for vi,weights in enumerate(d['weights']):
        for bi,w in weights:rows[bi].append((vi,w))
    for bi,rows_b in rows.items():
        if not rows_b:continue
        b=bones[bi];mapped=b
        while mapped['name'] not in target_by_name and mapped['parent']>=0:mapped=bones[mapped['parent']]
        t=target_by_name.get(mapped['name'],tb[0])
        ids=np.array([r[0] for r in rows_b]);w=np.array([r[1] for r in rows_b])
        local=(pos[ids]-np.array(mapped['position']))@np.linalg.inv(np.array(mapped['axes']))
        moved=local@np.array(t['axes'])+np.array(t['position'])
        out[ids]+=moved*w[:,None]
    return out

def neighbors_by_group(query,qgroups,points,pgroups,k):
    ids=np.empty((len(query),k),int);dist=np.empty((len(query),k))
    for group in np.unique(qgroups):
        qi=np.flatnonzero(qgroups==group);pi=np.flatnonzero(pgroups==group)
        if len(pi)<k:pi=np.arange(len(points))
        ds,ix=cKDTree(points[pi]).query(query[qi],k=k)
        ids[qi]=pi[ix];dist[qi]=ds
    weights=1./np.maximum(dist,.08)**2;weights/=weights.sum(axis=1)[:,None]
    return ids,weights

tg=dominant_groups(target);sg=dominant_groups(skin);sv=bind_warp(skin)
# Only the visible sculpted body contributes to garment fitting; the masked
# MetaHuman proxy and the neck seam are retained separately in the base asset.
visible=np.unique(tt[np.array(target['triangle_materials'])==2].reshape(-1))
if len(visible)==0:raise RuntimeError('Visible Jason body section missing')
ni,nw=neighbors_by_group(sv,sg,tv[visible],tg[visible],4)
nearest=tv[visible][ni];residual=(nearest*nw[:,:,None]).sum(axis=1)-sv
# Bound local displacement, then smooth on the donor skin to preserve folds.
length=np.linalg.norm(residual,axis=1);residual*=np.minimum(1.,7./np.maximum(length,1e-8))[:,None]
si,sw=neighbors_by_group(sv,sg,sv,sg,14)
residual=(residual[si]*sw[:,:,None]).sum(axis=1)

# Triangle normals are used only for a small fitting clearance, not for texture changes.
normals=np.zeros_like(tv);tn=np.cross(tv[tt[:,1]]-tv[tt[:,0]],tv[tt[:,2]]-tv[tt[:,0]])
for j in range(3):np.add.at(normals,tt[:,j],tn)
normals/=np.maximum(np.linalg.norm(normals,axis=1),1e-12)[:,None]
manifest={}
for key,entry in read('inputs').items():
    if not key.startswith('ue_') or key.endswith('_skin'):continue
    d=read(key);g=dominant_groups(d);v=bind_warp(d)
    ids,w=neighbors_by_group(v,g,sv,sg,8)
    fitted=v+(residual[ids]*w[:,:,None]).sum(axis=1)
    close,cw=neighbors_by_group(fitted,g,tv[visible],tg[visible],3);native_ids=visible[close]
    surface=(tv[native_ids]*cw[:,:,None]).sum(axis=1)
    normal=(normals[native_ids]*cw[:,:,None]).sum(axis=1)
    normal/=np.maximum(np.linalg.norm(normal,axis=1),1e-12)[:,None]
    clearance=np.sum((fitted-surface)*normal,axis=1)
    fitted+=normal*np.maximum(0.,.12-clearance)[:,None]
    weights=[]
    for src_ids,blend in zip(native_ids,cw):
        total={}
        for vi,mix in zip(src_ids,blend):
            for bone,bw in target['weights'][vi]:total[bone]=total.get(bone,0)+bw*mix
        top=sorted(total.items(),key=lambda p:-p[1])[:8];den=sum(w for _,w in top)
        weights.append([[int(b),float(w/den)] for b,w in top if w>1e-5])
    result={'source':d['source'],'positions':fitted.tolist(),'weights':weights,'materials':d['materials']}
    (ROOT/(key+'_fitted.json')).write_text(json.dumps(result,separators=(',',':')))
    manifest[key]='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/SK_Jason_'+key
    print('JASON_GARMENT_FITTED',key,len(fitted),flush=True)

# Retain Jason's native skin/UVs, splitting only material sections for the
# existing shirt/glove coverage contract (0=sleeves,1=arms,2=hands,3=torso,4=rest).
st=np.array(skin['triangles'],int);centroids=sv[st].mean(axis=1)
region=cKDTree(centroids).query(tv[tt].mean(axis=1),k=1)[1]
regions=np.array(skin['triangle_materials'])[region]
# Split the upper half of the upper arms so a short sleeve can hide its covered
# skin without removing the exposed forearm. Full sleeves cover both regions.
tc=tv[tt].mean(axis=1)
for side in ('l','r'):
    shoulder=np.array(target_by_name['upperarm_'+side]['position']);elbow=np.array(target_by_name['lowerarm_'+side]['position'])
    axis=elbow-shoulder;t=np.sum((tc-shoulder)*axis,axis=1)/np.dot(axis,axis)
    arm=(regions==1)&(tc[:,0]*(1 if side=='l' else -1)>0)&(t<.48)
    regions[arm]=0
mids=np.array(target['triangle_materials']);regions[mids==0]=6;regions[mids==1]=5
base={'source':target['source'],'triangle_materials':regions.tolist(),
      'materials':[{'slot':n,'asset':target['materials'][2]['asset']} for n in ['DefaultSleeves','SkinArms','SkinHands','SkinTorso','SkinRest']]
       +[{'slot':'NeckSeam','asset':target['materials'][1]['asset']},{'slot':'MaskedProxy','asset':target['materials'][0]['asset']}]}
(ROOT/'base_fitted.json').write_text(json.dumps(base,separators=(',',':')))
manifest['base']='/Game/Characters/ModularOutfit20260924/JasonPlayer20261003/SK_Jason_Base'
(ROOT/'fitted_assets.json').write_text(json.dumps(manifest,indent=2))
