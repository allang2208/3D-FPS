from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'fit_actual_connector.py').read_text().split('out=[]')[0],str(O/'fit_actual_connector.py'),'exec'))
out=[]
for sign in (-1,1):
 for z in (.055,.065,.075,.085,.095):
  for y in (.045,.055,.065):
   for x in (-.008,0,.008):
    path=[Vector((x,0,sign*.030)),Vector((x,0,sign*z)),Vector((x,y,sign*z)),Vector((0,.042,0))]
    points=[a.lerp(b,float(t)) for a,b in zip(path,path[1:]) for t in np.linspace(0,1,64)]
    distance=min(tree.find_nearest(p)[3] for tree in trees for p in points)
    length=sum((b-a).length for a,b in zip(path,path[1:]))
    out.append({'points':[list(p) for p in path],'clearance_mm':distance*1000,'length_m':length,'score':min(distance,.006)-length*.005})
out.sort(key=lambda x:-x['score']);(O/'Diagnostics/end_connector.json').write_text(json.dumps(out[:15],indent=2));print('CONNECTOR_END_BEST',out[:3],flush=True)
