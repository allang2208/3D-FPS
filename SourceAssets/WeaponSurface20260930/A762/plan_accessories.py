"""Item 2: plan the A762 accessories on the weapon-surface standard (plain CPython).

Inputs: Bake/accessory_materials.json (inspect_accessories.py), the ACC_* geometry dumps and
slot_plan.json. Every accessory slot gets one of:
- skip: glass, lenses, reticles, translucent/masked materials (the masked holographic
  housing keeps its cut-out) and the muzzle-recess helpers - not surfaces of the finish;
- body: the slot used an A762 body material (FactoryStock_Metal04 interface plates,
  magazine materials) -> same preset and values as that gun slot in slot_plan.json;
- a preset from the part's role, decided per slot from its material name and its share of
  the accessory's area (see ROLE): polymer bodies of grips/stocks, rubber pads, anodised
  optic/light housings, satin-steel hardware, muzzle devices and magazines.
Each accessory instance samples its own mask in UV0 (baked when UV0 is a unique layout,
otherwise the neutral mask). Writes Bake/accessory_plan.json.
"""
import json
import re
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import seated  # noqa: E402

mats = json.loads((HERE / 'Bake' / 'accessory_materials.json').read_text(encoding='utf-8'))
slot_plan = json.loads((HERE / 'slot_plan.json').read_text(encoding='utf-8'))['main']
MAGAZINE = {'preset': 'CleanSatinSteel', 'scalars': {'Roughness': 0.48, 'EdgeHighlight': 0.0, 'EdgeWear': 0.0}}
STEEL = {'preset': 'CleanSatinSteel'}
ANOD = {'preset': 'CleanAnodized'}
POLY = {'preset': 'CleanPolymer'}
RUBBER = {'preset': 'Rubber'}
SKIP = {'skip': 'not a finish surface'}
# Slot suffix -> role, decided from the material names and area shares (Interface plates and
# magazine materials come from the gun body; see module doc).
ROLE = {
    'angled': {'0': POLY},
    'balanced_reargrip': {'0': POLY, '1': STEEL},
    'brake': {'0': STEEL, '1': SKIP},
    'canted': {'0': POLY, '1': STEEL},
    'core_stock': {'0': POLY, '1': RUBBER, '2': STEEL},
    'drum': {'0': MAGAZINE, '1': STEEL, '2': MAGAZINE},
    'flashlight': {'0': ANOD, '1': ANOD},
    'holographic': {'0': {'skip': 'masked housing keeps its window cut-out'}, '1': SKIP},
    'laser': {'0': ANOD, '1': ANOD},
    'lpvo_1_6x': {'0': SKIP, '1': SKIP, '2': ANOD},
    'lpvo_ring': {'0': ANOD},
    'panoramic_red_dot': {'0': SKIP, '1': SKIP, '2': ANOD},
    'phantom_reargrip': {'0': POLY, '1': STEEL},
    'prism': {'0': POLY, '1': ANOD, '2': ANOD},
    'prism_scope_2x': {'0': SKIP, '1': SKIP, '2': ANOD},
    'qr_performance': {'0': STEEL, '1': POLY, '2': RUBBER, '3': STEEL},
    'skeleton': {'0': STEEL, '1': POLY, '2': RUBBER},
    'stable_antislip_reargrip': {'0': RUBBER, '1': STEEL},
    'suppressor': {'0': STEEL, '1': SKIP},
    'tactical_suppressor': {'0': STEEL, '1': SKIP, '2': STEEL},
    'tactical_telescopic': {'0': STEEL, '1': POLY, '2': RUBBER, '3': STEEL},
    'tactical_vertical': {'0': POLY, '2': STEEL},
    'titanium_brake': {'0': STEEL, '1': SKIP, '2': STEEL},
    'vertical': {'0': POLY, '1': STEEL},
}


def uv_unique(key):
    """Share of occupied UV0 cells (512^2) whose surface samples lie > 0.5 cm apart in 3D,
    and the share of samples outside [0,1]."""
    h, pos, tri, mat, uv, _ = seated.read_geometry(seated.GEOMETRY / (key + '.bin'))
    P = pos[tri].astype(np.float64)
    area = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    rng = np.random.default_rng(7)
    n = 80000
    pick = rng.choice(len(tri), n, p=area / area.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    w = np.stack([1 - s, s * (1 - r2), s * r2], 1)
    xyz = (P[pick] * w[..., None]).sum(1)
    st = (uv[pick].astype(np.float64) * w[..., None]).sum(1)
    outside = float(((st < 0) | (st > 1)).any(1).mean())
    U = uv.astype(np.float64)
    e1, e2 = U[:, 1] - U[:, 0], U[:, 2] - U[:, 0]
    uv_area = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]).sum()
    cell = np.clip((st % 1 * 512).astype(int), 0, 511)
    key_ = cell[:, 0] * 512 + cell[:, 1]
    order = np.argsort(key_)
    ks, xs = key_[order], xyz[order]
    starts = np.r_[0, np.nonzero(np.diff(ks))[0] + 1]
    ends = np.r_[starts[1:], len(ks)]
    bad = sum(1 for a, b in zip(starts, ends) if b - a > 1 and np.ptp(xs[a:b], axis=0).max() > 0.5)
    return {'overlap_share': round(bad / max(len(starts), 1), 4), 'outside_share': round(outside, 4),
            'triangles': int(len(tri)), 'area_cm2': round(float(area.sum()), 1),
            'uv_per_cm': round(float(np.sqrt(uv_area / area.sum())), 5)}


plan = {}
for mesh, entry in mats.items():
    key = mesh.replace('SM_A762_', '')
    uvq = uv_unique('ACC_' + key)
    unique = uvq['overlap_share'] < 0.035 and uvq['outside_share'] < 0.05
    slots = {}
    for s in entry['slots']:
        info = s['material'] or {}
        path = info.get('path') or ''
        suffix = s['slot'].rsplit('_', 1)[-1]
        d = {'material': path}
        body = re.search(r'/Weapons/A762/Refinement0\d/Materials/M_A762_(\w+)\.', path)
        if body and 'M_A762_' + body.group(1) in slot_plan:
            spec = slot_plan['M_A762_' + body.group(1)]
            d.update(action='preset', preset=spec['preset'], scalars=spec.get('scalars', {}),
                     vectors=spec.get('vectors', {}), reason='gun body material M_A762_' + body.group(1))
        elif key in ROLE and suffix in ROLE[key]:
            role = ROLE[key][suffix]
            if 'skip' in role:
                d.update(action='skip', reason=role['skip'])
            else:
                d.update(action='preset', preset=role['preset'], scalars=role.get('scalars', {}), reason='role')
        else:
            d.update(action='skip', reason='unclassified: kept as is')
        if d['action'] == 'preset' and 'OPAQUE' not in (info.get('blend') or ''):
            d.update(action='skip', reason='non-opaque blend kept as is')
        if d['action'] == 'preset':
            d['normal'] = next((t['path'] for t in info.get('textures', []) if 'NORMALMAP' in t['compression']), None)
        slots[s['slot']] = d
    plan[mesh] = {'path': entry['path'], 'uv0': uvq, 'mask': 'bake' if unique else 'neutral', 'slots': slots}
    print(mesh.ljust(34), 'mask', plan[mesh]['mask'].ljust(7), flush=True)
    for k, d in slots.items():
        print('    %-32s %-6s %-16s %s' % (k[:32], d['action'], d.get('preset', ''), d['reason'][:40]), flush=True)
(HERE / 'Bake' / 'accessory_plan.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
print('A762_ACCESSORY_PLAN', len(plan), sum(d['action'] == 'preset' for p in plan.values() for d in p['slots'].values()))
