"""Read-only source-pose diagnosis on the saved Jason skin (orthographic figure)."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

root = Path('D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/ThirdPersonMeleeRegression20261010'
out.mkdir(parents=True, exist_ok=True)
geo = json.loads((root/'SourceAssets/JasonPlayer20261003/Jason.json').read_text())
rig = json.loads((root/'SourceAssets/ThirdPersonSwordKwang20261006/retargeted-poses.json').read_text())
names, parents = rig['names'], rig['parents']
assert names == [b['name'] for b in geo['bones']]
points = np.array(geo['positions']); triangles = np.array(geo['triangles'], dtype=int)
def fk(frame):
    frame = np.asarray(frame)
    m = np.zeros((len(names), 4, 4)); m[:, 3, 3] = 1
    m[:, :3, :3] = R.from_quat(frame[:, 3:7]).as_matrix() * frame[:, None, 7:10]
    m[:, :3, 3] = frame[:, :3]
    for i, p in enumerate(parents):
        if p >= 0: m[i] = m[p] @ m[i]
    return m
inverse_bind = np.linalg.inv(fk(rig['reference']))
weights = {}
for i, influences in enumerate(geo['weights']):
    for bone, weight in influences:
        weights.setdefault(bone, []).append((i, weight))
weights = {b: (np.array(rows)[:, 0].astype(int), np.array(rows)[:, 1, None]) for b, rows in weights.items()}
def skin(frame):
    transform = fk(frame) @ inverse_bind
    result = np.zeros_like(points)
    for bone, (ids, weight) in weights.items():
        result[ids] += (points[ids] @ transform[bone, :3, :3].T + transform[bone, :3, 3])*weight
    return result
versions = {
    'Kwang V2': root/'SourceAssets/ThirdPersonSwordKwang20261006/adapted-actions.json',
    'Grip V3': root/'SourceAssets/ThirdPersonSwordGrip20261007/adapted-actions.json',
}
cases = [('DashOverhead', .40), ('DashOverhead', .65), ('Whirlwind.Loop', .5)]
fig, axes = plt.subplots(2, 3, figsize=(12, 8), facecolor='#20252c')
for row, (label, path) in enumerate(versions.items()):
    data = json.loads(path.read_text())
    for col, (clip, phase) in enumerate(cases):
        frames = data['clips'][clip]['frames']; frame = frames[round(phase*(len(frames)-1))]
        p = skin(frame)
        # Front three-quarter view, with proper depth sorting and neutral lighting.
        view = R.from_euler('z', 18 if col < 2 else 165, degrees=True).as_matrix()
        p = p @ view.T; faces = p[triangles]
        normal = np.cross(faces[:, 1]-faces[:, 0], faces[:, 2]-faces[:, 0])
        normal /= np.maximum(np.linalg.norm(normal, axis=1, keepdims=True), 1e-8)
        light = np.array([-.3, -.8, .5]); light /= np.linalg.norm(light)
        shade = .55 + .4*np.abs(normal @ light)
        colors = np.stack([shade*.91, shade*.82, shade*.72], axis=1)
        order = np.argsort(-faces[:, :, 1].mean(axis=1))
        ax = axes[row, col]; ax.set_facecolor('#20252c')
        ax.add_collection(PolyCollection(faces[order][:, :, [0, 2]], facecolors=colors[order], edgecolors='none'))
        ax.set_xlim(-80, 80); ax.set_ylim(72, 185); ax.set_aspect('equal'); ax.axis('off')
        ax.set_title(f'{label} | {clip} {phase:.0%}', color='white', fontsize=11)
fig.tight_layout()
fig.savefig(out/'source-skin-comparison.png', dpi=140, facecolor=fig.get_facecolor())
print(out/'source-skin-comparison.png')
