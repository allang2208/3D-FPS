"""Compare the installed quick-melee grasp with its own accepted idle grip."""
from pathlib import Path
import sys,json,hashlib,numpy as np
from scipy.spatial.transform import Rotation as R
O=Path(__file__).resolve().parent;R6=O.parent/'QuickMeleeRecoveryR6_20261020';R5=O.parent/'QuickMeleeElbowR5_20261020'
sys.path.insert(0,str(O.parent/'QuickMeleeHandR3_20261019'))
import check_surfaces as s
from action_framing import camera_for_frame

def measure(p,idle):
    root,h,l=[s.ids[n] for n in ['WPN_root','hand_r','lowerarm_r']]
    current=s.relative(p[root],p[h]);wanted=s.relative(idle[root],idle[h])
    hd=s.rigid(p[h])[:3,:3]@s.rigid(s.ref[h])[:3,:3].T
    fore=s.unit(p[h,:3,3]-p[l,:3,3]);native=s.unit(s.ref[h,:3,3]-s.ref[l,:3,3])
    digits=[j for j,n in enumerate(s.names) if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
    differences=[]
    for j in digits:
        par=s.parents[j];a=s.relative(p[par],p[j]);b=s.relative(idle[par],idle[j])
        differences.append((s.names[j],float(np.degrees((R.from_matrix(s.rigid(a)[:3,:3])*R.from_matrix(s.rigid(b)[:3,:3]).inv()).magnitude()))))
    return {'grip_offset_cm':float(np.linalg.norm((current[:3,3]-wanted[:3,3])*np.linalg.norm(p[root,:3,:3],axis=0))),
        'grip_rotation_degrees':float(np.degrees((R.from_matrix(s.rigid(current)[:3,:3])*R.from_matrix(s.rigid(wanted)[:3,:3]).inv()).magnitude())),
        'wrist_axis_bend_degrees':float(np.degrees(np.arccos(np.clip(fore@(hd@native),-1,1)))),
        'worst_digit_local_rotation':max(differences,key=lambda x:x[1]),'corrective_signature':s.driver.signature(s.matrix_pose(p),'r')}

if __name__=='__main__':
    manifest=json.loads((R6/'install_receipt.json').read_text())['assets']
    for family,x in manifest.items():
        actual=Path('D:/FPS3D/FPSGAME/Content')/(x['path'].removeprefix('/Game/')+'.uasset')
        assert hashlib.sha256(actual.read_bytes()).hexdigest()==x['sha256'],family+' changed since R6'
    capture=json.loads((R6/'native-saved-glove.json').read_text());report={}
    for family in capture['families']:
        order=[family['names'].index(n) for n in s.names];idle=s.matrices(np.array(family['frames'][0]['bones'])[order]);rows=[]
        for row in family['frames']:
            p=s.matrices(np.array(row['bones'])[order]);rows.append({'frame':row['frame'],**measure(p,idle)})
        report[family['family']]=rows
    (O/'diagnosis-r6.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({'base_samples':[r for r in report['base'] if r['frame'] in [-1,12,20,40,60,68,72,84,96,108]],
        'families':{f:{'max_grip_rotation':max(r['grip_rotation_degrees'] for r in rows),'max_grip_offset_cm':max(r['grip_offset_cm'] for r in rows),
        'max_wrist_bend_degrees':max(r['wrist_axis_bend_degrees'] for r in rows)} for f,rows in report.items()}},indent=2),flush=True)
