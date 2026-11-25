"""Cut six skirt panels on the assembled lower garment, in centimetres."""
import numpy as np


def skirt_angle(p):
    # Cylindrical join at the centre back. Equalise the elliptical hip section.
    return np.arctan2(p[...,0], (p[...,1]-2.)*1.24)


def drape(p):
    angle = skirt_angle(p)
    drop = np.clip((93.-p[...,2])/77.,0.,1.)
    gain = drop**.85*(.48+.52*drop)
    bend = angle+.085*np.sin(angle*2.+drop*3.2)+.09*drop
    radius = gain*(1.27*np.cos(7*bend+.3)+.58*np.cos(11*bend-1.1)+.31*np.sin(4*angle+drop*2.))
    # The upper gather fans out into longer, softer lobes at the hem.
    radius += .29*np.sin(14.*angle+.5)*np.sin(np.pi*drop)*np.exp(-drop*2.)
    lift = gain**3*(.38*np.cos(7*bend+.6)+.30*np.sin(3*angle-.4))
    return np.stack([np.sin(angle)*radius,.86*np.cos(angle)*radius,lift],axis=-1)


def tailor_skirt(data):
    mask = data["ids"] == data["mats"].tolist().index("Skirt")
    tri = data["tri"][mask]
    verts = np.unique(tri)
    points = data["p"][verts]
    theta = skirt_angle(data["p"][tri])
    u = theta/(2*np.pi)+.5
    crosses = np.ptp(u,axis=1)>.5
    u[crosses] = np.where(u[crosses]<.5,u[crosses]+1.,u[crosses])
    # Follow the non-level original waist and hem so the woven guards follow the edge.
    bins = 96
    angle = skirt_angle(points)
    stops = np.linspace(-np.pi,np.pi,bins,endpoint=False)
    low,high = [],[]
    for a in stops:
        z = points[np.abs(np.angle(np.exp(1j*(angle-a)))) < 1.6*np.pi/bins,2]
        low.append(z.min())
        high.append(z.max())
    hem = np.interp(theta,stops,low,period=2*np.pi)
    waist = np.interp(theta,stops,high,period=2*np.pi)
    data["uv"][mask] = np.stack((u,np.clip((waist-data["p"][tri,2])/(waist-hem),0.,1.)),axis=-1)
    axes = np.eye(3)*.025
    jac = np.eye(3)+np.stack([(drape(points+a)-drape(points-a))/.05 for a in axes],axis=-1)
    normals = np.einsum("...ij,...j->...i",np.linalg.inv(jac).transpose(0,2,1)[np.searchsorted(verts,tri)],data["n"][mask])
    data["n"][mask] = normals/np.maximum(1e-10,np.linalg.norm(normals,axis=-1,keepdims=True))
    data["p"][verts] = points+drape(points)


def lower_belt_edge(points, x):
    a,b = points,np.roll(points,-1,axis=1)
    crosses = (a[:,:,0] < x) != (b[:,:,0] < x)
    a,b = a[crosses],b[crosses]
    edge = a+(b-a)*((x-a[:,0])/(b[:,0]-a[:,0]))[:,None]
    front = edge[edge[:,1] < edge[:,1].min()+1.]
    return float(front[:,2].min())
