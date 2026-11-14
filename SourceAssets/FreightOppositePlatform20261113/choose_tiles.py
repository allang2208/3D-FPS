"""Find regular grid coordinates and match each photographed remnant to a complete neighboring ceramic tile."""
from pathlib import Path
import numpy as np,json,gzip
R=Path(__file__).resolve().parent;rows=json.loads((R/'tile-groups.json').read_text())
g=json.load(gzip.open(R/'ceramic.json.gz'));v=np.asarray(g['v'])+g['origin'];f=np.asarray(g['t']);tris=v[f];slots=np.array(g['slot']);cent=tris.mean(1)
patches=[];donors={}
for axis in (0,1):
    h=1-axis;plane=6176.4 if axis==0 else -3033.6
    group=[q for q in rows if q[0]==axis];full=[q for q in group if q[2]>455 and q[5]-q[3]>29]
    us=np.median([q[3]-31*round((q[3]-full[0][3])/31) for q in full]);zbase=np.median([q[4]-15.8*round((q[4]-full[0][4])/15.8) for q in full])
    width=np.median([q[5]-q[3] for q in full]);height=np.median([q[6]-q[4] for q in full])
    # Read a few actual intact face mappings per orientation; the color atlas must match the surrounding glaze.
    donorrows=sorted(full,key=lambda q:abs((q[3]+q[5])/2-(-2300 if axis==0 else 6750)))[:4];dn=[]
    for q in donorrows:
        a,z,b,k=q[3:];found=np.flatnonzero((slots==1)&(np.ptp(tris[:,:,axis],axis=1)<.045)&(abs(cent[:,axis]-plane)<.5)&(cent[:,h]>a)&(cent[:,h]<b)&(cent[:,2]>z)&(cent[:,2]<k))
        tn=int(max(found,key=lambda i:abs(np.cross(tris[i,1]-tris[i,0],tris[i,2]-tris[i,0])[axis])))
        donors[str(tn)]=dict(axis=axis,bounds=[a,z,b,k],corners=tris[tn][:,[h,2]].tolist())
        dn.append(tn)
    seen=set()
    for q in group:
        if q[2]<20 or q[2]>=450:continue
        a,z,b,k=q[3:];u=round(((a+b)/2-width/2-us)/31);j=round(((z+k)/2-height/2-zbase)/15.8)
        if (u,j) in seen:continue
        seen.add((u,j));left=us+u*31;bottom=zbase+j*15.8
        if left<(-3035 if axis==0 else 6174) or left+width>(-1558 if axis==0 else 7820):continue
        patches.append(dict(axis=axis,plane=plane,rect=[left,bottom,left+width,bottom+height],donor=dn[(u*17+j*7)%len(dn)]))
(R/'tile-plan.json').write_text(json.dumps(dict(patches=patches,donors=donors),indent=1),'utf8')
print('Retile',len(patches),'existing cells')
