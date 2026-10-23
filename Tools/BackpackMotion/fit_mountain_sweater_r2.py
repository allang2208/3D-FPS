"""Refit the existing mountain harness to the current tailored knit shirt.

Keep all topology, bag shell, UVs, bone weights and motion masks. Record a spatial
delta map so both existing LODs can receive the same fit without decimation.
"""
import hashlib
import json
import sys
from pathlib import Path
import numpy as np

P = Path('D:/FPS3D/FPSGAME'); R = P/'SourceAssets/BackpackMotion20261022'
sys.path.insert(0, str(P/'Tools/BackpackHarness'))
from author import read, write, envelope, lift_required, smooth_lift, frame, Mesh

plan = read(R/'manifest.json')
row = next(r for r in plan['variants'] if r['kind']=='mountain' and r['profile']=='knit_sweater')
source = P/'SourceAssets/BackpackHarnessRebuild20261020/Authored/knit_sweater.json'
data = read(source); old = np.array(data['positions']); v = old.copy()
maskdata = read(R/'Masks/mountain_knit_sweater.json'); mask = np.array(maskdata['values'])
inputs = P/'SourceAssets/ExpeditionBackpack20261022/BodyInputs'
equations, _ = envelope(read(inputs/'body.json'), read(inputs/'ue_field_sweater.json'))
rigid = np.unique(np.array(data['triangles'])[data['harness_face_count']:])
back = float(lift_required(v[rigid], np.tile([0., -1., 0.], (len(rigid), 1)), equations, .4).max())+.05
v[:, 1] -= back*mask
for part in data['parts']:
    if not part['name'].startswith('shoulder_return_'):
        continue
    rings = np.array(part['rows']); base = v[rings].mean(axis=1)
    _, _, outward = frame(base, equations)
    total = np.zeros(len(rings))
    # Broad shoulder faces and connecting quads, not only their corner vertices.
    for iteration in range(4):
        points = v[rings]
        samples = np.concatenate([points*(1-f)+np.roll(points, -1, axis=1)*f for f in (0., .25, .5, .75)], axis=1)
        requirements = lift_required(samples.reshape(-1, 3), np.repeat(outward, samples.shape[1], axis=0), equations, .5).reshape(len(rings), -1).max(axis=1)
        requirements[[0, -1]] = 0.
        if requirements.max() < 1e-4:
            break
        updated = smooth_lift(total+requirements, pin_ends=True)
        v[rings] += ((updated-total)[:, None]*outward)[:, None, :]
        total = updated
    # Cap centres have their own vertices, and must share the endpoint offset.
    for i, end in enumerate((0, -1)):
        cap = part['cap_faces'][i*12:(i+1)*12]
        centre = set(np.array(data['triangles'])[cap].flat)-set(rings[end])
        for vertex in centre:
            v[vertex] = v[rings[end]].mean(axis=0)
    part['path'] = v[rings].mean(axis=1).tolist()
    part['response_r2_fit_lift_cm'] = total.tolist()
# Move the sewn chest tabs and adjusters with their newly fitted pad stations.
# Otherwise raising a shoulder pad would leave its fixed chest attachment behind.
parts = {part['name']: part for part in data['parts']}
tab_shifts = []
for index, side in enumerate(('l', 'r')):
    pad_rows = np.array(parts['shoulder_return_'+side]['rows'])
    old_path = old[pad_rows].mean(axis=1)
    pad_delta = (v[pad_rows]-old[pad_rows]).mean(axis=1)
    for name in ('sternum_tab_'+str(index), 'adjuster_'+side):
        part = parts[name]
        faces = part.get('faces', part.get('side_faces', [])+part.get('cap_faces', []))
        vertices = np.unique(np.array(data['triangles'])[faces])
        station = np.linalg.norm(old_path-old[vertices].mean(axis=0), axis=1).argmin()
        shift = pad_delta[station];v[vertices] = old[vertices]+shift
        if part.get('rows'):
            part['path'] = v[np.array(part['rows'])].mean(axis=1).tolist()
            tab_shifts.append(shift)
sternum = parts['sternum']; rings = np.array(sternum['rows'])
for j, vertices in enumerate(rings):
    f = j/(len(rings)-1);v[vertices] = old[vertices]+tab_shifts[0]*(1-f)+tab_shifts[1]*f
for i, end in enumerate((0, -1)):
    cap = sternum['cap_faces'][i*12:(i+1)*12]
    centre = set(np.array(data['triangles'])[cap].flat)-set(rings[end])
    for vertex in centre:v[vertex] = old[vertex]+tab_shifts[i]
sternum['path'] = v[rings].mean(axis=1).tolist()
hardware = np.unique(np.array(data['triangles'])[parts['sternum_adjuster']['faces']])
v[hardware] = old[hardware]+(tab_shifts[0]+tab_shifts[1])*.5
data['positions'] = v.tolist()
mesh = Mesh(data['bones'], data['materials']); mesh.data = data; mesh.normals()
out = R/'MountainSweaterR2'; out.mkdir(exist_ok=True)
write(out/'authored.json', data)
write(out/'mask.json', dict(positions=v.tolist(), values=maskdata['values']))
write(out/'fit_delta.json', dict(before=old.tolist(), delta=(v-old).tolist(), bag_rear_cm=back,
                                input_asset='/Game/Characters/BackpackMotion20261022/Mountain/SK_Jason_Backpack_Sweater.SK_Jason_Backpack_Sweater', source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                                asset='/Game/Characters/BackpackMotion20261022/MountainR2/SK_Jason_Backpack_Sweater.SK_Jason_Backpack_Sweater'))
print('MOUNTAIN_SWEATER_REFIT', back, float(np.linalg.norm(v-old, axis=1).max()), flush=True)
