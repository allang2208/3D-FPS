import json,gzip,ast,bisect,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
O=Path(__file__).resolve().parent;D=json.load(gzip.open(O/'before.json.gz','rt'));names=D['names'];parents=D['parents'];indices={n:i for i,n in enumerate(names)}
K=Matrix.Diagonal((1,-1,1,1));rest={n:Matrix(m) for n,m in D['rest'].items()};local_rest={n:rest[parents[n]].inverted()@m if parents[n] else m for n,m in rest.items()}
tree=ast.parse((O.parent/'M24ReloadRefine20261028/install.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('qlerp','sample'):exec(compile(ast.unparse(n),n.name,'exec'))
tree=ast.parse((O.parent/'M24ReceiverGripRebuild20261031/author_grasp.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('raw','transform','compose','frame','under','smooth'):exec(compile(ast.unparse(n),n.name,'exec'))
def entry(family,role):return next(c for c in D['profiles'][family]['clips'] if c['base'].split('.')[-1]=='A_M24_'+role)
if __name__=='__main__':
 out={};anchor=compose(entry('base','idle'),0.)[0]['WPN_root']
 for role in ('fire','equip','reload_empty'):
  e=entry('base',role);rows=[]
  for f in range(round(e['duration']*30)+1):
   row,local=compose(e,f/30);g=anchor.inverted()@row['WPN_root'];bolt=row['WPN_root'].inverted()@row['WPN_BoltHandle']
   rows.append({'frame':f,'root_cm':[round(x*100,4) for x in g.translation],'root_deg':[round(math.degrees(x),4) for x in g.to_euler()],'bolt_cm':[round(x*100,4) for x in bolt.translation],'bolt_deg':[round(math.degrees(x),4) for x in bolt.to_euler()]})
  out[role]=rows
  print(role,json.dumps([r for r in rows if r['frame']%5==0]),flush=True)
 (O/'motion_sources.json').write_text(json.dumps(out,indent=2))
