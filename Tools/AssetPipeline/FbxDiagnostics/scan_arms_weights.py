import sys, glob, numpy as np
from scan_body_fbx import parse_fbx

def kids(nodes, name):
    return [c for c in nodes if len(c) > 0 and c[0] == name]

path = sys.argv[1]
tree, ver = parse_fbx(path)
objs = kids(tree, 'Objects')
connections = kids(tree, 'Connections')

# map: node id -> (name, classname)
id2name = {}
for o in objs[0][2]:
    if len(o) >= 2 and o[1] and isinstance(o[1][0], int):
        id2name[o[1][0]] = o[0]

# connections: C "OO" child parent or "OP"
conns = []
for c in connections[0][2]:
    if len(c) > 1 and c[0] == 'C':
        args = c[1]
        if len(args) >= 3:
            conns.append((args[0], args[1], args[2], args[3] if len(args) > 3 else None))

# deformers
deformers = [o for o in objs[0][2] if len(o) > 0 and o[0] == 'Deformer']
subs = [d for d in deformers if len(d) > 1 and len(d[1]) > 2 and d[1][2] == 'Cluster']
clusters = [d for d in deformers if len(d) > 1 and len(d[1]) > 2 and d[1][2] == 'SubDeformer']

# parent map
parentof = {}
for kind, a, b, prop in conns:
    if kind == 'OO':
        parentof[a] = b

# find model node names
models = {o[1][0]: o[0] for o in objs[0][2] if len(o) > 0 and o[0] == 'Model'}

def bonename_of_cluster(cl):
    cid = cl[1][0]
    p = parentof.get(cid)
    return models.get(p, p)

# classify bone side
def side(name):
    if not name: return '?'
    n = name.lower()
    if n.endswith('_l') or '_l' in n[-4:] or '.l' in n or 'left' in n: return 'L'
    if n.endswith('_r') or '_r' in n[-4:] or '.r' in n or 'right' in n: return 'R'
    return 'C'

ARM = ('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')
def is_arm(name):
    if not name: return False
    return any(k in name.lower() for k in ARM)

# geometry vertex count
geos = kids(objs[0][2], 'Geometry')
nverts = None
for g in geos:
    vnodes = [c for c in g[2] if c[0] == 'Vertices']
    if vnodes:
        nverts = len(vnodes[0][1][0]) // 3
        print('geom verts', nverts)
        break

# For each cluster get indices+weights
both = []  # verts touched by L and R arm clusters
infl = {}  # vert -> set of sides (L arm, R arm, center, nonarm)
for cl in subs + clusters:
    idx = None; wts = None
    for c in cl[2]:
        if c[0] == 'Indexes': idx = c[1][0]
        if c[0] == 'Weights': wts = c[1][0]
    if idx is None or wts is None: continue
    bn = bonename_of_cluster(cl)
    s = side(str(bn))
    a = is_arm(str(bn))
    tag = ('L' if s == 'L' else 'R' if s == 'R' else 'C') + ('A' if a else 'N')
    for i, w in zip(idx, wts):
        if w <= 0: continue
        infl.setdefault(i, {})[tag] = infl.get(i, {}).get(tag, 0) + float(w)

cross = [v for v, t in infl.items() if ('LA' in t or 'RA' in t)]
print('verts influenced by arm bones:', len(cross))
LR = [v for v, t in infl.items() if 'LA' in t and 'RA' in t]
print('verts influenced by BOTH L and R arm bones:', len(LR))
if LR:
    print('sample:', LR[:20])
LC = [v for v, t in infl.items() if 'LA' in t and 'CN' in t]
RC = [v for v, t in infl.items() if 'RA' in t and 'CN' in t]
print('verts L-arm + center-nonarm:', len(LC), ' R-arm + center-nonarm:', len(RC))
