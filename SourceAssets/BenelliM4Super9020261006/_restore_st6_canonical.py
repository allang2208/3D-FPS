"""Restore the clean M4 canonical for ue_st6_sleeves from source_shirt.json so
fix_st6_sleeves.py (non-idempotent) can rebuild on a fresh base."""
import json, numpy as np
from pathlib import Path
O = Path(__file__).parent; X = O / 'EquipmentSources'; Y = O / 'EquipmentAuthored'
a = json.loads((O / 'authoring.json').read_text())
C = np.diag([100., -100., 100., 1.]); Ci = np.linalg.inv(C)
warp = {n: C @ np.array(m) @ Ci for n, m in a['v7_to_native_warp'].items()}
ref = json.loads((X / 'rig_M4.json').read_text())


def old_name(n):
    if n.startswith('lowerarm_aux_'):
        return 'lowerarm_' + n[-1]
    return n


def target_name(n, bones):
    if n in ('lowerarm_l', 'lowerarm_r') and 'lowerarm_aux_' + n[-1] in bones:
        return 'lowerarm_aux_' + n[-1]
    if n in bones:
        return n
    if '_twist_' in n or n.startswith('lowerarm_aux_'):
        return n.split('_')[0] + '_' + n[-1]
    if '_metacarpal_' in n:
        return n.split('_')[0] + '_01_' + n[-1]
    if n.startswith('spine_'):
        return 'spine_03'
    return n


def fit(data, transforms, rename, binding, profile, item):
    ps = np.array(data['positions']); points = np.c_[ps, np.ones(len(ps))]
    matrices = []; weights = []
    for i, row in enumerate(data['weights']):
        mixed = np.zeros((4, 4)); total = 0.; wrow = {}
        for n, w in row.items():
            key = old_name(n); dest = rename(n)
            if dest not in binding['bones']:
                continue
            m = transforms.get(n, transforms.get(key))
            if m is None:
                if w > .03:
                    raise RuntimeError('Unmapped garment bone ' + profile + ' ' + n)
                continue
            mixed += m * w; total += w; wrow[dest] = wrow.get(dest, 0) + w
        if total <= 1e-7:
            raise RuntimeError('Unbound garment vertex ' + profile)
        matrices.append(mixed / total)
        weights.append({n: w / total for n, w in wrow.items()})
    matrices = np.array(matrices)
    output = np.einsum('nij,nj->ni', matrices, points)[:, :3]
    triangles = np.array(data['triangles'], dtype=int)
    normalm = np.linalg.inv(matrices[:, :3, :3]).transpose(0, 2, 1)
    ns = np.einsum('fcij,fcj->fci', normalm[triangles], np.array(data['normals']))
    ns /= np.maximum(np.linalg.norm(ns, axis=2, keepdims=True), 1e-8)
    result = {k: data[k] for k in ('triangles', 'uv', 'triangle_materials', 'materials', 'material_slots')}
    result.update(profile=profile, item=item, binding_source=binding['source'],
                  positions=output.tolist(), normals=ns.tolist(), weights=weights)
    path = Y / (profile + '_' + item + '.json')
    path.write_text(json.dumps(result, separators=(',', ':')))
    print('restored', path.name, len(result['positions']), 'verts')
    return result


source = json.loads((X / 'source_shirt.json').read_text())
fit(source, {n: np.linalg.inv(m) for n, m in warp.items()},
    lambda n: target_name(old_name(n), ref['bones']), ref, 'M4', 'ue_st6_sleeves')
