"""Author separate V7 skin-contact grips against the saved food meshes.

The drinking action supplies the single left-hand lift/recovery convention.
Each loaf gets its own palm contact and bounded finger wrap, baked into JSON;
the game does no surface search. No rendering or gameplay tests are performed.
"""
import json
import math
import runpy
from pathlib import Path
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
food_motion = runpy.run_path(str(OUT/'natural_food_motion.py'))['food_motion']
v7 = ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7'
source = json.loads((v7/'M4_original.json').read_text(encoding='utf-8-sig'))
skin = json.loads((v7/'Authored/M4.json').read_text(encoding='utf-8-sig'))
bones = source['bones']
by_index = {b['index']: n for n, b in bones.items()}
parent = {n: by_index.get(b['parent']) for n, b in bones.items()}
order = sorted(bones, key=lambda n: bones[n]['index'])

def frame(x, z):
    x = x.normalized()
    z = (z-x*z.dot(x)).normalized()
    return Matrix((x, z.cross(x), z)).transposed()

rest = {}
for name, bone in bones.items():
    rotation = Matrix([Vector(a).normalized() for a in bone['axes']]).transposed()
    matrix = rotation.to_4x4()
    matrix.translation = Vector(bone['position'])
    rest[name] = matrix
inverse = {n: m.inverted() for n, m in rest.items()}
local = {n: inverse[parent[n]]@m if parent[n] else m for n,m in rest.items()}
origin = rest['hand_l'].translation
palm = frame(rest['middle_01_l'].translation-origin,
    (rest['index_01_l'].translation-origin).cross(rest['pinky_01_l'].translation-origin))
hand = (palm.inverted()@rest['hand_l'].to_3x3()).to_4x4()

def hand_child(name):
    while name:
        if name == 'hand_l': return True
        name = parent[name]
    return False

children = [n for n in order if hand_child(n)]
digits = ('index','middle','ring','pinky','thumb')
direction, correction, patches = {}, {}, {}
for digit in digits:
    for segment in range(3):
        name = f'{digit}_{segment+1:02}_l'
        nxt = f'{digit}_{segment+2:02}_l'
        d = (rest[nxt].translation-rest[name].translation if nxt in rest else
            rest[name].to_3x3()@rest[parent[name]].to_3x3().inverted()@
            (rest[name].translation-rest[parent[name]].translation))
        direction[name] = d
        reference = frame(d, palm.col[2])
        correction[name] = reference.inverted()@rest[name].to_3x3()
        candidates = []
        for position, weights in zip(skin['positions'], skin['weights']):
            if weights.get(name, 0) < .55: continue
            p = Vector(position)
            relative = p-rest[name].translation
            along = relative.dot(d.normalized()) / d.length
            if .15 < along < .85:
                candidates.append((relative.dot(reference.col[2]), p, weights))
        candidates.sort(key=lambda p:p[0], reverse=True)
        # Actual V7 skin on the palmar side of this phalanx, not a bone tip.
        patches[name] = [(p,w) for _,p,w in candidates[:8]]

def pose(parameters):
    goal = {}
    for name in children:
        if name == 'hand_l':
            goal[name] = hand.copy()
            continue
        matrix = goal[parent[name]]@local[name]
        if name in correction:
            digit, number, _ = name.split('_')
            segment = int(number)-1
            data = parameters[digit]
            rotation = (Matrix.Rotation(math.radians(data['spread'][segment]),3,'Z')@
                Matrix.Rotation(-math.radians(data['flex'][segment]),3,'Y')@correction[name])
            matrix = rotation.to_4x4()
            matrix.translation = (goal[parent[name]]@local[name]).translation
        goal[name] = matrix
    return {name: matrix@inverse[name] for name,matrix in goal.items()}

def bounded(data, thumb=False):
    a,b,c = data['flex']
    if thumb:
        return 5 <= a <= 42 and 10 <= b-a <= 55 and 10 <= c-b <= 40 and c <= 115
    return 35 <= a <= 85 and 30 <= b-a <= 72 and 10 <= c-b <= 45 and c <= 180

profiles = {}
for definition, folder, model, height, across in (
    ('bread','Bread20261003','Bread',5.5,.8),
    ('baguette_bread','Baguette20261003','Baguette',15.0,.2),
):
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets'/folder/f'{model}_Authored.blend'))
    loaf = bpy.data.objects[f'SM_{model}']
    points = [loaf.matrix_world@v.co*100 for v in loaf.data.vertices]
    section = [p for p in points if abs(p.z-height)<.75]
    contact = Vector(((min(p.x for p in section)+max(p.x for p in section))*.5,
        (min(p.y for p in section)+max(p.y for p in section))*.5,height))
    # Upright object to semantic palm: X along fingers, -Y along loaf, Z palmar.
    object_to_palm = Matrix(((1,0,0),(0,0,-1),(0,1,0)))
    center = Vector((8.2, across, 4.55 if definition=='bread' else 3.5))
    parameters = {
        'index': {'spread':[-3,-3,-3], 'flex':[62,116,146]},
        'middle': {'spread':[-1,-1,-1], 'flex':[64,118,148]},
        'ring': {'spread':[-2,-2,-2], 'flex':[58,112,142]},
        'pinky': {'spread':[-3,-3,-3], 'flex':[48,104,134]},
        'thumb': {'spread':[-30,-18,-12], 'flex':[18,52,78]},
    }
    baseline = {n:list(d['flex']) for n,d in parameters.items()}
    faces = [tuple(p.vertices) for p in loaf.data.polygons]

    def surface_at():
        return BVHTree.FromPolygons([object_to_palm@(p-contact)+center for p in points], faces)

    surface = surface_at()
    def cost(only=None):
        transforms = pose(parameters)
        score = 0.
        for digit in ((only,) if only else digits):
            for segment in range(3):
                name = f'{digit}_{segment+1:02}_l'
                samples = patches[name]
                if not samples: continue
                for position, weights in samples:
                    p = sum((transforms[n]@position*w for n,w in weights.items() if n in transforms), Vector())
                    nearest, normal, _, distance = surface.find_nearest(p)
                    signed = (p-nearest).dot(normal)
                    # A slight clearance keeps skin outside the crust. More
                    # weight on penetration prevents fitting through the loaf.
                    score += (distance-.035)**2 + 12*min(0,signed-.015)**2
            score += .002*sum((a-b)**2 for a,b in zip(parameters[digit]['flex'],baseline[digit]))
        return score

    # Deterministic bounded authoring, retaining native bones/weights/scale.
    for step in (8.,4.,2.,1.):
        for _ in range(2):
            for digit in digits:
                current = cost(digit)
                for segment in range(3):
                    original = parameters[digit]['flex'][segment]
                    best = original
                    for delta in (-step,step):
                        parameters[digit]['flex'][segment] = original+delta
                        if bounded(parameters[digit], digit=='thumb'):
                            value = cost(digit)
                            if value < current: current,best = value,original+delta
                    parameters[digit]['flex'][segment] = best
                if digit=='thumb':
                    for segment in range(3):
                        original = parameters[digit]['spread'][segment]
                        best = original
                        for delta in (-step,step):
                            parameters[digit]['spread'][segment] = original+delta
                            if -55 <= original+delta <= -5:
                                value = cost(digit)
                                if value < current: current,best = value,original+delta
                        parameters[digit]['spread'][segment] = best
            current = cost()
            for axis in (0,2):
                original, best = center[axis], center[axis]
                for delta in (-step*.015,step*.015):
                    center[axis] = original+delta
                    surface = surface_at()
                    value = cost()
                    if value < current: current,best = value,original+delta
                center[axis] = best
                surface = surface_at()

    profiles[definition] = {
        'grip_height': height, 'grip_in_object': [round(v,4) for v in contact],
        'grip_in_palm': [round(v,4) for v in center], 'digits':parameters,
        'opens_container':False,
        'authoring': 'V7 native palmar skin and this loaf surface; single left-hand drinking-action lift; independent food grasp.',
        **food_motion(definition),
    }
(OUT/'grip_profiles.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('FOOD_GRIPS_AUTHORED', json.dumps({n:{k:d[k] for k in ('grip_in_object','grip_in_palm','digits')} for n,d in profiles.items()}))
