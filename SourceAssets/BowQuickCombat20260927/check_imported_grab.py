"""Targeted imported-pose comparison for the user's missing right-hand report."""
import json,bpy
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).parent
script=P/'generated_action_v2.py';ns={'__file__':str(script)}
exec(compile(script.read_text().split('bpy.ops.wm.open_mainfile')[0],str(script),'exec'),ns)
actual=json.loads((P/'imported-after.json').read_text())
def mat(v):
    x,y,z,w=v['q'];a=Quaternion((w,x,y,z)).to_matrix().to_4x4();a.translation=Vector(v['p']);return a
max_error=0.;contacts=[]
for row in actual['poses']:
    t=row['t'];source=ns['pose'](t)
    max_error=max(max_error,max((source[n].translation-Vector(row['bones'][n]['p'])).length for n in ('hand_l','hand_r','bow_grip')))
    if .14<=t<=.62:
        contacts.append(mat(row['bones']['bow_grip']).inverted()@Vector(row['bones']['hand_r']['p']))
drift=max((p-contacts[0]).length for p in contacts)
result={'length_seconds':actual['length'],'maximum_sampled_source_import_error_cm':max_error,
        'sampled_right_grip_drift_cm':drift,'grasp_zone':'10 cm above left grasp',
        'offline_framing':'16:9; current catalog hip offset; 60, 75, 90 degree vertical FOV',
        'gameplay_tested':False}
(P/'inspection-result.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
