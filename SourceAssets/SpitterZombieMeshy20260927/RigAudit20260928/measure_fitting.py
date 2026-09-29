"""Measure fitting changes without writing animation or mesh assets."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;author=ROOT.parent/'LibraryMotionV7/author_library_motion.py'
prefix=author.read_text(encoding='utf-8').split("report={'movement':{}")[0]
ns={'__file__':str(author),'__name__':'diagnostic_helpers'}
exec(compile(prefix,str(author),'exec'),ns)
rig=ns['rig'];rig.animation_data_clear();rows={}
def stat(xs):return dict(zip(['min','median','p95','max'],map(float,np.percentile(xs,[0,50,95,100]))))
for role in ['Walk_A','Walk_B','Walk_C','Run_A']:
    seconds=ns['metadata'][role]['seconds'];frames=[]
    ns['apply'](ns['sample'](role,0));p0=ns['point']('Hips').copy()
    ns['apply'](ns['sample'](role,seconds));drift=ns['point']('Hips')-p0
    for t in np.linspace(0,seconds,61):
        ns['apply'](ns['sample'](role,float(t)))
        ns['move_hips'](Vector((-drift.x*t/seconds,-drift.y*t/seconds,0)))
        ns['gaze']();before=ns['point']('Hips').copy();ns['ground']()
        frames.append(dict(t=float(t),hip_before=list(before),hip_after=list(ns['point']('Hips'))))
    offsets=[r['hip_after'][2]-r['hip_before'][2] for r in frames]
    rows[role]=dict(ground_offset_m=stat(offsets),ground_offset_range_m=max(offsets)-min(offsets),frames=frames)
(ROOT/'fitting_comparison.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print('FITTING_MEASURED',json.dumps({k:{a:b for a,b in v.items() if a!='frames'} for k,v in rows.items()}))
