"""Fit the existing rack overtravel to the receiver's rear roof geometry.

Authoring measurement only; no render, editor/game launch or acceptance test.
The handle and open ejection window are deliberately excluded from the roof fit.
"""
import json
from pathlib import Path
import numpy as np
O=Path(__file__).parent
G=json.loads((O.parent/'Super90LoaderR23_20261010/geometry.json').read_text())
body=G['meshes']['Super90_body']; v=np.array(body['positions'])
tri=np.array([v[[f[0],f[i],f[i+1]]] for f in body['faces'] for i in range(1,len(f)-1)])
tri=tri[(tri[:,:,1].min(1)<-.13)&(tri[:,:,1].max(1)>-.22)&(tri[:,:,2].max(1)>-.77)]
bolt=np.array(G['meshes']['Super90_bolt']['positions'])
bolt=bolt[(bolt[:,1]<-.035)&(np.abs(bolt[:,0])<.014)]

def roof_gap(travel):
    points=bolt.copy();points[:,1]-=travel
    top=np.full(len(points),-np.inf)
    for a,b,c in tri:
        den=(b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(den)<1e-12:continue
        u=((b[1]-c[1])*(points[:,0]-c[0])+(c[0]-b[0])*(points[:,1]-c[1]))/den
        w=((c[1]-a[1])*(points[:,0]-c[0])+(a[0]-c[0])*(points[:,1]-c[1]))/den
        inside=(u>=-1e-6)&(w>=-1e-6)&(u+w<=1.000001)
        top=np.maximum(top,np.where(inside,u*a[2]+w*b[2]+(1-u-w)*c[2],-np.inf))
    found=np.isfinite(top)
    if not found.all():raise RuntimeError('Rear roof fit left receiver surface')
    return float(np.min(top-points[:,2]))

base=.1065;old_extra=.024;clearance=.001
lo=base;hi=base+old_extra
if roof_gap(lo)<clearance:raise RuntimeError('Existing open stop does not fit the receiver')
for _ in range(24):
    mid=(lo+hi)/2
    if roof_gap(mid)>=clearance:lo=mid
    else:hi=mid
# Round down to 0.1 mm; preserve a defined surface margin at the rearmost stop.
extra=np.floor((lo-base)*10000)/10000
report={'part':'Super90_bolt / WPN_bolt','open_travel_m':base,
        'old_extra_travel_m':old_extra,'new_extra_travel_m':float(extra),
        'roof_clearance_m':clearance,'rear_roof_triangles':len(tri),'rear_bolt_vertices':len(bolt),
        'old_rear_roof_gap_m':roof_gap(base+old_extra),'fitted_rear_roof_gap_m':roof_gap(base+extra),
        'scope':'Native rear bolt and receiver source geometry, not game validation'}
(O/'bolt_fit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
