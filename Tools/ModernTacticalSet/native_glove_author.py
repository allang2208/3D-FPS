"""Fit the cloth and its trim via homologous points on the actual bare hand skins."""
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree
from trimesh.triangles import closest_point, points_to_barycentric

from native_glove_profile import P,SET,R,RIG,SOURCE_FILE
FINGERS = ('thumb','index','middle','ring','pinky')

def read(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def unit(x):
    return x / np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-12)

def hand_zone(weights):
    mass = {}
    for name, weight in weights.items():
        region = name.split('_')[0]
        region = region if region in FINGERS else 'palm'
        key = (name[-1],region)
        mass[key] = mass.get(key,0) + weight
    return max(mass,key=mass.get)

def corners_key(uv):
    return tuple(sorted(map(tuple,uv)))

def correspondence(source, target):
    # Identical native atlas across both grips. Pair triangles by UV triplet and
    # reorder corners; UE may split a seam into a different number of vertices.
    f = np.asarray(source['triangles'])
    tf = np.asarray(target['triangles'])
    suv = np.rint(np.asarray(source['uv'])*100000).astype(np.int32)
    tuv = np.rint(np.asarray(target['uv'])*100000).astype(np.int32)
    index = {}
    for j,uv in enumerate(tuv):
        index.setdefault(corners_key(uv),[]).append(j)
    points = np.asarray(source['positions'])
    target_points = np.asarray(target['positions'])
    sf, dst = [], []
    for i,uv in enumerate(suv):
        zone = hand_zone(source['weights'][f[i,0]])[0]
        for j in index.get(corners_key(uv),[]):
            if hand_zone(target['weights'][tf[j,0]])[0] != zone:
                continue
            order = [np.argmin(np.sum(abs(tuv[j]-x),axis=1)) for x in uv]
            row = tf[j,order]
            if len(set(row)) != 3:
                continue
            for verts in (points[f[i]],target_points[row]):
                if np.linalg.norm(np.cross(verts[1]-verts[0],verts[2]-verts[0]))<1e-6:
                    break
            else:
                sf.append(f[i])
                dst.append(row)
                break
    return np.array(sf),np.array(dst)

def frames(tri):
    x = unit(tri[:,1]-tri[:,0])
    z = unit(np.cross(x,tri[:,2]-tri[:,0]))
    return np.stack([x,np.cross(z,x),z],axis=2)

def sample(source, target, glove):
    sf,tf = correspondence(source,target)
    sp = np.array(source['positions'])
    tp = np.array(target['positions'])
    gp = np.array(glove['positions'])
    face_zones = [hand_zone(source['weights'][i]) for i in range(len(sp))]
    zones = np.array([f'{s}/{r}' for s,r in face_zones])
    bone_names = {b['index']:b['name'] for b in glove['bones']}
    bindings = [{bone_names[i]:w for i,w in ws} for ws in glove['weights']]
    desired = np.array(['/'.join(hand_zone(ws)) for ws in bindings])
    chosen = np.zeros(len(gp),int)
    bary = np.zeros((len(gp),3))
    for region in np.unique(desired):
        ids = np.where(desired==region)[0]
        eligible = np.flatnonzero(np.any(zones[sf]==region,axis=1))
        tree = cKDTree(sp[sf[eligible]].mean(1))
        for start in range(0,len(ids),512):
            chunk = ids[start:start+512]
            idx = eligible[tree.query(gp[chunk],k=24)[1]]
            nearby = closest_point(sp[sf[idx]].reshape(-1,3,3),np.repeat(gp[chunk],24,axis=0)).reshape(-1,24,3)
            best = np.argmin(np.linalg.norm(nearby-gp[chunk,None,:],axis=2),axis=1)
            winners = idx[np.arange(len(chunk)),best]
            chosen[chunk] = winners
            b = points_to_barycentric(sp[sf[winners]],nearby[np.arange(len(chunk)),best]).clip(0,1)
            bary[chunk] = b/b.sum(1,keepdims=True)
    a,b = sf[chosen],tf[chosen]
    ps = np.einsum('ni,nij->nj',bary,sp[a])
    pt = np.einsum('ni,nij->nj',bary,tp[b])
    rotation = frames(tp[b])@np.transpose(frames(sp[a]),(0,2,1))
    pos = pt+np.einsum('nij,nj->ni',rotation,gp-ps)
    return pos,b,bary,rotation

def extend_cuff(pos,rows,bary,target):
    """Carry the proximal band under the R4 shotgun sleeve along native skin."""
    p = np.array(target['positions'])
    all_faces = np.array(target['triangles'])
    anchors = np.einsum('ni,nij->nj', bary, p[rows])
    for side in ('l', 'r'):
        wrist = np.array(target['bones']['hand_'+side]['position'])
        axis = unit(wrist-np.array(target['bones']['lowerarm_'+side]['position']))
        station = -(anchors-wrist)@axis
        ids = np.flatnonzero((station>.4)&(np.linalg.norm(anchors-wrist,axis=1)<9))
        taper = np.clip((station[ids]-.4)/2.35,0,1)
        length = 3.3*taper*taper*(3-2*taper)
        guess = anchors[ids]-length[:,None]*axis
        # The target is projected to its own forearm so width and skin weights
        # follow the real wrist throughout the new overlap, including the strap.
        permitted = np.linalg.norm(p[all_faces].mean(1)-wrist,axis=1)<11
        f = all_faces[permitted]
        tree = cKDTree(p[f].mean(1))
        for start in range(0,len(ids),512):
            ix = ids[start:start+512]
            g = guess[start:start+512]
            cand = f[tree.query(g,k=24)[1]]
            near = closest_point(p[cand].reshape(-1,3,3),np.repeat(g,24,axis=0)).reshape(-1,24,3)
            best = np.argmin(np.linalg.norm(near-g[:,None],axis=2),axis=1)
            hit = near[np.arange(len(ix)),best]
            rows[ix] = cand[np.arange(len(ix)),best]
            b = points_to_barycentric(p[rows[ix]],hit).clip(0,1)
            bary[ix] = b/b.sum(1,keepdims=True)
            pos[ix] += hit-anchors[ix]

def transport():
    source = read(SET/'CombatShirtR3/CuffRepairR1/Read/Native_M4.json')
    target = read(R/'Read'/(RIG+'_Jason.json'))
    glove = read(SET/'CombatShirtR4/Authored/gloves_M4.json')
    previous = read(R/'Read/R4.json')
    pos,rows,bary,rotation = sample(source,target,glove)
    if RIG=='Super90':
        extend_cuff(pos,rows,bary,target)
    names = {n:v['index'] for n,v in target['bones'].items()}
    weights = []
    for inds,factors in zip(rows,bary):
        total = {}
        for vi,factor in zip(inds,factors):
            for n,w in target['weights'][vi].items():
                total[names[n]] = total.get(names[n],0) + w*factor
        pairs = sorted(((i,w) for i,w in total.items() if w>1e-7),key=lambda x:-x[1])[:8]
        den = sum(w for _,w in pairs)
        weights.append([[i,w/den] for i,w in pairs])
    faces = np.array(glove['triangles'])
    norms = unit(np.einsum('fvij,fvj->fvi',rotation[faces],np.array(glove['normals'])))
    out = dict(source=previous['source'],skeleton=target['skeleton'],positions=pos.tolist(),
               triangles=glove['triangles'],weights=weights,normals=norms.tolist(),
               uv=glove['uv'],materials=previous['materials'],material_slots=previous['material_slots'],
               triangle_materials=glove['triangle_materials'])
    if RIG=='M16':
        # The current right-hand glove already fits the M16. Keep its complete
        # installed surface, bindings, UV seams, materials and corner normals.
        parts=[]
        for data,side in [(out,'l'),(previous,'r')]:
            ws=data['weights']
            wnames={v['index']:n for n,v in target['bones'].items()}
            named=[{wnames[i]:w for i,w in row} for row in ws] if isinstance(ws[0],list) else ws
            tags=np.array([hand_zone(row)[0] for row in named])
            all_tri=np.array(data['triangles'])
            idx=np.flatnonzero((tags[all_tri]==side).all(1))
            used,inv=np.unique(all_tri[idx],return_inverse=True)
            parts.append(dict(positions=np.array(data['positions'])[used].tolist(),
                              triangles=inv.reshape(-1,3), weights=[[[names[n],w] for n,w in named[i].items()] for i in used],
                              **{f:np.array(data[f])[idx].tolist() for f in ('triangle_materials','uv','normals')}))
        offset=len(parts[0]['positions'])
        parts[0]['triangles']=parts[0]['triangles'].tolist()
        parts[1]['triangles']=(parts[1]['triangles']+offset).tolist()
        for field in parts[0]:
            out[field]=parts[0][field]+parts[1][field]
    SOURCE_FILE.write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
    np.savez_compressed(R/'native_anchors.npz',indices=rows,bary=bary)

if __name__=='__main__':
    transport()
