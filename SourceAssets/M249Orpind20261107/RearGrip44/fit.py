"""Fit one similarity transform per original mesh using the actual retained housing."""
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation


HERE = Path(__file__).resolve().parent
M249 = HERE.parent
CACHE = M249.parents[1]/'Saved/M249RearGrip44'
FIT = json.loads((M249/'GripMount40/fit.json').read_text())
RIM = np.array(FIT['rear_ring_cm'])*[1,-1,1]
PALM_Z = -15.5


def component(p):
    return (p[:, [1,0,2]]*100+[5.45,-28.6,-5.3])*[1,-1,1]


def section(tris, z):
    cut = tris[(tris[:, :, 2].min(1) < z) & (tris[:, :, 2].max(1) >= z)]
    samples = []
    for a, b in zip(cut.transpose(1,0,2), np.roll(cut,-1,axis=1).transpose(1,0,2)):
        valid = (a[:,2] < z) != (b[:,2] < z)
        a, b = a[valid], b[valid]
        samples.extend(a+(b-a)*((z-a[:,2])/(b[:,2]-a[:,2]))[:,None])
    return np.array(samples)


def center(points):
    return (points.min(0)+points.max(0))*.5


def seat_surface(p, tris, key):
    t = p[tris]
    c = t.mean(1)
    n = np.cross(t[:,1]-t[:,0], t[:,2]-t[:,0])
    area = np.linalg.norm(n,axis=1)
    n /= np.maximum(area[:, None],1e-15)
    lo, size = p.min(0), np.ptp(p,axis=0)
    # The two open profiles have a raised rear tang. Their load-bearing shelf
    # is the broad front facet, below the tang. The stable grip has a flat top.
    stable = key == 'stable_antislip_reargrip'
    high = (c[:,2]-lo[2])/size[2] > (.95 if stable else .80)
    front = (c[:,1]-lo[1])/size[1] < (1 if stable else .38)
    mask = high & front & (n[:,2] > .90)
    largest = np.flatnonzero(mask)[np.argmax(area[mask])]
    plane = n[largest]
    distance = (c-c[largest]) @ plane
    mask &= (n @ plane > .985) & (abs(distance) < .012*size[2])
    anchor = np.average(c[mask],axis=0,weights=area[mask])
    plane = np.average(n[mask],axis=0,weights=area[mask])
    return anchor, plane, t[mask].reshape(-1,3)


def underside(x, y, housing):
    a, b, c = housing[:,0], housing[:,1]-housing[:,0], housing[:,2]-housing[:,0]
    det = b[:,0]*c[:,1]-b[:,1]*c[:,0]
    valid = abs(det) > 1e-9
    det[~valid] = 1
    u = ((x-a[:,0])*c[:,1]-(y-a[:,1])*c[:,0])/det
    v = (b[:,0]*(y-a[:,1])-b[:,1]*(x-a[:,0]))/det
    h = a[:,2]+b[:,2]*u+c[:,2]*v
    h = h[valid & (u>=0) & (v>=0) & (u+v<=1) & (h>=-10.35) & (h<=-6.)]
    return h.min() if len(h) else np.nan


def fit(key, factory, housing):
    data = np.load(CACHE/(key+'.npz'))
    p, faces = data['points'], data['triangles']
    anchor, normal, contact = seat_surface(p, faces, key)
    # Keep both sides upright. Align only the fore/aft slope of the faces.
    flip = np.diag([-1.,-1.,1.])
    slope, intercept = np.polyfit(RIM[:,1],RIM[:,2],1)
    angle = np.arctan(slope)-np.arctan2(normal[1],normal[2])
    rotation = Rotation.from_rotvec([angle,0,0]).as_matrix() @ flip
    body = (p-anchor) @ rotation.T
    shelf = (contact-anchor) @ rotation.T
    palm = section(factory,PALM_Z)
    mid = center(palm)
    # Use the forward edge of the replacement's actual shelf and the front of
    # the receiver opening. Preserve its natural side profile and width.
    front = RIM[:,1].max()-.05
    sole = factory[:,:,2].min()
    palm_depth = np.ptp(palm[:,1])
    insertion = .25

    def placement(v):
        scale, y = v
        return np.array([mid[0], y, slope*y+intercept+insertion]), scale

    # Candidate keeps the grip heel, palm band and fore edge close to their
    # native landmarks, while permitting the original grip designs to differ.
    def residual(v):
        position, scale = placement(v)
        cut = section(body[faces], (PALM_Z-position[2])/scale)
        return [(center(cut)[1]*scale+position[1]-mid[1]),
                .55*(palm_depth-np.ptp(cut[:,1])*scale),
                .85*(body[:,2].min()*scale+position[2]-sole),
                1.5*(shelf[:,1].max()*scale+position[1]-front)]
    # Seat the original shoulder on solid receiver faces. Measure distinct
    # XY cells so dense triangles cannot bias the insertion towards one side.
    _, ids = np.unique(np.round(shelf[:,:2]/.011),axis=0,return_index=True)
    guess = [12.,15.]
    for step in range(5):
        result = least_squares(residual,guess,bounds=([9.,13.],[18.,17.3]),diff_step=1e-4)
        position, scale = placement(result.x)
        support = shelf[ids]*scale+position
        gaps = np.array([underside(x,y,housing)-z for x,y,z in support])
        gaps = gaps[np.isfinite(gaps)]
        if not len(gaps):
            raise ValueError('No overlapping receiver surface for '+key)
        dz = float(np.quantile(gaps,.12)+.10)
        if abs(dz)<.05 or step==4:
            break
        insertion += .7*dz
        guess = result.x
    # Set the depth of each original shoulder against the tapered side walls.
    # Move the front lip towards the stock where it also approaches the trigger.
    if key == 'stable_antislip_reargrip':
        position[1] -= .15
        dz -= 1.12
    elif key == 'balanced_reargrip':
        position[1] -= .22
        dz += .92
    position[2] += dz
    matrix = np.eye(4)
    matrix[:3,:3] = rotation*scale
    matrix[:3,3] = position-matrix[:3,:3]@anchor
    return dict(source_to_component_cm=matrix.tolist(),contact_center_cm=position.tolist(),
                uniform_scale_cm=scale, contact_samples=len(gaps), seat_offset_cm=insertion+dz)


if __name__ == '__main__':
    native = np.load(M249/'Geometry/RearGrip.npz')
    factory = component(native['positions'])[native['faces']]
    native = np.load(M249/'Geometry/Receiver.npz')
    triangles = np.delete(native['faces'],FIT['moved_body_faces'],axis=0)
    housing = component(native['positions'])[triangles]
    local = ((housing[:,:,1].min(1)<19) & (housing[:,:,1].max(1)>10)
             & (housing[:,:,2].min(1)<-5.8) & (housing[:,:,2].max(1)>-10.5))
    result = {key:fit(key,factory,housing[local]) for key in
              ('phantom_reargrip','stable_antislip_reargrip','balanced_reargrip')}
    (HERE/'placement.json').write_text(json.dumps(result,indent=2))
    for key, item in result.items():
        print(key, item['contact_center_cm'], 'seat offset', item['seat_offset_cm'], 'scale',item['uniform_scale_cm'])
