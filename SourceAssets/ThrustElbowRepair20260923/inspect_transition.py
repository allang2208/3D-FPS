import bpy,sys,json,math
from pathlib import Path
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from diagnose_elbows import matrix,pack,rebuild,PRIOR
d=json.loads((PRIOR/'Standard/source.json').read_text());v1=json.loads((PRIOR/'Standard/Thrust_patch.json').read_text());patch=json.loads((P/'Standard/Thrust_patch.json').read_text())
previous={};steps=[]
for row,old,new in zip(d['clips']['Thrust']['samples'],v1['samples'],patch['samples']):
    _,cur=rebuild(row,old,d['parents']);_,fix=rebuild({'world':{n:pack(m) for n,m in cur.items()}},new,d['parents'])
    for n in ('upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','lowerarm_twist_02_l','lowerarm_twist_02_r'):
        p=d['parents'][n];c=(cur[p].inverted()@cur[n]).to_quaternion();f=(fix[p].inverted()@fix[n]).to_quaternion()
        if n in previous:
            pc,pf=previous[n];angle=lambda a,b:math.degrees(2*math.acos(min(1,abs(a.dot(b)))))
            steps.append((angle(f,pf),angle(c,pc),row['seconds'],n))
        previous[n]=(c,f)
print('LARGEST_LOCAL_STEPS',sorted(steps,reverse=True)[:14])
