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
food_motion = runpy.run_path(str(ROOT/'SourceAssets/FoodGrip20261003/natural_food_motion.py'))['food_motion']
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

# The old fit used eight palmar samples per phalanx and Blender's loaf frame.
# Use the saved UE surface, the whole skinned hand (including palm) and contact
# patches separately. Nothing is changed on the accepted V7 mesh or skeleton.
import numpy as np
mesh = json.loads((OUT/'food-geometry.json').read_text())['baguette_bread']
points = np.array(mesh['positions'])
triangles = np.array(mesh['triangles'],dtype=int)
volume = np.einsum('ij,ij->i',points[triangles[:,0]],np.cross(points[triangles[:,1]],points[triangles[:,2]])).sum()
if volume<0:
    triangles = triangles[:,::-1]
surface = BVHTree.FromPolygons([Vector(p) for p in points],triangles.tolist(),all_triangles=True)
surface_low,surface_high=points.min(axis=0),points.max(axis=0)
ray_direction=Vector((1.,.173,.097)).normalized()
contact = np.array([0.,0.,15.])
object_to_palm = np.array([[1.,0.,0.],[0.,0.,-1.],[0.,1.,0.]])
profile = json.loads((ROOT/'SourceAssets/FoodGrip20261003/grip_profiles.json').read_text())['baguette_bread']
if (OUT/'baguette-previous.json').exists():
    previous=json.loads((OUT/'baguette-previous.json').read_text())
    profile['grip_in_palm']=previous['grip_in_palm']
    profile['grip_in_object']=[0.,0.,15.]
    profile['digits']=previous['digits']
parameters = profile['digits']
center = np.array(profile['grip_in_palm'],dtype=float)
# Profile contacts use the authored contact point; convert to the UE origin.
center += object_to_palm@(contact-np.array(profile['grip_in_object']))
baseline = {d:list(parameters[d]['flex']) for d in digits}
parameters['thumb'] = dict(spread=[-68.,-77.,-80.],flex=[26.,53.,74.])
skin_positions = np.array(skin['positions'])
selected = [i for i,w in enumerate(skin['weights']) if sum(v for n,v in w.items() if n in children)>.995]
selected = selected[::max(1,len(selected)//1800)]
selected_pos = np.column_stack((skin_positions[selected],np.ones(len(selected))))
skin_weights = np.array([[skin['weights'][i].get(n,0.) for n in children] for i in selected])
active = [(j,np.flatnonzero(skin_weights[:,j]>.0001)) for j in range(len(children))]
groups = [np.flatnonzero(skin_weights[:,[j for j,n in enumerate(children) if n.startswith(d+'_')]].sum(axis=1)>.35) for d in digits]
groups.append(np.flatnonzero(skin_weights[:,children.index('hand_l')]>.65))
patch_positions = []
patch_weights = []
for d in digits:
    for seg in (1,2):
        for p,w in patches[f'{d}_{seg+1:02}_l']:
            patch_positions.append([*p,1.])
            patch_weights.append([w.get(n,0.) for n in children])
patch_positions = np.array(patch_positions)
patch_weights = np.array(patch_weights)

def deform(transforms,positions,weights):
    result = np.zeros((len(positions),3))
    for j,n in enumerate(children):
        ids = np.flatnonzero(weights[:,j]>.0001)
        if len(ids):
            result[ids] += (positions[ids]@np.array(transforms[n]).T)[:,:3]*weights[ids,j,None]
    return result

def distances(p):
    obj = (p-center)@object_to_palm+contact
    signed,nearest = [],[]
    for v in obj:
        point,normal,_,distance = surface.find_nearest(Vector(v))
        # Nearest-face normals on this scanned crust can point away from a
        # distant exterior point. Ray parity distinguishes inside the loaf
        # from outside instead of treating every negative dot as penetration.
        inside=False
        if np.all(v>surface_low) and np.all(v<surface_high):
            origin=Vector(v);crossings=0
            for _ in range(32):
                hit,_,_,_=surface.ray_cast(origin,ray_direction,80.)
                if hit is None:break
                crossings+=1;origin=hit+ray_direction*.002
            inside=bool(crossings%2)
        signed.append(-distance if inside else distance)
        nearest.append(distance)
    return np.array(signed),np.array(nearest)

def objective():
    transforms = pose(parameters)
    signed,_ = distances(deform(transforms,selected_pos,skin_weights))
    _,dist = distances(deform(transforms,patch_positions,patch_weights))
    # Penetration of every surface region dominates contact accuracy. Pads get
    # 0.6 mm clearance; the palm and other finger surfaces may remain outside.
    score = sum(120*np.mean(np.minimum(signed[g]-.06,0)**2)+8*np.max(np.minimum(signed[g]-.06,0)**2) for g in groups if len(g))
    score += .12*np.mean((dist-.06)**2)
    score += .00008*sum((parameters[d]['flex'][i]-baseline[d][i])**2 for d in digits for i in range(3))
    return float(score),float(signed.min())

def legal(d):
    a,b,c = parameters[d]['flex']
    if d=='thumb':
        return -8<=a<=48 and 8<=b-a<=62 and 6<=c-b<=55 and c<=130
    return 18<=a<=85 and 20<=b-a<=74 and 6<=c-b<=48 and c<=180

initial = objective()
for step in (10.,5.,2.5,1.25):
    for iteration in range(3):
        for dim in (2,0,1):
            original_value = float(center[dim]);best_value=original_value;best=objective()[0]
            for delta in (-step*.045,step*.045):
                center[dim]=original_value+delta
                if 6.0<center[0]<10.5 and 2.5<center[2]<6.5 and -1.5<center[1]<1.5:
                    value=objective()[0]
                    if value<best:best,best_value=value,float(center[dim])
            center[dim]=best_value
        for d in digits:
            # The engine stores absolute palm-space flex angles. Change all
            # three together as well as each joint, so bounds cannot trap a
            # curled finger when the correct change is to open the whole digit.
            original_flex=list(parameters[d]['flex']);best_flex=original_flex;best=objective()[0]
            for delta in (-step,step):
                parameters[d]['flex']=[v+delta for v in original_flex]
                if legal(d):
                    value=objective()[0]
                    if value<best:best,best_flex=value,list(parameters[d]['flex'])
            parameters[d]['flex']=best_flex
            for field in ('spread','flex'):
                for seg in range(3):
                    if field=='spread' and d!='thumb' and seg>0:continue
                    original_value=parameters[d][field][seg];best_value=original_value;best=objective()[0]
                    for delta in (-step,step):
                        parameters[d][field][seg]=original_value+delta
                        spread=parameters[d]['spread']
                        valid=legal(d) and all((-100 if d=='thumb' else -6)<=x<=(0 if d=='thumb' else 6) for x in spread)
                        if d=='thumb':valid=valid and abs(spread[1]-spread[0])<=25 and abs(spread[2]-spread[1])<=25
                        if valid:
                            value=objective()[0]
                            if value<best:best,best_value=value,original_value+delta
                    parameters[d][field][seg]=best_value
                    if field=='spread' and d!='thumb':parameters[d]['spread']=[best_value]*3
        print('BAGUETTE_FIT',step,iteration,objective(),flush=True)
profile.update(grip_in_object=contact.tolist(),grip_height=15.,grip_in_palm=center.tolist(),digits=parameters,
    authoring='Saved UE baguette surface; full V7 hand skin penetration cost and separate finger-pad contact; opposing thumb; 2026-10-06')
(OUT/'baguette-grip.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(OUT/'grip-authoring.json').write_text(json.dumps(dict(initial_cost=initial,final_cost=objective(),sampled_skin_vertices=len(selected),
    note='Offline fitting objective only; no runtime/visual acceptance'),indent=2))
print('BAGUETTE_GRIP_AUTHORED',center.tolist(),flush=True)
transforms=pose(parameters)
fitted=deform(transforms,selected_pos,skin_weights)
signed,dist=distances(fitted)
worst=int(np.argmin(signed))
print('FITTED_SURFACE_EXTREMUM',signed[worst],fitted[worst].tolist(),skin['weights'][selected[worst]],flush=True)

