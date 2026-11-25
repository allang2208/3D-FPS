"""Tailor the surviving robe yoke to the keeper's own weighted neck, in UE centimetres."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


def shoulder_panel(robe, slot):
    faces = np.asarray(robe["triangles"])
    selected = np.asarray(robe["triangle_materials"]) == slot
    p = np.asarray(robe["positions"])
    xyz, welded = np.unique(np.round(p[faces[selected]], 4).reshape(-1, 3), axis=0, return_inverse=True)
    tri = welded.reshape(-1, 3)
    edges = np.roll(tri, 1, axis=1)
    graph = coo_matrix((np.ones(tri.size), (tri.ravel(), edges.ravel())), shape=(len(xyz), len(xyz)))
    _, labels = connected_components(graph, directed=False)
    yoke = labels[xyz[:, 2].argmax()]
    keep = ~selected
    keep[selected] = labels[tri[:, 0]] == yoke
    return keep


def neck_section(head, direction, origin, face_points, face_ids):
    # Horizontal ray from inside the neck. Barycentric weights at the hit
    # transfer the skin's actual bone blend to the rolled edge.
    a, b, c = face_points.transpose(1, 0, 2)
    ab, ac = b-a, c-a
    h = np.cross(direction, ac)
    det = np.einsum("ij,ij->i", ab, h)
    inv = np.divide(1., det, out=np.zeros_like(det), where=np.abs(det) > 1e-8)
    s = origin-a
    u = inv*np.einsum("ij,ij->i", s, h)
    q = np.cross(s, ab)
    v = inv*(q @ direction)
    dist = inv*np.einsum("ij,ij->i", ac, q)
    valid = (np.abs(det)>1e-8) & (u>=-1e-7) & (v>=-1e-7) & (u+v<=1.0000001) & (dist>0)
    if not valid.any():
        raise ValueError("The fitted neckline leaves the captured head surface")
    i = np.argmin(np.where(valid, dist, np.inf))
    weights = {}
    for vert, mix in zip(face_ids[i], [1-u[i]-v[i], u[i], v[i]]):
        for joint, value in zip(head["j"][vert], head["w"][vert]):
            if value > 0:
                weights[joint] = weights.get(joint, 0.) + max(0., mix)*value
    return origin+direction*dist[i], weights


def finish_neckline(path, head_path):
    with np.load(path) as data:
        dress = dict(data)
    with np.load(head_path) as data:
        head = dict(data)
    p, tri = dress["p"], dress["tri"]
    slot = dress["mats"].tolist().index("NeckLinen")
    cloth = dress["ids"] == slot
    # Sew only the yoke and its coincident edges. Keep unrelated layered panels separate.
    _, first, inverse = np.unique(np.round(p, 4), axis=0, return_index=True, return_inverse=True)
    remap = np.arange(len(p))
    touching = np.isin(inverse, inverse[tri[cloth]].ravel())
    remap[touching] = first[inverse[touching]]
    tri = remap[tri]
    yoke = tri[cloth]
    dress["uv"][cloth] = p[yoke, :2]/4.
    edges = np.stack((yoke, np.roll(yoke, -1, axis=1)), axis=-1).reshape(-1, 2)
    _, ix, count = np.unique(np.sort(edges, axis=1), axis=0, return_index=True, return_counts=True)
    boundary = edges[ix[count == 1]]
    graph = coo_matrix((np.ones(len(boundary)), boundary.T), shape=(len(p), len(p)))
    _, label = connected_components(graph, directed=False)
    loops = [boundary[label[boundary[:, 0]] == k] for k in np.unique(label[boundary[:, 0]])]
    if len(loops) != 2:
        raise ValueError(f"Expected inner and outer robe yoke seams, found {len(loops)}")
    inner = min(loops, key=lambda e: np.ptp(p[e[:, 0], 0]))
    ring = np.unique(inner)
    head_tri = head["tri"][head["ids"] == head["mats"].tolist().index("KeeperFace0")]
    hp = head["p"][head_tri]
    low = hp[:, :, 2].min()
    bottom = head["p"][np.unique(head_tri)]
    bottom = bottom[bottom[:, 2] < low+.09]
    center = (bottom.min(axis=0) + bottom.max(axis=0))/2
    top = np.maximum(p[ring, 2]+.25, low+.75)
    band = (hp[:, :, 2].min(axis=1) <= top.max()+.01) & (hp[:, :, 2].max(axis=1) >= top.min()-.01)
    hp, head_tri = hp[band], head_tri[band]
    rows, jw, ww = [], [], []
    for vi, z in zip(ring, top):
        delta = p[vi, :2]-center[:2]
        direction = np.r_[delta/np.linalg.norm(delta), 0.]
        skin, skin_weights = neck_section(head, direction, np.r_[center[:2], z], hp, head_tri)
        outer = skin + .28*direction
        rows.extend([.5*(p[vi]+outer)+[0,0,.12], outer, skin-.18*direction-[0,0,.12]])
        original = dict(zip(dress["j"][vi][dress["w"][vi]>0],dress["w"][vi][dress["w"][vi]>0]))
        for t in (.5, 1., 1.):
            weights = {j: (1-t)*original.get(j,0.)+t*skin_weights.get(j,0.) for j in original.keys()|skin_weights.keys()}
            pairs = sorted(((w,j) for j,w in weights.items() if w>1e-7), reverse=True)[:8]
            total = sum(w for w,j in pairs)
            jw.append([j for w,j in pairs] + [0]*(8-len(pairs)))
            ww.append([w/total for w,j in pairs] + [0.]*(8-len(pairs)))
    current = np.arange(len(p))
    caps = []
    for level in range(3):
        next_ring = np.full(len(p), -1)
        next_ring[ring] = len(p) + 3*np.arange(len(ring)) + level
        a,b = inner.T
        caps.extend([np.stack((current[b],current[a],next_ring[a]),axis=1),
                     np.stack((current[b],next_ring[a],next_ring[b]),axis=1)])
        current = next_ring
    caps = np.concatenate(caps)
    xyz = np.vstack((p, rows))
    n = -np.cross(xyz[caps[:,1]]-xyz[caps[:,0]], xyz[caps[:,2]]-xyz[caps[:,0]])
    smooth = np.zeros_like(xyz)
    for col in caps.T:
        np.add.at(smooth, col, n)
    smooth /= np.maximum(np.linalg.norm(smooth,axis=1,keepdims=True),1e-10)
    dress.update(p=xyz, tri=np.vstack((tri, caps)), w=np.vstack((dress["w"], ww)),
                 j=np.vstack((dress["j"], jw)), ids=np.r_[dress["ids"], np.full(len(caps), slot)],
                 uv=np.concatenate((dress["uv"], xyz[caps, :2]/4.)), n=np.concatenate((dress["n"], smooth[caps])))
    np.savez(path, **dress)
