"""Measure resting native head/hair against the actual R3 render LOD shells."""
import json
from pathlib import Path
import sys

from mathutils import Vector
from mathutils.bvhtree import BVHTree
import numpy as np

S = Path(__file__).resolve().parents[2]/'SourceAssets/ModernTacticalSet20261113'
R = S/'HelmetNapeR3'
OLD = S/'HelmetContourR2'
HAIR = S/'HelmetHairFitR1'
CELL = .14
# Two angular samples per degree; evaluate the narrow band around the open
# rim separately, since hairs can leave that opening without piercing the shell.
AZIMUTHS = np.arange(720)*2*np.pi/720
BAND = .022


def radial(tree, origin, axis):
    # Stop at the radial origin so a ray through the opening cannot return
    # the far wall on the opposite side of the head.
    point = tree.ray_cast(origin+55*axis, -axis, 55)[0]
    return (point-origin).dot(axis) if point is not None else None


def boundary(tree, origin):
    def hit(theta, phi):
        axis = Vector((np.sin(theta)*np.sin(phi), np.cos(theta)*np.sin(phi), np.cos(phi)))
        return radial(tree, origin, axis) is not None

    # The lower edge can turn inward on the nape. Locate the last shell hit
    # from outside before refining it. Start well above the lowest ear cut.
    elevations = np.arange(.88, 3.12, .055)
    edges = []
    for theta in AZIMUTHS:
        last = next((phi for phi in reversed(elevations) if hit(theta, phi)),None)
        if last is None:
            raise ValueError('Could not locate shell meridian')
        low, high = last, min(np.pi,last+.055)
        for _ in range(10):
            mid=(low+high)*.5
            if hit(theta,mid):
                low=mid
            else:
                high=mid
        edges.append(low)
    return np.asarray(edges)


def polar(points, origin):
    relative = points-origin
    return (np.arctan2(relative[:,0],relative[:,1])%(2*np.pi),
            np.arccos(np.clip(relative[:,2]/np.maximum(np.linalg.norm(relative,axis=1),1e-6),-1,1)))


def measure(tree, origin, points, phi, ends, old_ends, angles):
    limit = np.interp(angles,AZIMUTHS,ends,period=2*np.pi)
    old = np.interp(angles,np.arange(len(old_ends))*2*np.pi/len(old_ends),old_ends,period=2*np.pi)
    selected = np.flatnonzero(phi < limit+BAND)
    core = phi[selected] < limit[selected]-BAND
    extended = core & (phi[selected] >= old[selected]) & (np.cos(angles[selected]) < 0.)
    p = points[selected]
    cells,inverse = np.unique(np.round(p/CELL).astype(np.int32),axis=0,return_inverse=True)
    positions = cells*CELL
    center = Vector(origin)
    depth = np.full(len(cells),np.nan)
    distance = np.empty(len(cells))
    for idx, position in enumerate(positions):
        delta = Vector(position)-center
        hit = radial(tree,center,delta.normalized())
        if hit is not None:
            depth[idx] = hit-delta.length
        distance[idx] = tree.find_nearest(Vector(position))[3]

    # Use the triangle-distance bound before assigning a voxel's sign to its
    # points. Recast every point in a cell that could cross the surface or rim.
    half_diagonal = float(np.sqrt(3)*CELL/2)
    actual = depth[inverse].copy()
    exact = np.isnan(actual) | (actual<=0.) | (distance[inverse]<=half_diagonal) | ~core
    for i in np.flatnonzero(exact):
        delta = Vector(p[i])-center
        hit = radial(tree,center,delta.normalized())
        actual[i] = np.nan if hit is None else hit-delta.length

    def scope(mask):
        hits = mask & np.isfinite(actual)
        values = actual[hits]
        return dict(raw_points=int(mask.sum()),rays_missing_shell=int((mask&~hits).sum()),
                    outside_outer_surface=int(np.sum(values<0)),
                    minimum_sampled_radial_cm=round(float(values.min()),4) if len(values) else None)

    return dict(core=scope(core),new_rear_coverage=scope(extended),open_rim_band=scope(~core),
                voxel_centers=len(cells),smallest_core_surface_distance_lower_bound_cm=round(
                    float(distance[inverse[core]].min()-half_diagonal),4))


def review(rig, lod):
    fit=json.loads((HAIR/'fit.json').read_bytes())['profiles'][rig]
    previous=np.load(OLD/f'{rig}-profile.npz')
    origin=previous['origin']
    cloud=np.load(HAIR/f'{rig}-hair-envelope.npz')['positions']
    data=json.loads((R/'SavedLods'/f'{rig}_LOD{lod}.json').read_bytes())
    frame=data['attachment_frame']
    positions=np.asarray(data['positions'])@np.asarray(frame['axes'])+frame['position']
    tree=BVHTree.FromPolygons(positions.tolist(),data['triangles'],all_triangles=True)
    edge=boundary(tree,Vector(origin))
    result={'lod':lod, 'style':fit['style'], 'binding_basis':fit['binding_basis']}
    head_count=fit['head_points']
    for label,points in [('hair',cloud[:-head_count]),('head',cloud[-head_count:])]:
        theta,phi=polar(points,origin)
        result[label]=measure(tree,origin,points,phi,edge,previous['ends'],theta)
    print(rig,lod,result['hair']['core'],result['hair']['new_rear_coverage'],flush=True)
    return result


if __name__=='__main__':
    if '--' in sys.argv:
        rig,lod=sys.argv[sys.argv.index('--')+1:]
        result=review(rig,int(lod))
        (R/'SavedLods'/f'{rig}_LOD{lod}-clearance.json').write_text(json.dumps(result,indent=2))
        print(rig,lod,result['hair']['core'],result['hair']['new_rear_coverage'],flush=True)
    else:
        rigs={rig:[review(rig,i) for i in range(3)] for rig in ['Jason','Kaitlin']}
        (R/'clearance.json').write_text(json.dumps(dict(scope='Resting captured native head and hair against saved UE render LODs. Core excludes 0.022 radians at open rim. Outer signed radial result uses each occupied 1.4 mm cell and recasts all points near the shell or open rim.',rigs=rigs),indent=2))
