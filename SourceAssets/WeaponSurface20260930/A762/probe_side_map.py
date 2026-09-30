"""Blender (background): ASCII map of which slot is seen from each side of the seated A762.

blender -b --factory-startup -P probe_side_map.py -- <key>
Rows are z (top = high), columns are y (left = muzzle side); 0.5 cm cells. Used to place the
AK rivets on the visible receiver sheet. Read-only.
"""
import sys
from pathlib import Path
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

key = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'A762_AfterRepair'
h, pos, st, tri, mat, bone, gun = seated.load(key)
keep = gun
tris = tri[keep]
mats = mat[keep]
tree = BVHTree.FromPolygons([tuple(p) for p in st], tris.tolist(), all_triangles=True)
letters = {'M_A762_Receiver': 'R', 'M_A762_UpperReceiver03': 'U', 'M_A762_FrontAssembly_Rebuilt': 'F',
           'M_A762_Magazine_Rebuilt': 'M', 'M_A762_MagazineEdge_Rebuilt': 'm', 'M_A762_FactoryRearGrip': 'G',
           'M_A762_Bolt': 'B', 'M_A762_Handguard03': 'H', 'M_A762_Rail': 'r', 'M_A762_SightInner': 'i',
           'M_A762_FactoryStock_Metal04': 'S', 'M_A762_FactoryStock_Socket03': 's', 'M_A762_RearSight03': 'e'}
ys = np.arange(-36.0, -1.0, 0.5)
zs = np.arange(1.0, -13.0, -0.5)
for side, x0, d in (('LEFT (from -x)', -20.0, Vector((1, 0, 0))), ('RIGHT (from +x)', 30.0, Vector((-1, 0, 0)))):
    print(side, 'y from %.1f to %.1f' % (ys[0], ys[-1]), flush=True)
    for z in zs:
        row = []
        for y in ys:
            hit, nrm, idx, _ = tree.ray_cast(Vector((x0, y, z)), d, 60.0)
            if hit is None:
                row.append('.')
                continue
            ch = letters.get(h['slots'][mats[idx]], '?')
            row.append(ch if abs(nrm.x) > 0.8 else ch.lower() if ch.isupper() else ch)
        print('%6.1f %s' % (z, ''.join(row)), flush=True)
