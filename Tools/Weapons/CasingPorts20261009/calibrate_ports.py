"""Measured window centres from the current mesh views, in root-local cm."""
import json
import numpy as np
from pathlib import Path
from scipy.spatial.transform import Rotation
O=Path(__file__).parent
G=json.loads((O/'geometry_report.json').read_text())
D=json.loads((O/'ports_before.json').read_text())['weapons']
# Image coordinates refer to the 1100x700 diagnostic orthographic captures.
# Exterior lateral planes were read from current receiver/slide geometry.
PICKS={
 'm4': (505,367,2.2,1),
 'qbz191': (470,360,2.0,1),
 'a762': (468,385,2.0,1),
 'akm': (450,379,1.9,1),
 'ash12': (380,354,2.0,1),
 'm16a2': (541,327,2.0,1),
 'svd': (450,423,2.0,1),
 'pkm_lowpoly': (650,407,-3.0,-1),
 'lmg201': (650,423,-3.0,-1),
 'm1911': (440,351,1.3,1),
 'g18': (491,340,1.45,1),
 'pit_viper2011': (553,326,1.25,1),
 'super90': (405,331,2.25,1),
}
report={}
for key,row in G.items():
 if key in ('dw715','rsh12'):continue
 basis=np.array(row['basis_rows']);rest=np.array(row['port_semantic_cm'])
 bones=D[key]['clips']['fire']['samples'][0]['bones'];root_pose=bones['WPN_root']
 old_root=Rotation.from_quat(root_pose['q']).inv().apply(np.array(bones['WPN_SOCKET_Eject']['p'])-root_pose['p'])/root_pose['s']*100
 old=basis@old_root
 if key in ('hk416','a762','akm','pkm_lowpoly'):
  point=old.copy();side=1;pick=None
  if key=='pkm_lowpoly':side=-1;point[1]=-3.25
 else:
  px,py,y,side=PICKS[key];pick=[px,py]
  width=27 if key in ('m1911','g18','pit_viper2011') else 62
  target=rest.copy();target[1]=0
  if key=='ash12':width=56;target=np.array([-26.,0,7.])
  scale=1100/width
  x=target[0]+side*(550-px)/scale
  z=target[2]+((350-py)/scale+side*y*8/np.sqrt(10064))/(100/np.sqrt(10064))
  point=np.array([x,y,z])
 root=np.linalg.solve(basis,point)
 # Ray/triangle intersections on the centre line expose wrong-side placement.
 geo=np.load(O/'Geometry'/f'{key}.npz',allow_pickle=True)
 v=geo['vertices']@basis.T;tri=[]
 for f in geo['faces']:
  for j in range(1,len(f)-1):tri.append(v[[f[0],f[j],f[j+1]]])
 tri=np.array(tri);a=tri[:,0];b=tri[:,1]-a;c=tri[:,2]-a
 det=b[:,0]*c[:,2]-b[:,2]*c[:,0];good=np.abs(det)>1.e-8
 a,b,c,det=a[good],b[good],c[good],det[good]
 d=point[[0,2]]-a[:,[0,2]]
 s=(d[:,0]*c[:,2]-d[:,1]*c[:,0])/det;t=(b[:,0]*d[:,1]-b[:,2]*d[:,0])/det
 inside=(s>=0)&(t>=0)&(s+t<=1);hits=(a[:,1]+s*b[:,1]+t*c[:,1])[inside]
 rowout={'root_cm':root.round(6).tolist(),'semantic_cm':point.round(6).tolist(),
  'old_semantic_cm':old.tolist(),'reference_marker_semantic_cm':rest.tolist(),
  'outward_side':side,'view_pixel':pick,
  'anchor':'WPN_Slide' if key in ('m1911','g18','pit_viper2011') else 'WPN_root',
  'ray_surfaces_y_cm':sorted(set(np.round(hits,3).tolist()))}
 report[key]=rowout
 print(key, 'centre',np.round(point,3),'surface Ys',np.round(hits,3))
(O/'calibration.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
