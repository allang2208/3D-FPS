import json, sys
from pathlib import Path
j = json.load(open(Path(sys.argv[1]), encoding='utf-8'))
print('rest seg cm', j['rest_segments_cm'])
print('last vs idle cm', j['last_vs_idle_bone_delta_cm'])
hdr = ('frame', 'eye_mm', 'fwd_mm', 'near', 'frust', 'wrist_cm', 'seg_se', 'seg_ew', 'clav_shift')
print(''.join(f'{h:>10}' for h in hdr))
for r in j['frames']:
    s = r['seg_cm']
    row = (r['frame'], r['min_eye_dist_mm'], r['min_forward_mm'], r['near_verts'],
           r['near_in_frustum'], r['wrist_shoulder_cm'], s['shoulder_elbow'], s['elbow_wrist'],
           r['local_shift_cm']['clavicle_l'])
    print(''.join(f'{v:>10}' for v in row))
