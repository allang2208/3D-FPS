from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
parts=json.loads((O/'Diagnostics/foregrip_geometry.json').read_text())
for fn in ('grip_hand_fits.json','grip_hand_fits3.json'):
 fits=json.loads((O/fn).read_text())
 for family,fit in fits.items():
  p=s['copy'](s['idles'][family]);s['arm'](p,s['copy'](p),Matrix(fit['hand']),'l')
  for n in s['finger_names']['l']:p[n]=p[s['parents'][n]]@Matrix(fit['local'][n])
  vs=deform(p);st=BVHTree.FromPolygons(vs,skin['left'],all_triangles=True);g=parts[family];turn=p['WPN_root']@s['rest']['WPN_root'].inverted();vv=[turn@Vector(v) for v in g['vertices']];tree=BVHTree.FromPolygons(vv,g['faces'],all_triangles=True)
  hit={a for a,b in st.overlap(tree) if cuts([vs[i] for i in skin['left'][a]],[vv[i] for i in g['faces'][b]])}
  print('FITTED_EXACT',fn,family,len(hit),collision(p,False,sides=('left',)),flush=True)
