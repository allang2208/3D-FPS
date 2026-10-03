"""Diff A762 vs PKM ScopeBody verts in cutout window; show what tuck changed."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector

O = Path(r'D:\FPS3D\FPSGAME\SourceAssets\PSO1Russian20260923')
OUT = O / 'inspect_akm_a762'
DELTA = Vector((0.010, -0.015, 0.035))
AXIS_Z = 0.1024

def load_body_local(path):
    bpy.ops.wm.open_mainfile(filepath=str(path))
    body = bpy.data.objects['PSO_ScopeBody']
    mw = body.matrix_world
    return [(mw @ v.co) - DELTA for v in body.data.vertices]

a = load_body_local(OUT / 'PSO1_A762_Editable.before-tuck.blend')
p = load_body_local(O / 'PSO1_PKM_Editable.blend')
assert len(a)==len(p)
moved=[]
for i,(va,vp) in enumerate(zip(a,p)):
    d=(va-vp).length
    if d>1e-5:
        moved.append({
            'i':i,'d':round(d,5),
            'a':[round(va.x,4),round(va.y,4),round(va.z,4)],
            'p':[round(vp.x,4),round(vp.y,4),round(vp.z,4)],
            'ar':round(math.hypot(va.x,va.z-AXIS_Z),4),
            'pr':round(math.hypot(vp.x,vp.z-AXIS_Z),4),
        })
moved.sort(key=lambda m:-m['d'])
# region stats
in_win=[m for m in moved if m['a'][0]>-0.01 and -0.12<m['a'][1]<0.05 and m['a'][2]<0.12]
report={
    'moved_total':len(moved),
    'moved_in_window':len(in_win),
    'max_d':moved[0]['d'] if moved else 0,
    'top20':moved[:20],
    'window_top15':in_win[:15],
    'r_reduced': sum(1 for m in in_win if m['pr']+1e-6 < m['ar']),
}
(OUT/'a762_vs_pkm_body.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DIFF', json.dumps({
    'moved':len(moved),'window':len(in_win),'max_d':report['max_d'],
    'r_reduced':report['r_reduced'],
    'top5':moved[:5],
}), flush=True)
