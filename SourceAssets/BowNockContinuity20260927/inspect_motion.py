"""Scoped source-motion inspection requested for the nock continuity issue.

Evaluate authored contact trajectories and adjacent skeletal endpoints only.
No game, render, input automation, or asset mutation.
"""
from pathlib import Path
import json,math
P=Path(__file__).parent

def definitions(path):
    source=path.read_text(encoding='utf8')
    source=source.split('bpy.ops.wm.read_factory_settings',1)[0]
    scope={'__file__':str(path),'__name__':'motion_inspection'}
    exec(compile(source,str(path),'exec'),scope)
    return scope

result={}
for name,path in [('v16',P.parent/'BowNockFlow20260927/generated_actions.py'),('v21',P/'author_actions.py')]:
    s=definitions(path);pose=s['pose'];durations=s['DURATIONS'];draw=pose('Draw',0.)
    rows={}
    for role in ('Nock','QuickNock','ChainNock'):
        duration=durations[role]
        contact=(.82 if role=='Nock' else .90)*duration
        h=.00001
        before=pose(role,contact-h)['bow_nock'].translation
        at=pose(role,contact)['bow_nock'].translation
        after=pose(role,contact+h)['bow_nock'].translation
        vin=(at-before)/h;vout=(after-at)/h
        end=pose(role,duration)
        differences={}
        for bone in ('hand_r','lowerarm_r','upperarm_r','bow_grip'):
            qa=end[bone].to_quaternion();qb=draw[bone].to_quaternion()
            angle=math.degrees(2*math.acos(min(1.,abs(qa.dot(qb)))))
            differences[bone]={'position_cm':(end[bone].translation-draw[bone].translation).length,
                               'rotation_degrees':angle}
        rows[role]={'contact_speed_in_cm_s':vin.length,'contact_speed_out_cm_s':vout.length,
            'contact_velocity_step_cm_s':(vin-vout).length,'endpoint_to_Draw0':differences}
    result[name]=rows
(P/'motion-analysis.json').write_text(json.dumps({'scope':'authored source trajectories; not engine playback',
    'results':result,'gameplay_tested':False},indent=2),encoding='utf8')
print('NOCK_MOTION_SOURCE_ANALYSIS',json.dumps(result))
