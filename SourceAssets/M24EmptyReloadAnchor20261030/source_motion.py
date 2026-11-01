"""Read current root curves to locate the unwanted translation channel."""
import json,math,bisect,ast
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent
D=json.loads((O/'before.json').read_text());names=D['names'];parents=D['parents']
C=Matrix(json.loads((O.parent/'M24Hold20261027/hip-calibration.json').read_text())['hip_transform'])@Matrix.Diagonal((100,-100,100,1))
K=Matrix.Diagonal((1,-1,1,1))
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for name in ('qlerp','sample'):
    exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)),name,'exec'))
def compose(role,f):
    family='mag10' if role.endswith('mag10') else 'base';data=D['clips'][role]
    clip=next((c for c in D['profiles'][family]['clips'] if c['base']==data['path']),None)
    tracks={t['bone']:t for t in clip['tracks']} if clip else {}
    comp={}
    lo=max(0,min(int(f),data['keys']-1));hi=min(lo+1,data['keys']-1);w=f-lo
    for j,n in enumerate(names):
        a=data['poses'][str(lo)][j];b=data['poses'][str(hi)][j]
        v=[x+(y-x)*w for x,y in zip(a,b)];v[3:7]=qlerp(a[3:7],b[3:7],w)
        p=Vector(v[:3]);q=Quaternion((v[6],*v[3:6]));s=Vector(v[7:10])
        if n in tracks:
            d=sample(tracks[n],f/data['fps'],10,'values');p+=Vector(d[:3]);q=Quaternion((d[6],*d[3:6]))@q;s+=Vector(d[7:10])
        local=Matrix.LocRotScale(p,q,s);comp[n]=comp[parents[n]]@local if parents[n] else local
    return comp
if __name__=='__main__':
    report={'roots':[n for n in names if not parents[n]],'parents':{n:parents[n] for n in ('WPN_root','clavicle_l','clavicle_r')},'motion':{}}
    for role in D['clips']:
        if role=='idle':continue
        rows=[]
        for f in range(D['clips'][role]['keys']):
            row=compose(role,f);p=C@(K@row['WPN_root']@K).translation
            if f%5==0 or f==D['clips'][role]['keys']-1:rows.append([f,*p])
        report['motion'][role]=rows
    (O/'source_motion.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report),flush=True)
