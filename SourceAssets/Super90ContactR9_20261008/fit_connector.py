from pathlib import Path
O=Path(__file__).parent
source=O/'fit_handle_compact.py'
exec(compile(source.read_text(encoding='utf-8-sig').split('bounds=np.r_')[0],str(source),'exec'))
out=json.loads((O/'hand_fit.json').read_text(encoding='utf-8-sig'));h=np.array(out['loader_hand_in_handle']);loc={n:np.array(v) for n,v in out['loader_finger_local'].items()}
poses=matrices(h,loc);points=skin(poses)
remap=np.full(len(vs),-1,dtype=int);remap[ids]=np.arange(len(ids));sf=fs[np.all(remap[fs]>=0,axis=1)]
handmesh=trimesh.Trimesh(vertices=points,faces=remap[sf],process=False)
candidates=[];queries=[]
for x in np.linspace(-.008,.008,5):
 for z in np.linspace(-.037,.037,39):
    candidates.append((x,z));queries.extend([(x,y,z) for y in np.linspace(.010,.042,24)])
nearest,distance,_=trimesh.proximity.closest_point(handmesh,np.asarray(queries))
clear=distance.reshape(-1,24).min(axis=1)
rank=np.argsort(-clear)
for i in rank[:10]:print('CONNECTOR',candidates[i],'clearance_mm',clear[i]*1000,flush=True)
best=int(rank[0]);(O/'Diagnostics/connector_fit.json').write_text(json.dumps({'xy':list(candidates[best]),'clearance_mm':float(clear[best]*1000)}))
for n in selected:
    ii=np.flatnonzero(dominant==ix[n]);dd=sdf(points[ii]);print('HAND_GAP',n,round(float(np.min(dd))*1000,2),round(float(np.percentile(dd,5))*1000,2),flush=True)
