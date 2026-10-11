"""Compare just the requested arm segment after FBX import and compression."""
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'arm_clearance.py').read_text(encoding='utf-8'),str(O/'arm_clearance.py'),'exec'))
saved=json.loads((O/'saved_pose_samples.json').read_text(encoding='utf-8'))
candidate={b:[{n:Matrix(m) for n,m in p.items()} for p in ps] for b,ps in json.loads((O/'candidate_poses.json').read_text()).items()}
report={'scope':'normal/empty counts 1 and 7; 10 release/bolt/endpoint samples per clip','clips':{},'runtime_tested':False}
for name,clip in saved['clips'].items():
    branch='empty' if 'empty' in name else 'normal'
    row={'length':clip['length'],'source_position_error_cm':0.,'compressed_position_error_cm':0.,'compressed_rotation_error_deg':0.,'source_hand_unchanged_error':0.}
    for s in clip['samples']:
        f=s['frame'];p=candidate[branch][f]
        for n,raw in s['SOURCE'].items():
            expected=C@p[n]@K[n];t=mat(raw);c=mat(s['COMPRESSED'][n])
            row['source_position_error_cm']=max(row['source_position_error_cm'],(expected.translation-t.translation).length)
            row['compressed_position_error_cm']=max(row['compressed_position_error_cm'],(c.translation-t.translation).length)
            dq=c.to_quaternion().rotation_difference(t.to_quaternion());a=math.degrees(dq.angle);a=min(a,360-a)
            row['compressed_rotation_error_deg']=max(row['compressed_rotation_error_deg'],a)
        row['source_hand_unchanged_error']=max(row['source_hand_unchanged_error'],max(abs(p['hand_l'][i][j]-source_rows[branch][f]['hand_l'][i][j]) for i in range(4) for j in range(4)))
    report['clips'][name]=row
def axes(d,up):
    r=mat(d['WPN_root']);x=(Vector(d['WPN_FrontSight'][:3])-Vector(d['WPN_RearSight'][:3])).normalized()
    z=r.to_quaternion()@Vector(up);y=z.cross(x).normalized();z=x.cross(y).normalized()
    return Matrix((x,y,z)).transposed().to_quaternion()
frames=saved['framing'];base=Quaternion(Vector((0,0,1)),math.pi/2)
q=base@axes(frames['M4'],(0,0,1))@axes(frames['Super90'],(0,-1,0)).inverted()
cp=Vector((6,7,-7))+base@Vector(frames['M4']['hand_r'][:3])-q@Vector(frames['Super90']['hand_r'][:3])
report['camera_anchor_position_error_cm']=(cp-Vector(camera['location'])).length
angle=math.degrees(q.rotation_difference(Quaternion(camera['rotation'])).angle)
report['camera_anchor_rotation_error_deg']=min(angle,360-angle)
(O/'camera_current.json').write_text(json.dumps(dict(rotation=list(q),location=list(cp)),indent=2),encoding='utf-8')
(O/'saved_pose_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('R20_SAVED_COMPARISON',json.dumps(report),flush=True)
