"""Constrain the middle of a skinned strand against its animated carrier in mesh space."""
import numpy as np
from numba import njit

@njit
def project_arc(points, rest_tail, wall, roof):
    fitted = points.copy()
    lengths = np.sqrt(np.sum((points[1:]-points[:-1])**2,axis=1))
    # The final two spans lead into the authored top seam. Move with the carrier.
    fitted[6:] = points[-1] + rest_tail - rest_tail[-1]
    span = np.linalg.norm(fitted[6] - fitted[0])
    if span > lengths[:6].sum() * .985:
        fitted[6] = fitted[0] + (fitted[6]-fitted[0]) * (lengths[:6].sum()*.985/span)
    for iteration in range(85):
        for step in range(6):
            i = step if iteration % 2 else 5-step
            edge = fitted[i+1] - fitted[i]
            length = np.linalg.norm(edge)
            if length < 1e-6:continue
            correction = edge*(1-lengths[i]/length)
            movable_a = i != 0
            movable_b = i+1 != 6
            if movable_a:fitted[i] += correction*(.5 if movable_b else 1.)
            if movable_b:fitted[i+1] -= correction*(.5 if movable_a else 1.)
        for i in range(6):
            for frac in (.0,.25,.5,.75,1.):
                p = fitted[i]*(1-frac) + fitted[i+1]*frac
                dx, dz = p[0] - wall, roof - p[2]
                if dx <= 0 or dz <= 0:continue
                a = 1-frac if i != 0 else 0.
                b = frac if i+1 != 6 else 0.
                denom = a*a + b*b
                if denom < .001:continue
                axis = 0 if dx < dz else 2
                shift = (-dx if axis==0 else dz) / denom
                fitted[i,axis] += a*shift
                fitted[i+1,axis] += b*shift
    return fitted

def rigid_alignment(start, destination, old_tangent, new_tangent):
    a, b = old_tangent[[0,2]], new_tangent[[0,2]]
    angle = np.arctan2(a[1]*b[0]-a[0]*b[1], a @ b)
    c,s = np.cos(angle),np.sin(angle)
    rot = np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return np.vstack((destination-rot@start,[angle,0.,0.]))

def fit_strand(mats, idle, names, dominant, verts):
    result = {}
    for prefix in ("","New_"):
        box_id = names.index(prefix+"PKM_Box")
        parts = [prefix+f"PKM_Belt_{i:02d}" for i in range(9)]
        links = [prefix+f"PKM_Belt_Link_{i:02d}" for i in range(8)]
        local_centers = np.asarray([np.r_[verts[dominant==names.index(n)].mean(axis=0),1.] for n in parts])
        box_geo = verts[dominant==box_id]
        wall = box_geo[:,0].min() - .84
        roof = box_geo[:,2].max() + .84
        ids = [names.index(n) for n in parts]
        local = np.linalg.inv(mats[:,box_id:box_id+1]) @ mats[:,ids]
        centers = (local @ local_centers[...,None])[...,:3,0]
        old_names = [names.index(n.removeprefix("New_")) for n in parts]
        old_center = np.asarray([np.r_[verts[dominant==j].mean(axis=0),1.] for j in old_names])
        rest = ((np.linalg.inv(idle[names.index("PKM_Box")]) @ idle[old_names]) @ old_center[...,None])[:,:3,0]
        for n in parts+links:result[n] = np.zeros((len(mats),2,3))
        for k,p in enumerate(centers):
            # The idle tail already passes through its seam. Only the drooping side needs routing.
            drop = (rest[7,2]-rest[8,2]) - (p[7,2]-p[8,2])
            weight = np.clip((drop-.025)/.34,0,1)
            if weight == 0:continue
            fitted = project_arc(p,rest[6:],wall,roof)
            q = p + (fitted-p)*(weight*weight*(3-2*weight))
            for i,n in enumerate(parts):
                a,b = max(0,i-1), min(8,i+1)
                result[n][k] = rigid_alignment(p[i],q[i],p[b]-p[a],q[b]-q[a])
            for i,n in enumerate(links):
                result[n][k] = rigid_alignment((p[i]+p[i+1])/2,(q[i]+q[i+1])/2,
                                               p[i+1]-p[i],q[i+1]-q[i])
    return result

def as_matrix(values):
    offsets, angles = values[:,0], values[:,1,0]
    c, s = np.cos(angles),np.sin(angles)
    a = np.broadcast_to(np.eye(4),(len(values),4,4)).copy()
    a[:,0,0],a[:,0,2],a[:,2,0],a[:,2,2] = c,s,-s,c
    a[:,:3,3] = offsets
    return a
