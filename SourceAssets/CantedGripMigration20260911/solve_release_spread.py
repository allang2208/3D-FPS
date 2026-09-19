from pathlib import Path
O=Path(__file__).parent
exec((O/'solve_release_path.py').read_text().split('p0,v0=')[0])
oldfit=json.loads((O.parent/'CantedForegrip20260911/ThumbClose/fit_final.json').read_text());entries=json.loads((O.parent/'CantedForegrip20260911/ThumbClose/release_profile.json').read_text());vector=np.array(oldfit['release_vector']);best=None
def evaluate(a,b):
 global best
 hits=sh=0
 for u in [k/36 for k in range(1,37)]:
  j=min(len(entries)-2,int(u*(len(entries)-1)));l,h=entries[j:j+2];t=(u-l['u'])/(h['u']-l['u']);bas=basis.copy()
  for n,q in qs.items():
   v=q@Matrix(oldfit['basis'][n]).to_quaternion().inverted()@Quaternion(l['basis'][n]).slerp(Quaternion(h['basis'][n]),t)
   if n=='pinky_metacarpal_l':v=v@Quaternion((0,1,0),math.radians(a)*smooth(min(1,u*3)))
   if n=='ring_metacarpal_l':v=v@Quaternion((0,1,0),math.radians(b)*smooth(min(1,u*3)))
   bas[index[n],:3,:3]=np.array(v.to_matrix())
  p=base.copy();p[index['hand_l'],:3,3]+=G[:3,:3]@vector*smooth((u-.25)/.75)
  for i in left:p[i]=p[par[i]]@lr[i]@bas[i]
  v=np.einsum('bij,bnj->ni',p[active],pre)[:,:3];vv=v.tolist();hits+=len(BVHTree.FromPolygons(vv,faces,all_triangles=True).overlap(tree));trees={d:BVHTree.FromPolygons(vv,self_fs[d],all_triangles=True) for d in digits};sh+=sum(len(trees[c].overlap(trees[d])) for c,d in itertools.combinations(digits,2))
 score=(hits+sh)*1e5+a*a+b*b
 if best is None or score<best[0]:best=(score,a,b,hits,sh);print('RELEASE_SPREAD',best,flush=True)
for a,b in itertools.product([-12,-8,-4,0,4,8,12],[-4,0,4]):evaluate(a,b)
assert best[3]==0 and best[4]==0,best
fit['release_vector']=vector.tolist();fit['retreat_start']=.25;fit['release_spread_deg']=[best[1],best[2]];(O/'canted_refit.json').write_text(json.dumps(fit,indent=2))
for e in entries:
 for n,q in e['basis'].items():
  v=qs[n]@Matrix(oldfit['basis'][n]).to_quaternion().inverted()@Quaternion(q)
  if n=='pinky_metacarpal_l':v=v@Quaternion((0,1,0),math.radians(best[1])*smooth(min(1,e['u']*3)))
  if n=='ring_metacarpal_l':v=v@Quaternion((0,1,0),math.radians(best[2])*smooth(min(1,e['u']*3)))
  e['basis'][n]=list(v)
(O/'release_final.json').write_text(json.dumps(entries,indent=2));(O/'release_solution.json').write_text(json.dumps({'spread':best[1:3],'grip_pairs':best[3],'self_pairs':best[4],'samples':36},indent=2))
