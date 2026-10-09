from pathlib import Path
O=Path(__file__).parent
code=(O/'fit_connector.py').read_text().split('candidates=[]')[0]
exec(compile(code,str(O/'fit_connector.py'),'exec'))
candidates=[];queries=[]
for angle in np.linspace(-np.pi,np.pi,49)[:-1]:
 for z in np.linspace(-.038,.038,39):
    candidates.append((angle,z));queries.extend([(np.cos(angle)*r,np.sin(angle)*r,z) for r in np.linspace(.014,.065,28)])
_,distance,_=trimesh.proximity.closest_point(handmesh,np.asarray(queries));clear=distance.reshape(-1,28).min(axis=1);rank=np.argsort(-clear)
for i in rank[:20]:print('EXIT',np.rad2deg(candidates[i][0]),candidates[i][1],clear[i]*1000,flush=True)
(O/'Diagnostics/grip_exit.json').write_text(json.dumps([{'angle':float(np.rad2deg(candidates[i][0])),'z':float(candidates[i][1]),'clearance_mm':float(clear[i]*1000)} for i in rank[:20]],indent=2))
