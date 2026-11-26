"""Patch layout.json, TemperateVillageLayout.inl, TemperateVillageGroundData.inl, and RoadMask.png for ExpandedYardR42."""
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'SourceAssets/TemperateHillsVillage'
GROUND_INL = ROOT / 'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl'
LAYOUT_INL = ROOT / 'Source/FPSGAME/WorldGeneration/TemperateVillageLayout.inl'
BATCH = Path(r'F:/FPSGAMEData/ArtProduction/HillsVillageStable/ExpandedYardR42-20261125')

# 1. Backup prior editable data files before modification.
backup_dir = BATCH / 'Before/VillageData'
backup_dir.mkdir(parents=True, exist_ok=True)
for src in (SOURCE / 'layout.json', SOURCE / 'RoadMask.png', GROUND_INL, LAYOUT_INL):
    dst = backup_dir / src.name
    if not dst.exists():
        shutil.copy2(src, dst)

# 2. Update layout.json: relocate house 09 to (-34.5, 31.5, yaw 0) so public_frame = (-34.5, 27.0, 0).
plan = json.loads((SOURCE / 'layout.json').read_text(encoding='utf-8'))
for h in plan['houses']:
    if h[0] == '09':
        h[3], h[4], h[5] = -34.5, 31.5, 0
for r in plan['roads']:
    if r.get('name') == '南侧居住支路':
        r['points'] = [[-35.0, 23.0], [-34.5, 25.2], [-34.5, 26.2]]
(SOURCE / 'layout.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('UPDATED layout.json plot 09 -> (-34.5, 31.5, 0)')

# 3. Regenerate TemperateVillageLayout.inl via draw_plan.py --header-only.
draw_plan = ROOT / 'Tools/WorldGeneration/AbandonedVillage/draw_plan.py'
subprocess.run([sys.executable, str(draw_plan), '--header-only'], check=True)
print('REGENERATED TemperateVillageLayout.inl')

# 4. Locally flatten Relief and clear Gravel in TemperateVillageGroundData.inl + paint Gunshop tread on RoadMask.png.
# Exact same non-destructive local-patch pattern as smith_apron.py: untouched streets keep identical gravel & relief.
sys.path.insert(0, str(ROOT / 'Tools/WorldGeneration/AbandonedVillage'))
from village_ground_relief import write_native, box
from village_tread import ramp, soil_variation, tread

data = GROUND_INL.read_text(encoding='utf-8')
grid_txt = data.split('Relief[Rows][Columns]={', 1)[1].split('};', 1)[0]
stones_txt = data.split('constexpr FGravel Gravel[]={', 1)[1].split('};', 1)[0]


def parse_records(txt):
    return [tuple(map(int, g.split(','))) for g in re.findall(r'\{([0-9,\-]+)\}', txt)]


height = np.array(parse_records(grid_txt), dtype='f')
stones = parse_records(stones_txt)

ex, ey = plan['surface_extent_m']
xx = np.linspace(-ex, ex, height.shape[1])[None, :]
yy = np.linspace(-ey, ey, height.shape[0])[:, None]

# Flatten relief cleanly inside:
#   a) Relocated Gunshop 09 footprint & doorway approach: center (-34.5, 31.2), half (6.2, 6.2)
#   b) Expanded Stable west paddock + Stablemaster house + rear strip: center (33.7, 39.6), half (25.0, 7.5)
d_gun = box(xx, yy, (-34.5, 31.2), (6.2, 6.2))
d_stb = box(xx, yy, (33.7, 39.6), (25.0, 7.5))
clear = np.minimum(d_gun, d_stb)
height *= ramp(clear / 1.15)


def clear_scalar(x_m, y_m):
    dg = math.hypot(max(abs(x_m - (-34.5)) - 6.0, 0.0), max(abs(y_m - 31.2) - 6.0, 0.0))
    if abs(x_m - (-34.5)) <= 6.0 and abs(y_m - 31.2) <= 6.0:
        dg = -1.0
    ds = math.hypot(max(abs(x_m - 33.7) - 24.8, 0.0), max(abs(y_m - 39.6) - 7.3, 0.0))
    if abs(x_m - 33.7) <= 24.8 and abs(y_m - 39.6) <= 7.3:
        ds = -1.0
    return min(dg, ds)


before_stones = len(stones)
stones = [p for p in stones if clear_scalar(p[0] * 0.01, p[1] * 0.01) > 0.01 * p[2] + 0.12]
write_native(height, stones, plan, sample_stride=1)
print(f'PATCHED TemperateVillageGroundData.inl (gravel {before_stones} -> {len(stones)})')

# Paint subtle trodden soil link from South Lane (-35, 23) to new Gunshop threshold (-34.5, 27.0) on RoadMask.png
with Image.open(SOURCE / 'RoadMask.png') as im:
    arr = np.array(im.convert('RGBA'))
h_img, w_img = arr.shape[:2]
px = ((np.arange(w_img)[None, :] + 0.5) / w_img - 0.5) * (2 * ex)
py = ((np.arange(h_img)[:, None] + 0.5) / h_img - 0.5) * (2 * ey)
xs = np.flatnonzero((px[0] >= -41.5) & (px[0] <= -28.0))
ys = np.flatnonzero((py[:, 0] >= 21.5) & (py[:, 0] <= 29.0))
gx = px[:, xs]
gy = py[ys, :]
noise = soil_variation(gx, gy, 0.85, 7099)
grit = soil_variation(gx, gy, 0.24, 7109)
walk = tread(gx, gy, [(-34.5, 27.0, 0.95), (-35.2, 25.8, 0.72), (-35.5, 24.4, 0.68), (-35.0, 23.0, 0.85)], 0.06 * noise)
worn = ramp((walk + 0.42 + 0.12 * noise + 0.06 * grit) / 0.78)
outside_house = ramp((27.05 - gy) / 0.30)
tile = arr[ys[0]:ys[-1] + 1, xs[0]:xs[-1] + 1]
tile[:, :, 1] = np.maximum(tile[:, :, 1], np.rint(255 * worn * outside_house * 0.76).astype('uint8'))
tile[:, :, 2] = np.maximum(tile[:, :, 2], np.rint(255 * worn * outside_house * 0.38).astype('uint8'))
Image.fromarray(arr).save(SOURCE / 'RoadMask.png')
print('PATCHED RoadMask.png gunshop approach tread')
