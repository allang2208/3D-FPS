"""Repair original gill crease weights without replacing the accepted rig."""
import importlib.util
import json
from pathlib import Path
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OLD = ROOT/'RecoveryOriginalV08'
OUT = ROOT/'RecoveryOriginalV09'

def distance_segment(p, a, b):
    axis = b-a
    t = np.clip((p-a)@axis/max(float(axis@axis), 1.e-12), 0, 1)
    return np.linalg.norm(p-a-t[:, None]*axis, axis=1)

def author():
    OUT.mkdir(parents=True, exist_ok=True)
    src = np.load(ROOT/'Authoring/source_mesh.npz')
    regions = np.load(ROOT/'RecoveryOriginalV06/regions/source_regions_original_v06.npz')
    raw = src['positions'].astype(np.float64)
    faces = src['indices'].reshape(-1, 3)
    labels = regions['face_labels']
    weld = regions['source_welded_vertex_ids'].astype(np.int32)
    unique, first = np.unique(weld, return_index=True)
    count = int(weld.max())+1
    scale = 310/(raw[:, 1].max()-raw[:, 1].min())
    points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-raw[:, 1].min()]*scale
    wp = np.zeros((count, 3), dtype=np.float64)
    wp[unique] = points[first]
    record = json.loads((OLD/'original_skin_weights_v08.json').read_text(encoding='utf-8'))
    names = record['bone_names']; namespace = {n:i for i,n in enumerate(names)}
    saved = np.load(OLD/'original_skin_weights_v08.npz')
    original = np.zeros((len(raw), len(names)), np.float32)
    np.put_along_axis(original, saved['bone_indices'], saved['bone_weights'], axis=1)
    wf = weld[faces]
    member = np.zeros((count, 7), dtype=bool)
    for label in range(7):
        member[np.unique(wf[labels == label]), label] = True
    heads = json.loads((OLD/'rig_motion/original_rig_guides.json').read_text(encoding='utf-8'))['bone_heads_cm']
    heads = {n:np.asarray(p) for n,p in heads.items()}
    distances = np.minimum.reduce([distance_segment(wp, heads[a+'_'+s], heads[b+'_'+s])
        for s in ('l','r') for a,b in [('thigh','calf'),('calf','foot'),('foot','ball')]])
    leg_columns = [namespace[a+'_'+s] for s in ('l','r') for a in ('thigh','calf','foot','ball')]
    is_membrane = member[:, 1:].any(axis=1)
    polluted = is_membrane[weld] & (distances[weld] > 20.) & (original[:, leg_columns].sum(axis=1) > .02)
    if polluted.any():
        # Restore these accidental overlay rows from the pre-overlay authoring
        # field; true legs and all human-hand overlays keep the saved V08 rows.
        spec = importlib.util.spec_from_file_location('m07_pre_overlay', Path(__file__).with_name('prepare_original_weights_v08.py'))
        base = importlib.util.module_from_spec(spec); spec.loader.exec_module(base)
        base.OUT = OUT/'pre_overlay'; base.OUT.mkdir(parents=True, exist_ok=True)
        base.solve(ROOT/'RecoveryOriginalV06/regions/source_regions_original_v06.npz', OLD/'rig_motion/original_rig_guides.json')
        restored = np.load(base.OUT/'original_skin_weights_v08.npz')
        replacement = np.zeros((int(polluted.sum()), len(names)), np.float32)
        np.put_along_axis(replacement, restored['bone_indices'][polluted], restored['bone_weights'][polluted], axis=1)
        original[polluted] = replacement
    field = np.zeros((count, len(names)), np.float32)
    np.add.at(field, weld, original)
    field /= np.maximum(np.bincount(weld, minlength=count)[:, None], 1)
    field /= np.maximum(field.sum(axis=1, keepdims=True), 1.e-12)
    leaf_fields = {}
    for label in range(1, 7):
        ids = np.flatnonzero(member[:, label])
        chain = [f'gill_{label:02d}_{i:02d}' for i in (0,1,2)]
        start = heads[chain[0]]
        guide = json.loads((OLD/'rig_motion/original_rig_guides.json').read_text(encoding='utf-8'))
        end = np.asarray(guide['bone_tails_cm'][chain[-1]])
        axis = end-start
        t = np.clip((wp[ids]-start)@axis/max(float(axis@axis),1.e-10),0,.999999)*2
        low = np.floor(t).astype(np.int32)
        own = np.zeros((len(ids), len(names)), np.float32)
        rows = np.arange(len(ids))
        own[rows, np.asarray([namespace[n] for n in chain])[low]] = 1-(t-low)
        own[rows, np.asarray([namespace[n] for n in chain])[np.minimum(low+1,2)]] += t-low
        leaf_fields[label] = (ids, own)
    leaf_count = member[:,1:].sum(axis=1)
    shared = (leaf_count>1) & ~member[:,0]
    common = np.zeros_like(field)
    for label,(ids,own) in leaf_fields.items():
        common[ids] += own
    common /= np.maximum(leaf_count[:,None],1)
    # Every fold intersection gets ONE common field before any leaf writes.
    # Nearby surface vertices transition from that field to their own chain.
    field[shared] = common[shared]
    transitions = []
    fold_distances = np.full((count,7),np.inf,np.float32)
    for label,(ids,own) in leaf_fields.items():
        panel_faces = wf[labels == label]
        edges = np.concatenate([panel_faces[:,[0,1]],panel_faces[:,[1,2]],panel_faces[:,[2,0]]])
        edges.sort(axis=1); edges = np.unique(edges,axis=0)
        edges = edges[edges[:,0]!=edges[:,1]]
        local = np.full(count,-1,np.int32); local[ids] = np.arange(len(ids))
        ee = local[edges]
        lengths = np.linalg.norm(wp[edges[:,0]]-wp[edges[:,1]],axis=1)
        graph = coo_matrix((np.r_[lengths,lengths],(np.r_[ee[:,0],ee[:,1]],np.r_[ee[:,1],ee[:,0]])),shape=(len(ids),len(ids))).tocsr()
        seeds = np.flatnonzero(member[ids,0] | (leaf_count[ids]>1))
        if not len(seeds): raise RuntimeError('Original gill has no anatomical fold attachment: '+str(label))
        dist,_,origins = dijkstra(graph,directed=False,indices=seeds,min_only=True,return_predecessors=True)
        fold_distances[ids,label]=dist
        safe = origins>=0
        anchored = own.copy()
        anchored[safe] = field[ids[origins[safe]]]
        alpha = np.clip(dist/18.,0,1); alpha = alpha*alpha*(3-2*alpha)
        mixture = anchored*(1-alpha[:,None])+own*alpha[:,None]
        editable = ~member[ids,0] & (leaf_count[ids]==1)
        field[ids[editable]] = mixture[editable]
        transitions.append({'panel':label,'shared_fold_vertices':int((leaf_count[ids]>1).sum()),'transition_cm':18.})
    best = np.argpartition(field,-8,axis=1)[:,-8:]
    values = np.take_along_axis(field,best,axis=1)
    order = np.argsort(-values,axis=1)
    best = np.take_along_axis(best,order,axis=1).astype(np.int16)
    values = np.take_along_axis(values,order,axis=1)
    values /= np.maximum(values.sum(axis=1,keepdims=True),1.e-12)
    np.savez_compressed(OUT/'gill_skin_weights_v09.npz',bone_indices=best[weld],bone_weights=values[weld],
        source_welded_vertex_ids=weld,membrane_source_membership=is_membrane[weld],leg_overlay_spill_rows=polluted,
        fold_source_distance_cm=fold_distances[weld])
    record.update({'revision':'OriginalV09','method':'Single common fold field and original-edge 18 cm transitions; corrected stray leg overlay; welded UV copies unified.',
        'source_polluted_leg_rows_restored':int(polluted.sum()),'shared_nonbody_fold_welds':int(shared.sum()),
        'fold_transitions':transitions,'bone_count':len(names),'body_leg_hand_source':'Saved V08 rows except identified membrane overlay spill and coincident UV seam normalization',
        'tested':False,'rendered':False})
    (OUT/'gill_skin_weights_v09.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M07_V09_COMMON_GILL_FOLD_WEIGHTS_AUTHORED '+str(OUT),flush=True)

if __name__=='__main__': author()
