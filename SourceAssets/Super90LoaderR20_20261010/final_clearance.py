"""Re-evaluate the delivered poses with the current saved idle framing."""
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'arm_clearance.py').read_text(encoding='utf-8'),str(O/'arm_clearance.py'),'exec'))
camera=json.loads((O/'camera_current.json').read_text())
cm=Matrix.Translation(Vector(camera['location']))@Quaternion(camera['rotation']).to_matrix().to_4x4()@C
cam_matrix=np.asarray(cm)
out={'camera':camera,'fov_horizontal':112,'aspect':1276/837,'rows':[],'runtime_tested':False}
candidate=json.loads((O/'candidate_poses.json').read_text())
for branch in ('normal','empty'):
    for f in range(110,127 if branch=='normal' else 163):
        p=source_rows[branch][f];q={n:Matrix(v) for n,v in candidate[branch][f].items()}
        a=cloth_points(p);b=cloth_points(q)
        out['rows'].append(dict(branch=branch,frame=f,before=coverage(a,proximal),after=coverage(b,proximal),before_upper=coverage(a,upper),after_upper=coverage(b,upper)))
(O/'current_camera_clearance.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('CURRENT_FRAME_CLEARANCE',json.dumps([r for r in out['rows'] if r['branch']=='empty' and r['frame'] in (120,138,150)]),flush=True)
