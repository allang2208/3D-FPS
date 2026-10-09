from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
parts=json.loads((O/'Diagnostics/foregrip_geometry.json').read_text());out={'samples':0,'failures':[]}
for part,geometry in parts.items():
 family='vertical' if part=='tactical_vertical' else part;gf=geometry['faces'];gv=[Vector(v) for v in geometry['vertices']]
 for empty in (False,True):
  for f in list(range(0,34))+list(range(s['last_frame'](7)+(45 if empty else 8),s['duration'](7,empty)+1)):
   p=s['pose'](f,7,empty,family)[0];v=deform(p);turn=p['WPN_root']@s['rest']['WPN_root'].inverted();vs=[turn@x for x in gv];tree=BVHTree.FromPolygons(vs,gf,all_triangles=True);st=BVHTree.FromPolygons(v,skin['left'],all_triangles=True)
   hit={a for a,b in st.overlap(tree) if cuts([v[i] for i in skin['left'][a]],[vs[i] for i in gf[b]])};out['samples']+=1
   if hit:out['failures'].append({'part':part,'empty':empty,'frame':f,'triangles':len(hit),'bones':list(set(skin_names['left'][i] for i in hit))})
 print('FOREGRIP_CONTACT',part,'bad',sum(r['part']==part for r in out['failures']),flush=True)
(O/'Diagnostics/foregrip_contact.json').write_text(json.dumps(out,indent=2))
