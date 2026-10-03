"""Is the forearm sampling a non-skin region of the colour atlas?

The screenshot's dominant defect is a large hard-edged orange patch on the arm, which is a
UV/atlas problem, not a micro-detail one.  This samples the actual skin colour atlas at the
actual UVs of every vertex and reports the colour per bone group, so "which part of the arm
gets the orange" is answered from data.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

OUTFIT = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7')
ATLAS = Path(r'D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260924\OriginalShapeBareM4'
             r'\RefinedSkinV3\T_M4OriginalShape_SkinColour.png')

GROUPS = {
    'upperarm': ('upperarm_l', 'upperarm_r', 'upperarm_twist_01_l', 'upperarm_twist_01_r',
                 'upperarm_twist_02_l', 'upperarm_twist_02_r'),
    'lowerarm': ('lowerarm_l', 'lowerarm_r', 'lowerarm_twist_01_l', 'lowerarm_twist_01_r',
                 'lowerarm_twist_02_l', 'lowerarm_twist_02_r'),
    'hand': ('hand_l', 'hand_r'),
    'fingers': tuple(b for b in (
        'thumb_01_l', 'thumb_02_l', 'thumb_03_l', 'index_01_l', 'index_02_l', 'index_03_l',
        'middle_01_l', 'middle_02_l', 'middle_03_l', 'ring_01_l', 'ring_02_l', 'ring_03_l',
        'pinky_01_l', 'pinky_02_l', 'pinky_03_l',
        'thumb_01_r', 'thumb_02_r', 'thumb_03_r', 'index_01_r', 'index_02_r', 'index_03_r',
        'middle_01_r', 'middle_02_r', 'middle_03_r', 'ring_01_r', 'ring_02_r', 'ring_03_r',
        'pinky_01_r', 'pinky_02_r', 'pinky_03_r')),
}

d = json.loads((OUTFIT / 'Authored' / 'PKM.json').read_text(encoding='utf-8'))
UV = np.array(d['uv'], dtype=np.float64)          # (ntri, 3 corners, 2)
T = np.array(d['triangles'], dtype=np.int64)
W = d['weights']
nv = len(d['positions'])

img = Image.open(ATLAS).convert('RGB')
A = np.asarray(img, dtype=np.float64) / 255.0
H, Wd = A.shape[:2]
print('atlas %s  %dx%d' % (ATLAS.name, Wd, H))

# per-vertex UV: average the corner UVs of every triangle touching the vertex
acc = np.zeros((nv, 2))
cnt = np.zeros(nv)
for c in range(3):
    np.add.at(acc, T[:, c], UV[:, c])
    np.add.at(cnt, T[:, c], 1.0)
u = acc / np.maximum(cnt, 1.0)[:, None]

# wrap and sample
uu = np.mod(u[:, 0], 1.0)
vv = np.mod(u[:, 1], 1.0)
px = np.clip((uu * Wd).astype(int), 0, Wd - 1)
py = np.clip((vv * H).astype(int), 0, H - 1)
col = A[py, px]                                   # (nv, 3) display-referred

# "orange" = noticeably more red than blue
orange = (col[:, 0] - col[:, 2] > 0.10) & (col[:, 0] > 0.35)

print('\n%-10s %7s %8s %8s %8s %8s %9s' %
      ('group', 'verts', 'R', 'G', 'B', 'R-B', 'orange%'))
for g, bones in GROUPS.items():
    m = np.array([sum(e.get(b, 0.0) for b in bones) for e in W]) > 0.5
    if not m.any():
        print('  %-8s (none)' % g)
        continue
    c = col[m]
    print('  %-8s %7d %8.3f %8.3f %8.3f %8.3f %8.1f%%'
          % (g, m.sum(), c[:, 0].mean(), c[:, 1].mean(), c[:, 2].mean(),
             (c[:, 0] - c[:, 2]).mean(), 100.0 * orange[m].mean()))

# where along the forearm does orange appear?  distance from the elbow along the arm
lo = np.array([sum(e.get(b, 0.0) for b in GROUPS['lowerarm']) for e in W])
up = np.array([sum(e.get(b, 0.0) for b in GROUPS['upperarm']) for e in W])
arm = (lo > 0.3) | (up > 0.3)
if arm.any():
    print('\n--- orange by bone weight share (forearm fraction) ---')
    for lo_, hi_ in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.01)):
        m = arm & (lo >= lo_) & (lo < hi_)
        if m.any():
            print('  lowerarm weight %.1f-%.1f : %6d verts  R-B %+.3f  orange %5.1f%%'
                  % (lo_, hi_, m.sum(), (col[m][:, 0] - col[m][:, 2]).mean(),
                     100.0 * orange[m].mean()))

print('\n--- how much of the atlas is orange? ---')
print('  atlas pixels with R-B > 0.10 and R > 0.35: %.2f%%'
      % (100.0 * ((A[:, :, 0] - A[:, :, 2] > 0.10) & (A[:, :, 0] > 0.35)).mean()))
print('\nCOLOUR_SAMPLE_DONE')