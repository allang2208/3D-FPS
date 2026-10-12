import sys,json,math
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;sys.path.insert(0,str(O))
from grip_math import load,pose,matrix
d=load('SK_Super90_V7');profiles=load('profiles_after');poses=load('poses')
p=next(c for c in profiles['angled']['clips'] if 'A_Super90_idle.' in c['base'])
w,l=pose(d,poses[p['base']]['samples'][0],p);norm=matrix(d['rest']['WPN_root'])@w['WPN_root'].inverted();w={n:norm@m for n,m in w.items()}
targets=json.loads((O/'grasp_targets.json').read_text())['angled']
for n,t in targets.items():
    m=matrix(t);rest=matrix(d['rest'][d['parents'][n]]).inverted()@matrix(d['rest'][n])
    print(n,'world_pos_mm',round((m.translation-w[n].translation).length*10,3),'angle_deg',round(math.degrees(m.to_quaternion().rotation_difference(w[n].to_quaternion()).angle),3),'local_pos_diff_mm',round((rest.translation-matrix(l[n]).translation).length*10,3))
