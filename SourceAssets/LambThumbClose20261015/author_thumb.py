"""Author only lamb thumb rotations against the actual V7 skinned surface.

Keep palms, four fingers, mesh, weights and bone lengths fixed. The asymmetric
rack is fitted on each side; the runtime right-side spread convention is used.
No editor, render, game or savegame access.
"""
import copy
import json
import math
import runpy
from pathlib import Path

import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
V7 = ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
source = json.loads((ROOT/'SourceAssets/BenelliM4Super9020261006/EquipmentSources/rig_Traversal.json').read_text())
skin = json.loads((V7/'Authored/Traversal.json').read_text())
data = json.loads((OUT/'Before/Content/ColdSteelData/potion_use_motion.json').read_text())
bones = source['bones']
names = {b['index']: n for n, b in bones.items()}
parent = {n: names.get(b['parent']) for n, b in bones.items()}
order = sorted(bones, key=lambda n: bones[n]['index'])


def frame(x, z):
    x = x.normalized()
    z = (z-x*z.dot(x)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()


def rotation(euler):
    p, y, r = map(math.radians, euler)
    return Matrix.Rotation(y, 3, 'Z') @ Matrix.Rotation(-p, 3, 'Y') @ Matrix.Rotation(-r, 3, 'X')


rest = {}
for name, bone in bones.items():
    m = Matrix([Vector(axis).normalized() for axis in bone['axes']]).transposed().to_4x4()
    m.translation = Vector(bone['position'])
    rest[name] = m
inverse = {n: m.inverted() for n, m in rest.items()}
local = {n: inverse[parent[n]] @ m if parent[n] else m for n, m in rest.items()}
positions = np.column_stack([skin['positions'], np.ones(len(skin['positions']))])


def inside(surface, point):
    # Nearest-face normals alone misclassify points beyond a cut wrist or a rib
    # edge. Majority parity over oblique rays determines the side of the skin.
    votes = 0
    for direction in (Vector((1, .371, .619)).normalized(),
                      Vector((-.417, 1, .293)).normalized(),
                      Vector((.269, -.529, 1)).normalized()):
        origin, count = point.copy(), 0
        for _ in range(32):
            hit, _, _, _ = surface.ray_cast(origin, direction, 100.)
            if hit is None:
                break
            count += 1
            origin = hit+direction*.0001
        votes += count % 2
    return votes >= 2


class Grasp:
    def __init__(self, motion, geometry, side):
        self.motion, self.side = motion, side
        self.sign = -1 if side == 'r' else 1
        h = 'hand_'+side
        def below(n):
            while n:
                if n == h:
                    return True
                n = parent[n]
            return False
        self.hand_children = [n for n in order if below(n)]
        self.children = [n for n in order if below(n) or n in
                         ('lowerarm_'+side, 'lowerarm_twist_01_'+side, 'lowerarm_twist_02_'+side)]
        wrist = rest[h].translation
        self.palm = frame(rest['middle_01_'+side].translation-wrist,
                          (rest['index_01_'+side].translation-wrist).cross(rest['pinky_01_'+side].translation-wrist)*self.sign)
        self.hand = (self.palm.inverted() @ rest[h].to_3x3()).to_4x4()
        # Include forearm contributions to the thumb root, without renormalizing
        # away their 7-8% weights. Solve the same shoulder/elbow/wrist geometry as
        # PotionArmPose, then express the forearm in wrist/palm coordinates.
        self.forearms = []
        u, l = 'upperarm_'+side, 'lowerarm_'+side
        ru, rl = rest[l].translation-rest[u].translation, rest[h].translation-rest[l].translation
        for k in (motion['keys'][3], motion['keys'][5], motion['keys'][7], motion['keys'][9], motion['keys'][11]):
            g = rotation(k['rotation'])
            upright = Matrix(((1, 0, 0), (0, 0, self.sign), (0, -self.sign, 0)))
            desired = g @ upright
            grip = Vector(k['grip'])
            if side == 'r':
                grip += g @ rotation(motion['object_rotation']) @ (Vector(motion['right_grip_in_object'])-Vector(motion['grip_in_object']))
            palm_grip = Vector(motion['right_grip_in_palm'] if side == 'r' else motion['grip_in_palm'])
            target = grip-desired @ palm_grip
            shoulder, pole = Vector(data['shoulder']), Vector(data['elbow_pole'])
            shoulder.y *= self.sign
            pole.y *= self.sign
            reach = target-shoulder
            limit = (ru.length+rl.length)*.93
            if reach.length > limit:
                shoulder += reach.normalized()*(reach.length-limit)
            direction = (target-shoulder).normalized()
            distance = (target-shoulder).length
            along = (ru.length_squared-rl.length_squared+distance*distance)/(2*distance)
            bend = (pole-shoulder)-direction*(pole-shoulder).dot(direction)
            elbow = shoulder+direction*along+bend.normalized()*math.sqrt(max(0, ru.length_squared-along*along))
            ld = desired.inverted() @ (target-elbow).normalized()
            def xy(x, y):
                x = x.normalized();y = (y-x*y.dot(x)).normalized()
                return Matrix((x, y, x.cross(y))).transposed()
            deform = xy(ld, Vector((0, 1, 0))) @ xy(rl, self.palm.col[1]).inverted()
            lower = (deform @ rest[l].to_3x3()).to_4x4()
            lower.translation = desired.inverted() @ (elbow-target)
            self.forearms.append(lower)
        self.correction = {}
        for digit in motion['digits']:
            for segment in range(1, 4):
                n, nxt = f'{digit}_{segment:02}_{side}', f'{digit}_{segment+1:02}_{side}'
                direction = rest[nxt].translation-rest[n].translation if nxt in rest else (
                    rest[n].to_3x3() @ rest[parent[n]].to_3x3().inverted() @
                    (rest[n].translation-rest[parent[n]].translation))
                self.correction[n] = frame(direction, self.palm.col[2]).inverted() @ rest[n].to_3x3()
        self.thumb_ids = np.array([i for i, w in enumerate(skin['weights'])
                                   if sum(v for n, v in w.items() if n.startswith('thumb_') and n.endswith('_'+side)) > .1])
        self.hand_ids = np.array([i for i, w in enumerate(skin['weights'])
                                  if sum(w.get(n, 0) for n in self.hand_children) > .995])
        self.pad_local = np.array([j for j, i in enumerate(self.thumb_ids)
                                    if skin['weights'][i].get('thumb_03_'+side, 0) > .7])
        self.original = copy.deepcopy(motion.get('right_thumb', motion['digits']['thumb']) if side == 'r' else motion['digits']['thumb'])
        upright = Matrix(((1, 0, 0), (0, 0, self.sign), (0, -self.sign, 0)))
        object_to_palm = upright.inverted() @ rotation(motion['object_rotation'])
        grip = Vector(motion['right_grip_in_object'] if side == 'r' else motion['grip_in_object'])
        center = Vector(motion['right_grip_in_palm'] if side == 'r' else motion['grip_in_palm'])
        self.food = BVHTree.FromPolygons([object_to_palm @ (Vector(p)-grip)+center for p in geometry['vertices']], geometry['faces'])
        self.skin_weights = {n: np.array([w.get(n, 0) for w in skin['weights']]) for n in self.children}
        self.total_weights = sum(self.skin_weights.values())
        fixed = self.deform(self.original, self.hand_ids, self.forearms[0])
        lookup = {int(i): j for j, i in enumerate(self.hand_ids)}
        thumb_set = {i for i, w in enumerate(skin['weights'])
                     if sum(v for n, v in w.items() if n.startswith('thumb_') and n.endswith('_'+side)) > .001}
        # UE native triangle winding is opposite the supplied outward normals.
        faces = [[lookup[i] for i in reversed(t)] for t in skin['triangles']
                 if all(i in lookup and i not in thumb_set for i in t)]
        self.other_fingers = BVHTree.FromPolygons(fixed.tolist(), faces)

    def deform(self, thumb, ids, lower=None):
        goal = {}
        for n in self.children:
            if n == 'lowerarm_'+self.side:
                goal[n] = lower.copy()
                continue
            if n == 'hand_'+self.side:
                goal[n] = self.hand.copy()
                continue
            m = goal[parent[n]] @ local[n]
            if n in self.correction:
                digit, number, _ = n.split('_')
                s = int(number)-1
                pose = thumb if digit == 'thumb' else self.motion['digits'][digit]
                q = Matrix.Rotation(math.radians(pose['spread'][s])*self.sign, 3, 'Z') @ Matrix.Rotation(-math.radians(pose['flex'][s]), 3, 'Y') @ self.correction[n]
                loc = m.translation.copy()
                m = q.to_4x4()
                m.translation = loc
            goal[n] = m
        result = np.zeros((len(ids), 3))
        for n, m in goal.items():
            w = self.skin_weights[n][ids]
            if not np.any(w):
                continue
            result += (positions[ids] @ np.array(m @ inverse[n]).T)[:, :3]*w[:, None]
        return result/self.total_weights[ids, None]

    def distances(self, thumb):
        points = np.concatenate([self.deform(thumb, self.thumb_ids, lower) for lower in self.forearms])
        food, hand, distances = [], [], []
        for p in points:
            point = Vector(p)
            near, normal, _, distance = self.food.find_nearest(point)
            food.append(-distance if inside(self.food, point) else distance)
            distances.append(distance)
            near, normal, _, distance = self.other_fingers.find_nearest(point)
            hand.append(-distance if distance < 1.5 and inside(self.other_fingers, point) else distance)
        return np.array(food), np.array(hand), np.array(distances)

    def cost(self, thumb):
        food, hand, dist = self.distances(thumb)
        penetrations = np.minimum(food-.025, 0)**2 + np.minimum(hand-.015, 0)**2
        # All thumb skin participates, including the tip and mixed palm weights.
        # Pads provide contact, without pulling the entire thumb through meat.
        pad_ids = np.concatenate([self.pad_local+i*len(self.thumb_ids) for i in range(len(self.forearms))])
        pads = np.sort(dist[pad_ids])[:max(1, len(pad_ids)//5)]
        return float(1800*np.mean(penetrations)+1800*np.max(penetrations) +
                     2*np.mean((pads-.12)**2) + .0004*sum((v-b)**2 for v, b in zip(thumb['flex'], [5, 22, 35])))

    def metrics(self, thumb):
        food, hand, dist = self.distances(thumb)
        return {'thumb_skin_vertices': len(food), 'food_penetration_vertices_over_0_2mm': int(np.sum(food < -.02)),
                'max_food_penetration_cm': round(max(0., -float(food.min())), 5),
                'max_other_finger_penetration_cm': round(max(0., -float(hand.min())), 5),
                'nearest_tip_food_cm': round(float(dist[self.pad_local].min()), 5),
                'deepest_vertex_weights': skin['weights'][self.thumb_ids[food.argmin()%len(self.thumb_ids)]]}


def valid(p):
    a, b, c = p['flex']
    spread = p['spread']
    return (-15 <= a <= 55 and 0 <= b-a <= 60 and 0 <= c-b <= 45 and c <= 135 and
            all(-115 <= s <= -10 for s in spread) and
            abs(spread[1]-spread[0]) <= 20 and abs(spread[2]-spread[1]) <= 20)


report, authored = {}, {}
for item, folder, filename in [('roasted_large_lamb', 'LargeLamb20261014', 'large-lamb-geometry.json'),
                              ('roasted_lamb_ribs', 'LambRibs20261014', 'lamb-geometry.json')]:
    motion = copy.deepcopy(data[item])
    runpy.run_path(str(ROOT/'SourceAssets/FoodGrip20261003/lamb_food_motion.py'))['apply_lamb_motion'](motion,large=bool(motion.get('two_handed')),apply_grasp=False)
    if motion.get('two_handed'):
        # The existing grip buries the mixed-weight thumb root. A small outward
        # wrist clearance is necessary; all four finger joint rotations stay put.
        motion['grip_in_palm'][2] += 1.0
        motion['right_grip_in_palm'][2] += 1.2
    geometry = json.loads((ROOT/'SourceAssets'/folder/filename).read_text())
    authored[item] = {}
    for side in (('l', 'r') if motion.get('two_handed') else ('l',)):
        grasp = Grasp(motion, geometry, side)
        before = Grasp(data[item], geometry, side).metrics(grasp.original)
        seeds = [{'spread': [s, s+5, s+10], 'flex': [f, f+17, f+30]}
                 for s in (-90, -70, -50, -30) for f in (-10, 5, 20)]
        if valid(grasp.original):
            seeds.append(copy.deepcopy(grasp.original))
        best = min(seeds, key=grasp.cost)
        value = grasp.cost(best)
        for step in (12., 6., 3., 1.5, .75):
            for _ in range(3):
                for field in ('spread', 'flex'):
                    for segment in range(3):
                        prior = best[field][segment]
                        winning = prior
                        for delta in (-step, step):
                            best[field][segment] = prior+delta
                            if valid(best):
                                cost = grasp.cost(best)
                                if cost < value:
                                    value, winning = cost, prior+delta
                        best[field][segment] = winning
        after = grasp.metrics(best)
        authored[item][side] = {'thumb': best, 'grip_in_palm': motion['right_grip_in_palm' if side == 'r' else 'grip_in_palm']}
        report[item+'_'+side] = {'before': before, 'after': after, 'thumb': best}
        print(item, side, json.dumps(report[item+'_'+side]), flush=True)
(OUT/'thumb_profiles.json').write_text(json.dumps(authored, indent=2)+'\n')
(OUT/'thumb-authoring.json').write_text(json.dumps(report, indent=2)+'\n')
