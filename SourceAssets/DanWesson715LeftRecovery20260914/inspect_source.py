"""Inspect the requested closing/left-hand recovery interval only."""
import bpy, json
from pathlib import Path
_recovery_task_dir = Path(__file__).resolve().parent
SRC = _recovery_task_dir.parent / 'DanWesson715ReloadNatural20260914/author_actions.py'
__file__ = str(SRC)
exec(compile(SRC.read_text(encoding='utf-8').split('\nbake_source=')[0], str(SRC), 'exec'), globals())
O = _recovery_task_dir
report = {'cameras': [], 'meshes': [], 'poses': {}}
for ob in s.objects:
    if ob.type == 'CAMERA':
        report['cameras'].append({'name':ob.name, 'matrix':[list(v) for v in ob.matrix_world], 'lens':ob.data.lens})
    if ob.type == 'MESH' and not ob.hide_render:
        report['meshes'].append({'name':ob.name, 'dimensions':list(ob.dimensions)})
for kind, sampler, times in [('single_0_6', lambda t: pose_single(0,6,t), [7.90,8.10,8.37,8.60,8.80]),
                             ('speed_0', lambda t: pose_speed(0,t*3.85/3.6), [2.53,2.68,2.95,3.23,3.60])]:
    report['poses'][kind] = []
    for t in times:
        p = sampler(t)
        report['poses'][kind].append({'time':t, 'bones':{n:{'position':list(p[n].translation), 'quaternion':list(p[n].to_quaternion())} for n in ['hand_l','lowerarm_l','upperarm_l','hand_r','WPN_root','WPN_Loader']}})
(O/'source-close.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DW715_CLOSE_SOURCE',str(O/'source-close.json'),flush=True)
