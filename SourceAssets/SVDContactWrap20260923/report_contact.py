"""Describe the user-authorized local contact comparison, using baked skin."""
import json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

O = Path(__file__).parent
fit = json.loads((O / 'grasp_fit.json').read_text())
report = {'scope': 'Local source pose at insertion frame 220; no game or PIE test', 'poses': {}}
for label in ['before', 'after']:
    surface = json.loads((O / (label + '_surface.json')).read_text())
    hand, magazine = surface['parts'][:2]
    tree = BVHTree.FromPolygons([Vector(v) for v in magazine['vertices']], magazine['faces'])
    patches = dict(fit['pad_regions'], palm=fit['palm_region'])
    contact = {}
    for name, indices in patches.items():
        distances = sorted(tree.find_nearest(Vector(hand['vertices'][i]))[3] * 1000 for i in indices)
        contact[name] = {'mean_mm': sum(distances) / len(distances), 'minimum_mm': distances[0],
                         'median_mm': distances[len(distances) // 2], 'samples': len(distances)}
    report['poses'][label] = contact
(O / 'local_contact_comparison.json').write_text(json.dumps(report, indent=2))
for name in patches:
    print('SVD_LOCAL_CONTACT', name, round(report['poses']['before'][name]['mean_mm'], 2),
          '->', round(report['poses']['after'][name]['mean_mm'], 2), 'mm', flush=True)
