from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
trees=[]
for f in (87,100,114):
    p,handle,_=s['pose'](f,7,False);iv=handle.inverted();v=[iv@x for x in deform(p)]
    trees.append(BVHTree.FromPolygons(v,skin['left'],all_triangles=True))
out=[]
for z in (.032,.038,.042):
 for x in (-.025,-.012,.012,.025,.035):
  for y in (-.015,0.,.015):
    path=[Vector((.010,0,z)),Vector((x,y,.063)),Vector((0,.016,.08))]
    points=[a.lerp(b,float(t)) for a,b in zip(path,path[1:]) for t in np.linspace(0,1,36)]
    distance=min(tree.find_nearest(p)[3] for tree in trees for p in points)
    out.append({'points':[list(p) for p in path],'clearance_mm':distance*1000})
out.sort(key=lambda x:-x['clearance_mm']);(O/'Diagnostics/actual_connector.json').write_text(json.dumps(out[:15],indent=2));print('CONNECTOR_BEST',out[:3],flush=True)
