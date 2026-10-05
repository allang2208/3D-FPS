"""Replace remote chain ownership of low support patches with local skin weights."""
from pathlib import Path
import json, struct
import numpy as np
from scipy.spatial import cKDTree
from scipy.sparse import coo_matrix, diags
from scipy.sparse.linalg import splu

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004');OUT=ROOT/'ProductionV15'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
source=np.load(ROOT/'ProductionV11/Records/hardware_source.npz')
components=np.load(ROOT/'ProductionV11/Records/hardware_components.npz')
current=np.load(OUT/'Records/contact_source.npz')
p,faces=source['p'],source['f'];weld=components['weld'];mf=faces[source['metal']]
labels=components['metal_face_components'];sizes=components['component_sizes']
major=np.flatnonzero(sizes>=1000)
major_ids=np.unique(mf[np.isin(labels,major)])
tree=cKDTree(p[major_ids]);orphans=[];orphan_vertices=[]
for cid,size in enumerate(sizes):
    if cid in major:continue
    ids=np.unique(mf[labels==cid]);points=p[ids]
    distance,_=tree.query(points)
    # Material tint alone is not a chain attachment. These small low patches
    # are separated from the actual chain by at least an 8 cm median gap.
    if points[:,2].max()<.45 and np.median(distance)>.08:
        orphans.append({'component':cid,'triangles':int(size),'median_chain_gap_m':float(np.median(distance)),
                        'source_center':points.mean(0).tolist(),'old_contact_center':current['q'][ids].mean(0).tolist()})
        orphan_vertices.extend(ids)
orphan_vertices=np.unique(orphan_vertices)
_,first=np.unique(weld,return_index=True);points=p[first];n=len(points)
removed=np.unique(weld[orphan_vertices]);seed=np.unique(weld[np.unique(mf)])
kept=np.setdiff1d(seed,removed)
distance,_=cKDTree(points[removed]).query(points)
keep_distance,_=cKDTree(points[kept]).query(points)
# Include the old 6 cm contaminated transition plus a 2 cm clean boundary.
mask=(distance<.08)&(distance<keep_distance)
tri=weld[faces]
rows=tri.ravel();cols=tri[:,[1,2,0]].ravel();valid=rows!=cols
rows,cols=rows[valid],cols[valid]
strength=1./np.maximum(np.linalg.norm(points[rows]-points[cols],axis=1),.002)
graph=coo_matrix((np.r_[strength,strength],(np.r_[rows,cols],np.r_[cols,rows])),shape=(n,n)).tocsr()
old_b=current['bones'][first];old_w=current['weights'][first];groups=current['groups'].tolist()
old=coo_matrix((old_w.ravel(),(np.repeat(np.arange(n),4),old_b.ravel())),shape=(n,len(groups))).tocsr()
# The original four-slot skin also switches abruptly between base and the
# fourth root support. Include those existing split-weight ridges in the same
# local repair, so the border cannot inherit another protruding triangle.
root_columns=[i for i,name in enumerate(groups) if name.startswith('rootfan_') or name.startswith('roottoe_')]
root_weight=np.asarray(old[:,root_columns].sum(1)).ravel()
edge_length=np.linalg.norm(points[rows]-points[cols],axis=1)
posed=current['q'][first]
posed_length=np.linalg.norm(posed[rows]-posed[cols],axis=1)
ridge=(np.maximum(points[rows,2],points[cols,2])<.55)&(np.minimum(root_weight[rows],root_weight[cols])>.025)
ridge&=(edge_length>.003)&(posed_length>.025)&(posed_length>4*edge_length)
ridge_seeds=np.unique(np.r_[rows[ridge],cols[ridge]])
ridge_distance,_=cKDTree(points[ridge_seeds]).query(points)
mask|=ridge_distance<.045
mask[kept]=False
ids=np.flatnonzero(mask)
adjacent=graph[ids];interior=adjacent[:,ids]
system=diags(np.asarray(adjacent.sum(1)).ravel())-interior
boundary=(adjacent@old-interior@old[ids]).toarray()
# Harmonic continuation follows connected tissue, fixes the untouched border,
# and carries coincident material/UV copies through one welded surface solution.
solution=splu(system.tocsc()).solve(boundary)
solution=np.maximum(solution,0);solution/=np.maximum(solution.sum(1,keepdims=True),1.e-12)
bone_ids=np.argsort(solution,axis=1)[:,-8:][:,::-1]
weights=np.take_along_axis(solution,bone_ids,axis=1)
dropped=1.-weights.sum(1)
weights/=np.maximum(weights.sum(1,keepdims=True),1.e-12)
# Quantize once for Blender and UE; retain eight slots in the local patch.
quant=np.rint(weights*65535).astype(np.int32);quant[:,0]+=65535-quant.sum(1)
weights=quant.astype(np.float32)/65535.
payload=np.zeros((len(ids),19),dtype='<f4');payload[:,:3]=points[ids]
payload[:,3:11]=bone_ids;payload[:,11:19]=weights
with (OUT/'Exports/support_skin.bin').open('wb') as stream:
    stream.write(struct.pack('<i',len(ids)));stream.write(payload.tobytes())
(OUT/'Exports/support_bones.json').write_text(json.dumps(groups),encoding='utf8')
lookup=np.full(n,-1,np.int32);lookup[ids]=np.arange(len(ids));changed=np.flatnonzero(mask[weld]);mapped=lookup[weld[changed]]
np.savez(OUT/'Records/support_skin.npz',changed=changed,bones=bone_ids[mapped],weights=weights[mapped],orphan_vertices=orphan_vertices)

# The requested diagnosis is limited to the reported downstroke defect.
q=current['q'].copy();skin=current['skin'];q[changed]=0
for slot in range(8):
    for bone in np.unique(bone_ids[:,slot]):
        active=np.flatnonzero((bone_ids[mapped,slot]==bone)&(weights[mapped,slot]>0))
        vi=changed[active]
        q[vi]+=(p[vi]@skin[bone,:3,:3].T+skin[bone,:3,3])*weights[mapped[active],slot,None]
affected=np.any(mask[tri],axis=1)
ratios=[[],[]];lengths=[[],[]]
for a,b in ((0,1),(1,2),(2,0)):
    old_length=np.linalg.norm(p[faces[:,a]]-p[faces[:,b]],axis=1)
    valid=affected&(old_length>.003)
    for i,posed in enumerate((current['q'],q)):
        length=np.linalg.norm(posed[faces[valid,a]]-posed[faces[valid,b]],axis=1)
        ratios[i].append(length/old_length[valid]);lengths[i].append(length)
for entry in orphans:
    patch=np.unique(mf[labels==entry['component']]);entry['new_contact_center']=q[patch].mean(0).tolist()
report={'complete':True,'orphan_patches':orphans,'changed_source_vertices':len(changed),'changed_welded_vertices':len(ids),
        'local_max_influences':8,'discarded_weight_max':float(dropped.max()),'geometry_removed':0,
        'contact_diagnosis':{'frame':36,'seconds':1.2,'max_edge_ratio_before':float(np.concatenate(ratios[0]).max()),
            'max_edge_ratio_after':float(np.concatenate(ratios[1]).max()),
            'max_edge_length_before_m':float(np.concatenate(lengths[0]).max()),
            'max_edge_length_after_m':float(np.concatenate(lengths[1]).max()),
            'orphan_max_height_before_m':float(current['q'][orphan_vertices,2].max()),
            'orphan_max_height_after_m':float(q[orphan_vertices,2].max())},
        'animation_changed':False,'death_shapes_changed':False,'runtime_tested':False,'rendered':False}
remaining=[]
for a,b in ((0,1),(1,2),(2,0)):
    old_length=np.linalg.norm(p[faces[:,a]]-p[faces[:,b]],axis=1)
    new_length=np.linalg.norm(q[faces[:,a]]-q[faces[:,b]],axis=1)
    ratio=new_length/np.maximum(old_length,1.e-6)
    eligible=np.flatnonzero(affected&(old_length>.003))
    for fi in eligible[np.argsort(ratio[eligible])[-4:]]:
        vv=faces[fi]
        remaining.append({'face':int(fi),'ratio':float(ratio[fi]),'source':p[vv].mean(0).round(4).tolist(),
                          'target':q[vv].mean(0).round(4).tolist(),'edge_m':float(new_length[fi]),
                          'changed':mask[weld[vv]].tolist()})
report['remaining_edges']=sorted(remaining,key=lambda r:-r['ratio'])[:6]
(OUT/'Records/support_repair.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps({k:v for k,v in report.items() if k!='orphan_patches'},indent=2),flush=True)
