import json
import sys
from pathlib import Path

JOB = Path(r'D:\FPS3D\FPSGAME\SourceAssets\SVDReloadLeftArm20260925')
b = json.load(open(JOB / 'coverage_reload.json'))
a = json.load(open(JOB / 'coverage_reload_after.json'))
db = {r['frame']: r['fraction'] for r in b}
da = {r['frame']: r['fraction'] for r in a}
print('peak before %.4f at %s' % (max(db.values()), [f for f, v in db.items() if v == max(db.values())]))
print('peak after  %.4f at %s' % (max(da.values()), [f for f, v in da.items() if v == max(da.values())]))
print('frame  before   after')
for f in sorted(db):
    if 260 <= f <= 360 or db[f] > 0.05:
        print('%6d %8.4f %8.4f' % (f, db[f], da.get(f, 0.0)))
