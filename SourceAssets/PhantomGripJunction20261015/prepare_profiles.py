import numpy as np,json
from pathlib import Path
from scipy.spatial import ConvexHull
from scipy.ndimage import gaussian_filter1d
O=Path(__file__).parent;W=O/'Working';HK=np.array(json.loads((O.parent/'HK416Reworked20260930/authoring.json').read_text())['root_matrix']);HKI=np.linalg.inv(HK);R={};N=512
def segments(p,t,z):
 q=p[t];segs=[]
 for tri in q[(q[:,:,2].min(1)<z)&(q[:,:,2].max(1)>z)]:
  hits=[]
  for i,j in [(0,1),(1,2),(2,0)]:
   a,b=tri[i],tri[j]
   if (a[2]-z)*(b[2]-z)<0:hits.append(a+(b-a)*((z-a[2])/(b[2]-a[2])))
  if len(hits)==2:segs.append(np.array(hits)[:,:2])
 return np.array(segs)
def radii(edges,center,hull=False):
 if hull:
  pts=edges.reshape(-1,2);pts=pts[ConvexHull(pts).vertices];edges=np.stack((pts,np.roll(pts,-1,axis=0)),1)
 a=edges[:,0]-center;e=edges[:,1]-edges[:,0];out=[]
 for angle in np.linspace(0,2*np.pi,N,endpoint=False):
  d=np.array([np.cos(angle),np.sin(angle)]);den=d[0]*e[:,1]-d[1]*e[:,0];valid=abs(den)>1e-12;dist=np.divide(a[:,0]*e[:,1]-a[:,1]*e[:,0],den,out=np.zeros(len(den)),where=valid);u=np.divide(a[:,0]*d[1]-a[:,1]*d[0],den,out=np.zeros(len(den)),where=valid);mask=valid&(dist>0)&(u>=-1e-6)&(u<=1.000001)
  if not mask.any():raise RuntimeError('Missing surface radial sector')
  out.append(dist[mask].max())
 return np.array(out)
for key,slot,join,limit in [('HK416',0,0.,.006),('A762',1,-.010,-.005),('Super90',0,-.836,-.830)]:
 d=np.load(W/(key+'.npz'));p=d['grip_positions'];t=d['grip_triangles'];m=d['grip_mids']
 if key=='HK416':p=p@HKI[:3,:3].T+HKI[:3,3]
 b=segments(p,t[m==slot],join-.00005);a=segments(p,t[m!=slot],join+.00005);center=(b.reshape(-1,2).min(0)+b.reshape(-1,2).max(0))*.5;hull=key=='Super90'
 rb=radii(b,center,hull);rn=radii(a,center);rb2=radii(segments(p,t[m==slot],join-.0008),center,hull);rn2=radii(segments(p,t[m!=slot],join+.0008),center)
 body_slope=np.clip(gaussian_filter1d((rb-rb2)/.00075,10,mode='wrap'),-1.5,1.5);slope=np.clip(gaussian_filter1d((rb-rb2)/.00075-(rn2-rn)/.00075,10,mode='wrap'),-.5,.5);delta=gaussian_filter1d(rb-rn,6,mode='wrap');smooth_rb=gaussian_filter1d(rb,6,mode='wrap');dtheta=(np.roll(smooth_rb,-1)-np.roll(smooth_rb,1))/(2*2*np.pi/N)
 R[key]={'body_slot':slot,'join':join,'limit':limit,'center':center.tolist(),'delta':delta.tolist(),'slope_delta':slope.tolist(),'body_radius':smooth_rb.tolist(),'body_radius_derivative':dtheta.tolist(),'body_z_slope':body_slope.tolist(),'native_radius':rn.tolist(),'max_boundary_correction_mm':float(max(abs(delta))*1000),'radial_smoothing_error_mm':float(max(abs(smooth_rb-rb))*1000),'lower_profile':'outer support hull at existing roof' if hull else 'measured outer body section'}
 print('PROFILE',key,'max_correction_mm',R[key]['max_boundary_correction_mm'],flush=True)
(O/'profiles.json').write_text(json.dumps(R,indent=2))
