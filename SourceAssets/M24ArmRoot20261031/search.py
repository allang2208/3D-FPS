from pathlib import Path
exec(compile((Path(__file__).parent/'solve.py').read_text().split("\nif __name__=='__main__':")[0],'solve','exec'))
from collections import Counter
_,weld=np.unique(np.round(P,6),axis=0,return_inverse=True);tw=weld[F];nv=int(weld.max()+1)
counts=Counter(tuple(sorted((int(a),int(b)))) for f in tw for a,b in zip(f,np.roll(f,-1)));opens={v for e,n in counts.items() if n==1 for v in e}
root=left&(np.linalg.norm(P-np.array(rest['upperarm_l'].translation),axis=1)<.13)&np.isin(weld,list(opens));region=left[F].all(1)&(np.linalg.norm(P[F].mean(1)-np.array(rest['lowerarm_l'].translation),axis=1)<.12)
tree=ast.parse((O/'review.py').read_text());exec(compile(ast.unparse(next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='folded')),'folded','exec'))
def candidate(row,degrees,mix):
 out={n:m.copy() for n,m in row.items()};S,E,H=[row[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
 normal=(E-S).cross(H-E).normalized();other=(S-E).normalized().cross(normal);a=normal*math.cos(math.radians(mix))+other*math.sin(math.radians(mix));turn=Quaternion(a,math.radians(degrees))
 moved=Matrix.LocRotScale(E+turn@(S-E),turn@row['upperarm_l'].to_quaternion(),row['upperarm_l'].to_scale())
 for n in names:
  if (under(n,'upperarm_l') and not under(n,'lowerarm_l')) or n=='clavicle_l':out[n]=moved@row['upperarm_l'].inverted()@row[n]
 return out
rows=[compose(entry('skeleton_base',role),entry('skeleton_base',role)['duration']*t)[0] for role,t in [('idle',0),('sprint_enter',.3),('sprint_enter',.65),('sprint_loop',0),('sprint_loop',.5)]]
basefold=[folded(skin(row)) for row in rows];results=[]
for mix in (-75,-60,-45,-30,-15,0,15,30,45,60,75):
 for degrees in (6,8,10,12):
  clearance=999;folds=0
  for row,prior in zip(rows,basefold):
   X=skin(candidate(row,degrees,mix));cp=np.c_[X,np.ones(len(X))]@C.T;mask=root&(cp[:,0]>1);clearance=min(clearance,float((-cp[mask,2]-cp[mask,0]*.7673).min()));folds=max(folds,int((folded(X)&~prior).sum()))
  results.append({'mix':mix,'degrees':degrees,'clearance':clearance,'folds':folds})
(O/'search.json').write_text(json.dumps(results,indent=2));print('ROOT_POLE_SEARCH',json.dumps(sorted(results,key=lambda x:(x['clearance']<.7,x['folds'],x['degrees']))[:14]),flush=True)
