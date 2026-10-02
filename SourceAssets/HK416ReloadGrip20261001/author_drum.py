"""Author a tighter drum grasp on native HK416 clips, with the palm fixed.

Only the twelve four-finger joint rotation tracks are emitted. Visible skin
directions supply the flex axes; actual drum triangles supply the pad targets.
The accepted thumb, wrist, arm, mechanical motion and original clocks remain
in the source clips. No renderer, editor, game or acceptance checks are run.
"""
import gzip
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

O = Path(__file__).resolve().parent
I = O / 'Inputs'
DIGITS = ('index', 'middle', 'ring', 'pinky')


def unit(v):
    return v / max(float(np.linalg.norm(v)), 1e-12)


def matrices(values):
    a = np.asarray(values, dtype=float)
    out = np.broadcast_to(np.eye(4), (*a.shape[:-1], 4, 4)).copy()
    out[..., :3, :3] = Rotation.from_quat(a[..., 3:7].reshape(-1, 4)).as_matrix().reshape(*a.shape[:-1], 3, 3) * a[..., None, 7:10]
    out[..., :3, 3] = a[..., :3]
    return out


def smooth(a, b, x):
    t = np.clip((x-a)/(b-a), 0., 1.)
    return t*t*(3.-2.*t)


class Surface:
    """Nearest actual triangle among a spatially selected neighborhood."""
    def __init__(self, points, triangles):
        self.tri = np.asarray(points, float)[np.asarray(triangles, int)]
        self.tree = cKDTree(self.tri.mean(axis=1))
        self.normal = np.cross(self.tri[:, 1]-self.tri[:, 0], self.tri[:, 2]-self.tri[:, 0])
        self.normal /= np.maximum(np.linalg.norm(self.normal, axis=1, keepdims=True), 1e-12)

    def nearest(self, points):
        points = np.asarray(points, float)
        _, ids = self.tree.query(points, k=min(48, len(self.tri)))
        tr = self.tri[ids]
        p = points[:, None, :]
        a, b, c = tr[:, :, 0], tr[:, :, 1], tr[:, :, 2]
        ab, ac, ap = b-a, c-a, p-a
        aa = np.sum(ab*ab, axis=2); bb = np.sum(ab*ac, axis=2); cc = np.sum(ac*ac, axis=2)
        den = np.maximum(aa*cc-bb*bb, 1e-16)
        u = (cc*np.sum(ab*ap, axis=2)-bb*np.sum(ac*ap, axis=2))/den
        v = (aa*np.sum(ac*ap, axis=2)-bb*np.sum(ab*ap, axis=2))/den
        plane = a+u[..., None]*ab+v[..., None]*ac
        inside = (u>=0)&(v>=0)&(u+v<=1)
        candidates = [plane]
        for x, y in ((a, b), (b, c), (c, a)):
            xy = y-x
            t = np.clip(np.sum((p-x)*xy, axis=2)/np.maximum(np.sum(xy*xy, axis=2), 1e-16), 0., 1.)
            candidates.append(x+t[..., None]*xy)
        choices = np.stack(candidates, axis=2)
        dd = np.sum((choices-p[:, :, None, :])**2, axis=3)
        dd[:, :, 0] = np.where(inside, dd[:, :, 0], np.inf)
        k = dd.argmin(axis=2)
        closest = np.take_along_axis(choices, k[:, :, None, None], axis=2)[:, :, 0]
        dist = np.sum((closest-p)**2, axis=2)
        j = dist.argmin(axis=1); rows = np.arange(len(points))
        q = closest[rows, j]; n = self.normal[ids[rows, j]]
        return q, n, np.sqrt(dist[rows, j])


class HandSkin:
    def __init__(self, data, names, rest):
        self.pos = np.asarray(data['pos'], float)
        lookup = {str(n):i for i,n in enumerate(names)}
        self.ids = np.array([lookup[str(n)] for n in data['bones']], int)[data['bone_idx']]
        self.weights = np.asarray(data['bone_w'], float)
        self.inverse = np.linalg.inv(rest)
        dominant = self.ids[np.arange(len(self.pos)), self.weights.argmax(axis=1)]
        self.groups = {n: np.flatnonzero((dominant==lookup[n]) & (self.weights.max(axis=1)>.35)) for n in names if n.endswith('_l') and n.startswith(DIGITS)}
        self.centers = {n:self.pos[ix].mean(axis=0) for n,ix in self.groups.items() if len(ix)}

    def skin(self, pose, ix):
        p = self.pos[ix]; ids = self.ids[ix]; w = self.weights[ix]
        m = (pose@self.inverse)[ids]
        v = np.einsum('nkij,nj->nki', m[..., :3, :3], p)+m[..., :3, 3]
        return (v*w[..., None]).sum(axis=1)

    def centroid(self, pose, name):
        return self.skin(pose, self.groups[name]).mean(axis=0)


def main():
    required = (I/'bind.json', I/'HK416.npz', I/'drum.npz', O/'inputs.json')
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise RuntimeError('Native authoring inputs are not available: '+', '.join(missing))
    bind = json.loads((I/'bind.json').read_text())
    index = json.loads((O/'inputs.json').read_text())
    names = bind['names']; ni = {n:i for i,n in enumerate(names)}
    parents = np.asarray(bind['parents'], int); rest = matrices(bind['rest'])
    skin = HandSkin(np.load(I/'HK416.npz'), names, rest)
    drum = np.load(I/'drum.npz'); surface = Surface(drum['pos'], drum['tris'])
    source = json.load(gzip.open(I/'base__drum_reload.json.gz', 'rt', encoding='utf8'))
    sb = source['bones']; bi = {n:i for i,n in enumerate(sb)}
    source_world = matrices(source['world']); source_local = matrices(source['local'])
    ref_i = int(np.argmin(np.abs(np.asarray(source['times'])*60.-48.)))
    pose = rest.copy()
    for n in sb:pose[ni[n]] = source_world[ref_i, bi[n]]
    local = rest.copy()
    for j,p in enumerate(parents):
        if p>=0:local[j] = np.linalg.inv(rest[p])@rest[j]
    for n in sb:local[ni[n]] = source_local[ref_i, bi[n]]
    h = ni['hand_l']; m = ni['WPN_SOCKET_Magazine']
    inv_drum = np.linalg.inv(pose[m]@np.linalg.inv(rest[m]))
    rigid = inv_drum[:3, :3]
    def to_drum(points):return points@rigid.T+inv_drum[:3, 3]

    # Build an anatomical plane from visible native skin, not arbitrary bone axes.
    hand_center = rest[h, :3, 3]
    normal_rest = unit(np.cross(skin.centers['index_01_l']-hand_center, skin.centers['pinky_01_l']-hand_center))
    hand_rot = Rotation.from_matrix(pose[h, :3, :3]/np.linalg.norm(pose[h, :3, :3], axis=0)).as_matrix()
    hand_rest_rot = Rotation.from_quat(bind['rest'][h][3:7]).as_matrix()
    normal_world = unit(hand_rot@hand_rest_rot.T@normal_rest)
    directions = {}
    for digit in DIGITS:
        d = skin.centroid(pose, digit+'_02_l')-skin.centroid(pose, digit+'_01_l')
        directions[digit] = unit(d-normal_world*np.dot(d, normal_world))
    center_direction = unit(directions['middle']+directions['ring'])

    fitted = {}; anatomical = {}
    for digit in DIGITS:
        joint_names = [f'{digit}_{k:02d}_l' for k in (1,2,3)]
        joints = [ni[n] for n in joint_names]
        axes = []
        for k,n in enumerate(joint_names):
            d = skin.centers[joint_names[min(k+1, 2)]]-skin.centers[joint_names[max(k-1, 0)]]
            if np.linalg.norm(d)<1e-7:d = skin.centers[joint_names[2]]-skin.centers[joint_names[1]]
            world_axis = unit(np.cross(unit(d), normal_rest))
            axes.append(Rotation.from_quat(bind['rest'][ni[n]][3:7]).inv().apply(world_axis))
        adduct_axis = Rotation.from_quat(source['world'][ref_i][bi[joint_names[0]]][3:7]).inv().apply(normal_world)
        yaw = np.arctan2(np.dot(normal_world, np.cross(directions[digit], center_direction)), np.dot(directions[digit], center_direction))
        adduct = float(np.clip(np.degrees(yaw)*.60, -10., 10.))
        descendants = [j for j,n in enumerate(names) if n.startswith(digit+'_') and n.endswith('_l')]

        def deform(parameters):
            pp = pose.copy(); ll = local.copy()
            for k,j in enumerate(joints):
                extra = Rotation.from_rotvec(np.asarray(axes[k])*np.radians(parameters[k+1])).as_matrix()
                if k==0:extra = Rotation.from_rotvec(adduct_axis*np.radians(parameters[0])).as_matrix()@extra
                ll[j, :3, :3] = local[j, :3, :3]@extra
            for j in descendants:pp[j] = pp[parents[j]]@ll[j]
            return pp

        # Closest visible skin on the middle/distal segments supplies finger pads.
        pad_ids = []
        for n in joint_names[1:]:
            ids = skin.groups[n]
            q, norm, distance = surface.nearest(to_drum(skin.skin(pose, ids)))
            order = np.argsort(distance)
            selected = order[:max(8, int(len(ids)*.22))]
            pad_ids.extend(ids[selected[np.linspace(0, len(selected)-1, min(20,len(selected)), dtype=int)]].tolist())
        pad_ids = np.asarray(pad_ids, int)
        initial_points = to_drum(skin.skin(pose, pad_ids))
        _, _, gap = surface.nearest(initial_points)
        if float(np.median(gap))>12.:
            raise RuntimeError('Native drum/hand source spaces are inconsistent for '+digit)

        # Pick flex signs by the visible pads approaching the actual drum surface.
        signs = []
        for k in range(3):
            error = []
            for sign in (-1.,1.):
                delta = np.zeros(4);delta[k+1]=sign*3.
                _,_,gd = surface.nearest(to_drum(skin.skin(deform(delta), pad_ids)))
                error.append(float(np.mean(gd)))
            signs.append((-1.,1.)[int(np.argmin(error))])
        axes = [a*s for a,s in zip(axes,signs)]
        prior = np.array([adduct, 5., 6., 4.]) if digit!='pinky' else np.array([adduct, 15., 30., 16.])
        upper = np.array([adduct+2.5, 22., 22., 14.]) if digit!='pinky' else np.array([adduct+2.5, 32., 48., 28.])
        lower = np.array([adduct-2.5, 0., 0., 0.])
        # Target a small pad clearance; penalize penetration and excessive joint
        # changes separately so a closer tip cannot flatten or overfold the hand.
        def residual(x):
            points = to_drum(skin.skin(deform(x), pad_ids))
            q, norm, gd = surface.nearest(points)
            signed = np.einsum('ij,ij->i', points-q, norm)
            # Exported static shell normals are outward. This term is active
            # only near the surface, where its sign is meaningful.
            penetr = np.where((signed<0.)&(gd<2.5), -signed, 0.)
            contact = (gd-.16)/.36
            reg = (x-prior)/np.array([1.8,9.,10.,8.])
            return np.r_[contact/np.sqrt(len(gd)), penetr/.20/np.sqrt(len(gd)), reg*.75]
        fit = least_squares(residual, np.clip(prior,lower+1e-5,upper-1e-5), bounds=(lower,upper), loss='soft_l1', max_nfev=80, ftol=2e-5, xtol=2e-5, gtol=2e-5)
        fitted[digit] = {'degrees':fit.x.tolist(), 'axes_local':np.asarray(axes).tolist(), 'adduct_axis_local':adduct_axis.tolist()}
        anatomical[digit] = {'visible_direction_world':directions[digit].tolist(),'selected_pad_vertices':len(pad_ids),'joint_limits_degrees':upper[1:].tolist()}

    output = {'clips':{}}
    for asset,meta in index['clips'].items():
        if meta['family'] not in ('base','vertical','canted','prism','angled') or meta['kind'] not in ('drum_reload','drum_reload_empty'):continue
        src = json.load(gzip.open(meta['file'],'rt',encoding='utf8'))
        native = np.asarray(src['local'],float)
        lut = {n:i for i,n in enumerate(src['bones'])}
        frames = np.asarray(src['times'])*60.
        a,b,c,d = (18.,24.,92.,102.) if meta['kind']=='drum_reload' else (12.,18.,80.,92.)
        weight = smooth(a,b,frames)*(1.-smooth(c,d,frames))
        tracks = {}
        for digit in DIGITS:
            parameters = fitted[digit]
            values = parameters['degrees']
            for k in range(3):
                n = f'{digit}_{k+1:02d}_l'; row = native[:,lut[n]].copy()
                curl = Rotation.from_rotvec(np.outer(weight*np.radians(values[k+1]),parameters['axes_local'][k]))
                extra = curl
                if k==0:
                    adduct = Rotation.from_rotvec(np.outer(weight*np.radians(values[0]),parameters['adduct_axis_local']))
                    extra = adduct*curl
                q = (Rotation.from_quat(row[:,3:7])*extra).as_quat()
                # Preserve source representation exactly outside the contact
                # window, and select each active quaternion's source hemisphere.
                q[np.einsum('ij,ij->i',q,row[:,3:7])<0.] *= -1.
                row[weight>0.,3:7] = q[weight>0.]
                tracks[n] = row.tolist()
        output['clips'][asset] = {'source_sha256':meta['sha256'],'family':meta['family'],'kind':meta['kind'],'tracks':tracks}
    with gzip.open(O/'drum_tracks.json.gz','wt',encoding='utf8') as f:json.dump(output,f,separators=(',',':'))
    report = {'method':'Fixed original palm/arm; actual native visible-skin flex axes, constrained four-finger adduction and drum-pad fitting','inputs':'Current native UE raw poses and exported native skeletal/static geometry','fingers':fitted,'anatomical':anatomical,'windows_author_frames_60hz':{'drum_reload':[18,24,92,102],'drum_reload_empty':[12,18,80,92]},'unchanged':['hand_l','left_arm','thumb','metacarpals','all_bone_translation_and_scale','mechanical_tracks','clock','slap_116','return_128_148'], 'clips':len(output['clips']),'runtime_tested':False,'rendered':False}
    (O/'drum_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print('HK416_DRUM_GRASP_AUTHORED',len(output['clips']),flush=True)


if __name__=='__main__':main()
