"""Opt-in reload diagnosis from the captured native V9 geometry and compressed source."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import trimesh

O = Path(__file__).parent
R9 = O.parent / 'R9ReloadGrip'
env = {'__file__': str(R9 / 'author_reload_grip.py')}
text = (R9 / 'author_reload_grip.py').read_text()
exec(compile(text.split("report={'method'")[0], str(R9 / 'author_reload_grip.py'), 'exec'), env)
globals().update({k: v for k, v in env.items() if k not in ('O', '__file__', '__builtins__')})
profile_path = Path(sys.argv[1]) if len(sys.argv) > 1 else R9 / 'profile_reload_grip.json'
profile = json.loads(profile_path.read_text())
tag = sys.argv[2] if len(sys.argv) > 2 else 'r9'
mag_mesh = trimesh.Trimesh(vertices=mag['svch'][0], faces=mag['svch'][1], process=True)
mag_mesh.fix_normals(multibody=True)
body_v, body_t = geom('svch', lambda n: n in ('SVCH_Body', 'SVCH_Polymer', 'SVCH_Rubber', 'SVCH_BarrelSteel'))
body_mesh = trimesh.Trimesh(vertices=body_v, faces=body_t, process=True)
body_mesh.fix_normals(multibody=True)
# Preserve the actual signed surface metric, and report closed-shell containment
# separately. Open mechanical submeshes cannot provide reliable global inside/outside.
report = {'profile': str(profile_path), 'magazine_watertight': bool(mag_mesh.is_watertight),
          'body_watertight': bool(body_mesh.is_watertight), 'clips': {}}
hand_ids = HANDIDS[::3]
digits = np.array([N[DOM[i]].split('_')[0] for i in hand_ids])
fore = NI['lowerarm_l']
wrist_ids = np.flatnonzero((AW[:, HAND] > .08) & (AW[:, HAND] < .92))
edges = np.unique(np.sort(np.concatenate([np.asarray(arms['triangles'])[:, a] for a in ((0, 1), (1, 2), (2, 0))]), axis=1), axis=0)
edges = edges[np.isin(edges, wrist_ids).all(axis=1)]

for role in ('reload', 'reload_empty'):
    clip = motion['clips'][role]
    layer = next(c for c in profile['clips'] if c['base'] == clip['path'])
    base = np.asarray(clip['frames'])
    samples = []
    hand_positions = []
    source_positions = []
    wrist_strain = []
    for i, time in enumerate(clip['times']):
        src = comp(matrices(base[i]))
        pose = comp(matrices(old_pose(base[i], layer, time)))
        hand_positions.append(pose[HAND, :3, 3])
        source_positions.append(src[HAND, :3, 3])
        if i % 5 != 0:
            continue
        original_skin, new_skin = skin(src, np.unique(edges)), skin(pose, np.unique(edges))
        lookup = {int(n): j for j, n in enumerate(np.unique(edges))}
        edge_indices = np.array([[lookup[int(a)], lookup[int(b)]] for a, b in edges])
        oldlen = np.linalg.norm(original_skin[edge_indices[:, 1]] - original_skin[edge_indices[:, 0]], axis=1)
        newlen = np.linalg.norm(new_skin[edge_indices[:, 1]] - new_skin[edge_indices[:, 0]], axis=1)
        ratio = newlen / np.maximum(oldlen, 1e-6)
        wrist_strain.append({'frame': i, 'edge_ratio_p01': float(np.percentile(ratio, 1)),
                             'edge_ratio_p99': float(np.percentile(ratio, 99))})
        if not 20 <= i <= 305:
            continue
        pm = rigid(src[MAG])
        world = skin(pose, hand_ids)
        local = points(np.linalg.inv(pm), world)
        closest, mag_normals, distances = surfaces['svch'].nearest(local)
        mag_signed = np.einsum('ij,ij->i', local - closest, mag_normals)
        inside = mag_mesh.contains(local) if mag_mesh.is_watertight else np.zeros(len(local), bool)
        body_local = points(rest['svch'][ROOT] @ np.linalg.inv(src[ROOT]), world)
        body_surface = surface(body_v, body_t)
        q, normals, bd = body_surface.nearest(body_local)
        body_signed = np.einsum('ij,ij->i', body_local - q, normals)
        source_rel = R.from_matrix(rigid(src[fore])[:3, :3]).inv() * R.from_matrix(rigid(src[HAND])[:3, :3])
        target_rel = R.from_matrix(rigid(pose[fore])[:3, :3]).inv() * R.from_matrix(rigid(pose[HAND])[:3, :3])
        row = {'frame': i, 'time': time,
               'wrist_relative_delta_deg': float(np.rad2deg((target_rel * source_rel.inv()).magnitude())),
               'mag_penetration_max_mm': (float(distances[inside].max() * 10) if inside.any() else 0.) if mag_mesh.is_watertight else None,
               'mag_near_signed_min_mm': float(mag_signed[distances < 2.5].min() * 10) if (distances < 2.5).any() else None,
               'mag_inside_vertices': int(inside.sum()),
               'body_near_signed_min_mm': float(body_signed[bd < 2.5].min() * 10) if (bd < 2.5).any() else 0.,
               'digits': {}}
        for d in ('thumb', 'index', 'middle', 'ring', 'pinky'):
            ix = digits == d
            row['digits'][d] = {'distance_p10_mm': float(np.percentile(distances[ix], 10) * 10),
                                'distance_median_mm': float(np.median(distances[ix]) * 10)}
        samples.append(row)
    step = np.linalg.norm(np.diff(hand_positions, axis=0), axis=1)
    sstep = np.linalg.norm(np.diff(source_positions, axis=0), axis=1)
    report['clips'][role] = {'max_hand_step_cm_at_120fps': float(step.max()),
                              'max_source_hand_step_cm_at_120fps': float(sstep.max()),
                              'max_step_frame': int(step.argmax() + 1),
                              'samples': samples, 'wrist_strain': wrist_strain}
    print('RELOAD_MEASURED', role, 'max_step', step.max(),
          'wrist_edge_p01_min', min(r['edge_ratio_p01'] for r in wrist_strain),
          'min_near_surface_signed_mm', min(r['mag_near_signed_min_mm'] for r in samples if r['mag_near_signed_min_mm'] is not None), flush=True)
(O / ('measure_' + tag + '.json')).write_text(json.dumps(report, indent=2))
print('RELOAD_MEASURE_COMPLETE', tag, flush=True)
