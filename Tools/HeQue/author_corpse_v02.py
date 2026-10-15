"""One continuous positive-weight cage for HeQue tissue, cuffs and chain."""
import json,sys,itertools
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/SoftDeathV02';folder=ROOT/'HeQue'
sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'));import author_cages
author_cages.ROOT=ROOT;item=json.loads((ROOT/'sources.json').read_text('utf8'))[0]
# Keep the complete exported surface in the shared field. There are no rigid
# patch transforms, external tether nodes, or separate metal shape projections.
author_cages.author(item)
with (folder/'surface.bin').open('rb') as f:
    count=int(np.fromfile(f,'<i4',1)[0]);points=np.fromfile(f,'<f4').reshape(count,3).astype(float)
skin=json.loads((folder/'surface.bin.skin.json').read_text('utf8'));names=skin['bones']
metal=[];cuff=[];chain=[]
for i,row in enumerate(skin['weights']):
    cuff_weight=sum(w for b,w in row if names[int(b)].startswith('HQ_Cuff_'))
    chain_weight=sum(w for b,w in row if names[int(b)].startswith('HQ_Chain_'))
    weight=cuff_weight+chain_weight
    if weight>.8:metal.append(i)
    if cuff_weight>.8:cuff.append(i)
    if chain_weight>.8:chain.append(i)
cage=json.loads((folder/'cage.json').read_text('utf8'));nodes=np.array(cage['nodes'])
edges=np.unique(np.sort([pair for tet in cage['tetrahedra'] for pair in itertools.combinations(tet,2)],axis=1),axis=0)
centres=(nodes[edges[:,0]]+nodes[edges[:,1]])*.5
cuff_distance,_=cKDTree(points[cuff]).query(centres)
chain_distance,_=cKDTree(points[chain]).query(centres)
heads=np.array(skin['heads_m']);axis=heads[names.index('HQ_Chain_14')]-heads[names.index('HQ_Chain_00')];axis/=np.linalg.norm(axis)
directions=nodes[edges[:,1]]-nodes[edges[:,0]];directions/=np.linalg.norm(directions,axis=1)[:,None]
# Reinforce cuff regions and chain width, but let the chain bend/shorten along
# its hanging axis rather than becoming a rigid support strut under the body.
reinforced=(cuff_distance<cage['spacing_m']*.48)|((chain_distance<cage['spacing_m']*.48)&(np.abs(directions@axis)<.35))
cage['reinforced_edges']=edges[reinforced].tolist()
cage['collapse_in_place']=True
cage['unsupported_source_bones']=['Bone_008','Bone_007','Bone_006','Bone_005','Bone_004',
    'Bone_015','Bone_014','Bone_013','Bone_012','Bone_011']
cage['unsupported_source_bones']+=[n for n in names if n.startswith('HQ_Chain_')]
cage['unsupported_min_weight']=.55
cage['embedding']='M14 V19 continuous positive tetrahedral field for complete body and metal; no rigid patches'
(folder/'cage.json').write_text(json.dumps(cage,separators=(',',':')),encoding='utf8')
old=json.loads((PROJECT/'SourceAssets/HeQueBoss20261014/RigV01/SoftCorpse/HeQue/cage.json').read_text('utf8'))
old_nodes=np.array(old['nodes'])
drift=[float(np.linalg.norm(old_nodes[h['nodes']].mean(0)-np.array(h['center']))*100*450/170) for h in old['hardware']]
report=dict(stage='authored',source_vertices=count,soft_nodes=len(nodes),tetrahedra=len(cage['tetrahedra']),
    rigid_patches=len(cage['hardware']),reinforced_edges=len(cage['reinforced_edges']),metal_vertices=len(metal),
    old_rigid_patches=len(drift),old_max_centroid_drift_cm_per_projection=max(drift),
    death_handoff_seconds=0.,runtime_tested=False,rendered=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_CONTINUOUS_CORPSE_V02_AUTHORED '+json.dumps(report),flush=True)
