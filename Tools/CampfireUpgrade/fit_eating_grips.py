"""Fit single-hand food poses to the V9 palm and the cooked mesh in UE centimeters.

Run with background Blender. Without --publish this prints the existing contact
measurements. With --publish it fits the fingers and writes the runtime profiles.
"""
import copy
import itertools
import json
import math
import runpy
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree


ROOT = Path(__file__).resolve().parents[2]
SOURCES = ROOT / 'SourceAssets'
DATA = ROOT / 'Content/ColdSteelData'
DIGITS = ('thumb', 'index', 'middle', 'ring', 'pinky')
WILD = {'roasted_venison': 'Venison', 'roasted_boar_meat': 'BoarMeat', 'roasted_fox_meat': 'FoxMeat'}


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def frame(x, z):
    x = x.normalized()
    z = (z - x * z.dot(x)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()


def rotation(angles):
    pitch, yaw, roll = map(math.radians, angles)
    return Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(-pitch, 3, 'Y') @ Matrix.Rotation(-roll, 3, 'X')


class Hand:
    def __init__(self):
        bones = read(SOURCES / 'ModularOutfit20260925/BarePalmV7/M4_original.json')['bones']
        baseline = read(SOURCES / 'BareHandAudit20261016/Final/56a5bcfd1c23.json')
        skin = read(SOURCES / 'BareSkinV9M4_20261017/Work/install_payload.json')
        parents = {row['index']: name for name, row in bones.items()}
        self.parent, self.rest, self.local = {}, {}, {}
        self.correction = {}
        for name, row in sorted(bones.items(), key=lambda pair: pair[1]['index']):
            parent = parents.get(row['parent'])
            if name != 'hand_l' and parent not in self.rest:
                continue
            self.parent[name] = parent
            transform = Matrix([Vector(a).normalized() for a in row['axes']]).transposed().to_4x4()
            transform.translation = Vector(row['position'])
            self.rest[name] = transform
            if name != 'hand_l':
                self.local[name] = self.rest[parent].inverted() @ transform
        wrist = self.rest['hand_l'].translation
        palm = frame(self.rest['middle_01_l'].translation-wrist,
                     (self.rest['index_01_l'].translation-wrist).cross(self.rest['pinky_01_l'].translation-wrist))
        self.wrist = (palm.inverted() @ self.rest['hand_l'].to_3x3()).to_4x4()
        for digit in DIGITS:
            for index in range(3):
                name = f'{digit}_{index+1:02}_l'
                transform = self.rest[name]
                nxt = self.rest.get(f'{digit}_{index+2:02}_l')
                par = self.rest[self.parent[name]]
                axis = nxt.translation-transform.translation if nxt else (
                    transform.to_3x3() @ par.to_3x3().inverted() @ (transform.translation-par.translation))
                self.correction[name] = frame(axis, palm.col[2]).inverted() @ transform.to_3x3()
        # Bind V9's actual rest surface and sparse replacement weights.
        weights = [skin['weights'].get(str(v), w) for v, w in zip(skin['vertex_ids'], baseline['weights'])]
        indices = [i for i, w in enumerate(weights) if sum(w.get(n, 0) for n in self.rest) > .995]
        points = np.array(skin['positions'])[indices]
        _, unique = np.unique(points.round(4), axis=0, return_index=True)
        ids = np.asarray(indices)[unique]
        points = np.column_stack((points[unique], np.ones(len(unique))))
        self.vertices = len(points)
        self.bind = {}
        for name, transform in self.rest.items():
            w = np.array([weights[i].get(name, 0.) for i in ids])
            take = np.flatnonzero(w)
            bind = (points[take] @ np.array(transform.inverted()).T) * w[take,None]
            self.bind[name] = (take, bind)
        dominant = [max(weights[i], key=weights[i].get) for i in ids]
        self.groups = {d: np.array([i for i,n in enumerate(dominant) if n.startswith(d+'_') and 'metacarpal' not in n], dtype=int)
                       for d in DIGITS}
        self.groups['palm'] = np.flatnonzero(~np.isin(np.arange(len(points)),np.concatenate(list(self.groups.values()))))
        self.contact = {d: np.array([i for i,n in enumerate(dominant) if n in (f'{d}_02_l',f'{d}_03_l')], dtype=int) for d in DIGITS}

    def deform(self, digits):
        posed = {}
        vertices = np.zeros((self.vertices, 3))
        for name in self.rest:
            transform = self.wrist if name=='hand_l' else posed[self.parent[name]] @ self.local[name]
            if name in self.correction:
                digit, number, _ = name.split('_')
                j = int(number)-1
                pose = digits[digit]
                if 'local_rotations' in pose:
                    x,y,z,w = pose['local_rotations'][j]
                    orient = transform.to_3x3() @ Quaternion((w,x,y,z)).to_matrix()
                else:
                    orient = (Matrix.Rotation(math.radians(pose['spread'][j]),3,'Z')
                              @ Matrix.Rotation(-math.radians(pose['flex'][j]),3,'Y') @ self.correction[name])
                position = transform.translation.copy()
                transform = orient.to_4x4()
                transform.translation = position
            posed[name] = transform
            ids, bind = self.bind[name]
            vertices[ids] += bind @ np.array(transform)[:3,:].T
        return vertices


def food_surface(name, meshes, profile):
    if name in WILD:
        mesh = 'SM_Roasted' + WILD[name]
        bpy.ops.wm.open_mainfile(filepath=str(SOURCES / 'CampfireUpgrade20261026/Blends' / (mesh+'.blend')))
        obj = bpy.data.objects[mesh]
        points = np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices]) * [100,-100,100]
        faces = np.array([list(poly.vertices) for poly in obj.data.polygons])
    else:
        points = np.array(meshes[name]['vertices'])
        faces = np.array(meshes[name]['faces'])
    a,b,c = points[faces].transpose((1,0,2))
    if np.sum(a*np.cross(b,c)) < 0:
        faces = faces[:,::-1]
    grip = profile.get('grip_in_object', [0,0,profile['grip_height']])
    basis = frame(Vector((1,0,0)), Vector((0,1,0))) @ rotation(profile.get('palm_rotation',[0,0,0]))
    relative = basis.inverted() @ rotation(profile.get('object_rotation',[0,0,0]))
    return BVHTree.FromPolygons((points-grip) @ np.array(relative).T, faces.tolist())


def signed_distances(surface, points):
    vals = []
    ray = Vector((.731,.349,.586)).normalized()
    for point in points:
        p = Vector(point)
        _, _, _, distance = surface.find_nearest(p)
        # Normal signing alone can classify free space near a concave crease as inside.
        hits = 0
        start = p
        while True:
            hit, _, _, _ = surface.ray_cast(start, ray)
            if hit is None:
                break
            hits += 1
            start = hit + ray*.0005
        vals.append(-distance if hits%2 else distance)
    return np.array(vals)


def set_food_rotation(profile, angles):
    old = rotation(profile['object_rotation'])
    new = rotation(angles)
    bite = Vector(profile['bite_in_object']) - Vector(profile['grip_in_object'])
    delta = old @ bite - new @ bite
    if delta.length > .0001:
        for key in profile['keys']:
            key['grip'] = list(Vector(key['grip']) + rotation(key['rotation']) @ delta)
    profile['object_rotation'] = angles


def fit(hand, surface, profile, publish, roll_options=()):
    center = np.array(profile['grip_in_palm'])
    original = center.copy()
    digits = profile['digits']
    initial = copy.deepcopy(digits)
    verts = hand.deform(digits)

    def metrics(points, offset):
        values = signed_distances(surface, points-offset)
        return (round(float(max(0,-values.min())),3), int((values<-.15).sum()))

    before = metrics(verts, center)
    if not publish or before[0] < .10:
        return before, before
    best_metrics, best_center, best_digits = before, center.copy(), copy.deepcopy(digits)

    def score(points, offset, groups):
        loss = 0.
        for group in groups:
            ids = hand.groups[group][::2]
            depths = signed_distances(surface, points[ids]-offset)
            # Keep both the web and the back of the digits clear of the mesh.
            penetration = 60*np.mean(np.minimum(depths-.035,0)**2) + 12*max(0.,-depths.min())**2
            # Keep the curved chicken bone outside the web of the palm before
            # closing the fingers. Five independent finger terms would
            # otherwise favour holding the bone inside the palm.
            loss += penetration * (6 if group=='palm' and roll_options else 1)
            if group != 'palm':
                pads = signed_distances(surface, points[hand.contact[group][::4]]-offset)
                count = min(6,len(pads))
                closest = np.partition(np.abs(pads-.045), count-1)[:count]
                loss += 2*np.mean(closest**2)
        return loss

    starts = [original+delta for delta in itertools.product((-.75,0,.75),repeat=3)]
    choices = [(profile.get('object_rotation',[0,0,0]),surface), *roll_options]
    best_loss = float('inf')
    best_surface = surface
    for angles, surface in choices:
        for offset in starts:
            loss = score(verts,offset,hand.groups)+.08*np.sum((offset-original)**2)
            if loss < best_loss:
                best_loss, center, best_surface, chosen_angles = loss, offset, surface, angles
    surface = best_surface
    for step in (1., 1., .65, .4, .22):
        for axis in (2,0,1):
            best = center.copy()
            best_score = score(verts, center, hand.groups) + .08*np.sum((center-original)**2)
            for shift in (-.48,-.24,.24,.48):
                candidate = center.copy()
                candidate[axis] += shift*step
                if np.linalg.norm(candidate-original)>2.1: continue
                loss = score(verts, candidate, hand.groups) + .08*np.sum((candidate-original)**2)
                if loss < best_score:
                    best, best_score = candidate, loss
            center = best
        for digit in DIGITS:
            pose = digits[digit]
            if 'local_rotations' in pose:
                continue
            for field in ('flex','spread'):
                for joint in range(3):
                    start = pose[field][joint]
                    reference = initial[digit][field][joint]
                    best = start
                    loss = score(verts,center,[digit]) + .0009*(start-reference)**2
                    for delta in (-6.,-3.,3.,6.):
                        value = start+delta*step
                        limit = 22 if roll_options else 15
                        if abs(value-reference)>limit: continue
                        pose[field][joint] = value
                        if field=='flex' and min(np.diff(pose[field]))<3: continue
                        probe = hand.deform(digits)
                        trial = score(probe,center,[digit]) + .0009*(value-reference)**2
                        if trial<loss:
                            best,loss = value,trial
                    pose[field][joint] = round(best,3)
                    verts = hand.deform(digits)
        current = metrics(verts, center)
        if current[0] <= before[0] and (current[1],current[0]) < (best_metrics[1],best_metrics[0]):
            best_metrics, best_center, best_digits = current, center.copy(), copy.deepcopy(digits)
    profile['digits'] = best_digits
    profile['grip_in_palm'] = best_center.round(4).tolist()
    if best_metrics!=before and roll_options:
        set_food_rotation(profile, chosen_angles)
    return before, best_metrics


def main():
    publish = '--publish' in sys.argv
    path = DATA / 'potion_use_motion.json'
    original = path.read_bytes()
    profiles = json.loads(original.decode('utf-8-sig'))
    grip_dir = SOURCES / 'FoodGrip20261003'
    loaf_frame = runpy.run_path(str(grip_dir/'publish_food_motion.py'))['runtime_family']
    seeds = {
        'bread': loaf_frame('bread',read(grip_dir/'grip_profiles.json')['bread']),
        'baguette_bread': loaf_frame('baguette_bread',read(SOURCES/'Consume20261006/baguette-grip.json')),
        'roasted_chicken_leg': read(SOURCES/'CampfireChickenUse20261014/grip_profile.json'),
        'roasted_lamb_ribs': read(SOURCES/'LambRibs20261014/grip_profile.json'),
        'roasted_sausage': read(SOURCES/'Sausage20261014/grip_profile.json'),
    }
    meshes = read(SOURCES / 'FoodThirdPerson20261017/food_geometries.json')
    hand = Hand()
    for name in ('bread','baguette_bread','roasted_chicken_leg','roasted_lamb_ribs','roasted_sausage',*WILD):
        parent = 'roasted_sausage' if name in WILD else name
        profile = copy.deepcopy(profiles[parent])
        if publish:
            for key in ('grip_in_palm','digits'):
                profile[key] = copy.deepcopy(seeds[parent][key])
            if name=='roasted_chicken_leg':
                profile.pop('palm_rotation',None)
                set_food_rotation(profile,seeds[parent]['object_rotation'])
        else:
            profile = profiles.get(name,profile)
        surface = food_surface(name,meshes,profile)
        roll_options = []
        if publish and name=='roasted_chicken_leg':
            # Rotate the curved bone in the grasp, keeping the elbow/wrist
            # naturally aligned and the edible end on its authored path.
            for roll in range(-150,181,30):
                if roll:
                    angles = [-90,0,roll]
                    roll_options.append((angles,food_surface(name,meshes,dict(profile,object_rotation=angles))))
        before, after = fit(hand,surface,profile,publish,roll_options)
        print(f'{name}: (worst penetration cm, vertices deeper than 0.15 cm) {before} -> {after}',flush=True)
        if publish and (before!=after or name in WILD or profile.get('authoring','').startswith('V9 palm/finger fit')):
            if before!=after or name in WILD:
                profile['authoring'] = 'V9 palm/finger fit to '+name+' mesh; authored grip-to-bite trajectory retained.'
            else:
                profile['authoring'] = seeds[parent]['authoring']
            profiles[name] = profile
    if publish:
        if path.read_bytes()!=original:
            raise RuntimeError('Motion data changed during fitting; rerun on the current profiles.')
        path.write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
