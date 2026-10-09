from pathlib import Path
O=Path(__file__).parent
source=O/'fit_handle_surface.py'
exec(compile(source.read_text().split('bounds=np.r_')[0],str(source),'exec'))
out=json.loads((O/'hand_fit.json').read_text());h=np.array(out['loader_hand_in_handle']);loc={n:np.array(v) for n,v in out['loader_finger_local'].items()}
points=skin(matrices(h,loc));d=sdf(points)
for n in selected:
    ii=np.flatnonzero((dominant==ix[n])&(d<0))
    if len(ii):print(n,len(ii),round(min(d[ii])*1000,3),'bounds_mm',np.round(np.min(points[ii],axis=0)*1000,1),np.round(np.max(points[ii],axis=0)*1000,1))
print('TOTAL',len(ids),'point_bounds',points.min(axis=0),points.max(axis=0))
