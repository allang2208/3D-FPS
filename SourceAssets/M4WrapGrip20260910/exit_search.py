exec(open(__file__.replace('exit_search.py','whole_grip_search.py'),encoding='utf-8-sig').read().split('best=(1e20,None)')[0])
report=[]
for axis in [(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(1,1,0),(1,0,0)]:
 rows=[]
 for k in range(1,31):
  shift=Vector(axis)*k*.003;vv=[v+shift for v in vs];t=BVHTree.FromPolygons(vv,fs);rows.append(sum(len(t.overlap(x)) for x in trees))
 report.append(dict(axis=axis,max_pairs=max(rows),rows=rows));print(report[-1],flush=True)
(O/'exit_search.json').write_text(json.dumps(report,indent=2))
