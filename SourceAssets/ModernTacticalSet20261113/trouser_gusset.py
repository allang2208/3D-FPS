"""Tailor the shared crotch in native centimetres, before body and cuff derivation."""
import math
from collections import defaultdict

import numpy as np


def ease(low, high, x):
    t = np.clip((x - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def mix_weights(left, right, fraction):
    totals = defaultdict(float)
    for row, factor in ((left, 1 - fraction), (right, fraction)):
        for bone, weight in row:
            totals[int(bone)] += weight * factor
    pairs = sorted(((i, w) for i, w in totals.items() if w > 1e-7), key=lambda p: -p[1])[:8]
    total = sum(w for _, w in pairs)
    return [[i, w / total] for i, w in pairs]


def tailor(data, bones, cut=False):
    p = np.array(data['positions'], dtype=float)
    x, y, z = p.T.copy()
    # The existing left and right leg rings meet on this sewn U-shaped saddle.
    yc = .8
    saddle = 80 - 8.5 * np.sqrt(np.maximum(0, 1 - ((y - yc) / 13.8) ** 2))
    below = np.maximum(saddle - z, 0)
    center = (1 - ease(2.5, 13, abs(x))) * ease(60, 68, z) * (1 - ease(82, 91, z))
    # Lower the center rise and add length around the seat and front fork.
    p[:, 2] -= 1.15 * center * np.exp(-((z - saddle) / 5.8) ** 2)
    p[:, 1] += .48 * center * np.tanh((y - yc) / 5)
    seam_support = (1 - ease(0, 8, abs(x))) * (1 - ease(0, 5.5, below))
    hip = .87 * ease(67, 89, z)
    hip += (1 - hip) * .65 * seam_support
    band = .12 + 4.8 * (1 - ease(.4, 4.5, below))
    share = ease(-band, band, x)
    for i in np.flatnonzero(center):
        weights = [(bones['pelvis'], hip[i]), (bones['thigh_l'], (1 - hip[i]) * share[i]),
                   (bones['thigh_r'], (1 - hip[i]) * (1 - share[i]))]
        data['weights'][i] = mix_weights(data['weights'][i], weights, center[i])
    data['positions'] = p.tolist()
    if not cut:
        return

    shell = data['parts'][0]
    cloth_faces = shell['triangles']
    faces = np.asarray(data['triangles'][:cloth_faces])
    # Relax the original pinched join over its connected one-ring neighborhood.
    # The two legs exchange neighbors only where their existing seam is welded.
    for _ in range(3):
        acc = np.zeros_like(p)
        count = np.zeros(len(p))
        for k in range(3):
            np.add.at(acc, faces[:, k], p[faces[:, (k+1)%3]] + p[faces[:, (k-1)%3]])
            np.add.at(count, faces[:, k], 2)
        amount = .30 * center * np.exp(-((z - saddle) / 4.5) ** 2) * (count > 0)
        p += (acc / np.maximum(count[:, None], 1) - p) * amount[:, None]
    data['positions'] = p.tolist()
    # A continuous cut line goes down one inner thigh, under the seat and up
    # the other thigh. Split crossed edges once and share them between fabrics.
    across = np.sign(x) * np.hypot(x, below)
    field = (abs(across)/5.6)**1.5 + (abs(y-yc)/11.8)**1.5 + (np.maximum(z-saddle,0)/3.0)**2 - 1
    normal = np.zeros_like(p)
    tri = p[faces]
    cross = -np.cross(tri[:, 1]-tri[:, 0], tri[:, 2]-tri[:, 0])
    for k in range(3):
        np.add.at(normal, faces[:, k], cross)
    normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-12)
    # Continuous grain on the seat and leg, with UV wrap at the inner/back seam.
    rise = ease(66, 81, z)
    axis_x = np.interp(z, [14,45,66,81], [14.7,12.2,10.5,9.8]) * (1-rise)
    axis_y = np.interp(z, [14,45,66,81], [-2.6,.1,2.3,.8])
    circumference = 2 * math.pi * np.interp(z, [14,45,66,81], [4.7,7.3,9.55,14.5])
    gus_uv = np.column_stack((across / 8, (y-yc)/8))
    cut_edges = {}
    result = {key: [] for key in ('triangles','normals','uv','triangle_materials')}

    def intersection(a, b):
        ai, an, au, ag = a
        bi, bn, bu, bg = b
        t = field[ai] / (field[ai]-field[bi])
        if t < 1e-8:return a
        if t > 1 - 1e-8:return b
        key = tuple(sorted((ai,bi)))
        if key not in cut_edges:
            cut_edges[key] = len(data['positions'])
            data['positions'].append((p[ai]+(p[bi]-p[ai])*t).tolist())
            data['weights'].append(mix_weights(data['weights'][ai],data['weights'][bi],t))
        n = an + (bn-an)*t
        return cut_edges[key], n/max(np.linalg.norm(n),1e-12), au+(bu-au)*t, ag+(bg-ag)*t

    def emit(poly, gusset, material):
        for k in range(1,len(poly)-1):
            corners = [poly[0],poly[k],poly[k+1]]
            ids = [c[0] for c in corners]
            if len(set(ids)) != 3:continue
            result['triangles'].append(ids)
            result['normals'].append([c[1].tolist() for c in corners])
            result['uv'].append([c[3 if gusset else 2].tolist() for c in corners])
            result['triangle_materials'].append(5 if gusset else material)

    for fi, f in enumerate(faces):
        side = 1 if x[f].sum() >= 0 else -1
        theta = np.arctan2(x[f] - side*axis_x[f], y[f]-axis_y[f])
        theta = theta[0] + (theta-theta[0]+math.pi)%(2*math.pi)-math.pi
        chart = np.column_stack((theta*circumference[f]/(math.tau*8),z[f]/8))
        normals = np.array(data['normals'][fi])
        normals += (normal[f]-normals)*center[f,None]
        normals /= np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
        vertices = [(int(v),n,uv,gus_uv[v]) for v,n,uv in zip(f,normals,chart)]
        inside = field[f] < 0
        if inside.all() or not inside.any():
            emit(vertices,inside.all(),1)
            continue
        for take_inner in (True,False):
            polygon=[]
            for k, a in enumerate(vertices):
                b=vertices[(k+1)%3]
                if inside[k] == take_inner:polygon.append(a)
                if inside[k] != inside[(k+1)%3]:polygon.append(intersection(a,b))
            emit(polygon,take_inner,1)
    data['authored_cloth_faces']=len(result['triangles'])
    for key, sequence in result.items():
        data[key] = sequence + data[key][cloth_faces:]
