"""Shared native-coordinate helpers frozen from the V12 authoring source."""
import bisect
import json
import math
from pathlib import Path
import bpy
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
DATA = json.loads((P/'inputs.json').read_text('utf-8'))
SOURCE = ROOT/'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/RuneSword_BareArmsV7.blend'
FPS, FRAMES = 120, 198
C = Matrix.Diagonal(Vector((1,-1,1)))
PARENTS = DATA['parents']
NAMES = list(PARENTS)
TIME_MAP = [(0,0.),(32,32/120),(80,80/120),(96,.8),
            (105,.9127450980392157),(111,116/120),(120,1.05),(198,1.70)]

def mat(p,q,s=(1,1,1)):
    return Matrix.LocRotScale(Vector(p),q,Vector(s))

def native(row):
    return mat(row['p'],Quaternion(row['q']),row['s'])

def canonical(m):
    p,q,s = m.decompose()
    return mat(C@p*.01,(C@q.to_matrix()@C).to_quaternion(),s)

def globalize(local):
    world = {}
    def get(n):
        if n not in world:
            parent = PARENTS[n]
            world[n] = get(parent)@local[n] if parent in local else local[n].copy()
        return world[n]
    for n in NAMES:get(n)
    return world

def localize(world):
    return {n:world[PARENTS[n]].inverted()@world[n] if PARENTS[n] in world else world[n] for n in NAMES}

def descendants(name):
    result = {name}
    for n in NAMES:
        parent = PARENTS[n]
        while parent in PARENTS:
            if parent==name:
                result.add(n)
                break
            parent = PARENTS[parent]
    return result

HANDS = {side:descendants('hand_'+side) for side in ('l','r')}
WEAPON = descendants('WPN_root') | {'ik_hand_l','ik_hand_r'}

def smooth(x):
    x = max(0.,min(1.,x))
    return x*x*x*(10+x*(-15+6*x))

def source_time(frame):
    for (a,ta),(b,tb) in zip(TIME_MAP,TIME_MAP[1:]):
        if frame<=b:return ta+(tb-ta)*(frame-a)/(b-a)
    return TIME_MAP[-1][1]

def sample_keys(samples,t):
    times = [e['seconds'] for e in samples]
    k = max(0,min(len(times)-1,bisect.bisect_right(times,t)-1))
    j = min(len(times)-1,k+1)
    alpha = (t-times[k])/(times[j]-times[k]) if j!=k else 0.
    a,b = samples[k]['bones'],samples[j]['bones']
    result = {}
    for n in NAMES:
        qa,qb = Quaternion(a[n]['q']),Quaternion(b[n]['q'])
        if qa.dot(qb)<0:qb = -qb
        result[n] = dict(p=list(Vector(a[n]['p']).lerp(Vector(b[n]['p']),alpha)),
                         q=list(qa.slerp(qb,alpha)),
                         s=list(Vector(a[n]['s']).lerp(Vector(b[n]['s']),alpha)))
    return result

