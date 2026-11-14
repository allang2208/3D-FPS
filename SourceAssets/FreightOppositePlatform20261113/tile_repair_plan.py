"""Select localized ceramic islands from the exported UE source geometry, keeping mortar and surrounding unbroken fields intact."""
from pathlib import Path
import numpy as np,json,gzip
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
R=Path(__file__).resolve().parent
g=json.load(gzip.open(R/'ceramic.json.gz'));v=np.asarray(g['v'])+g['origin'];f=np.asarray(g['t']);t=v[f];slot=np.asarray(g['slot'])
# In the authored target corner the offending shards are front-facing triangles of the glaze atlas.
# Inspect the front surfaces grouped by their actual tile cells rather than matching one global slot.
cent=t.mean(1);level=np.abs(t[:,:,2].max(1)-t[:,:,2].min(1))
pieces=[];info=[]
for axis,world_plane,lo,hi in [(0,6176.4,-3033.,-1562.),(1,-3033.6,6178.,7820.)]:
    h=1-axis
    mask=(slot==1)&(np.ptp(t[:,:,axis],axis=1)<.045)&(np.abs(cent[:,axis]-world_plane)<.5)&(cent[:,h]>=lo)&(cent[:,h]<hi)
    ids=np.flatnonzero(mask)
    pts=t[ids][:,:,[h,2]];raw=np.round(pts.reshape(-1,2),2);unique,inv=np.unique(raw,axis=0,return_inverse=True)
    inv=inv.reshape(-1,3);i=np.concatenate([inv[:,0],inv[:,1],inv[:,2]]);j=np.concatenate([inv[:,1],inv[:,2],inv[:,0]])
    _,grp=connected_components(coo_matrix((np.ones(len(i)),(i,j)),shape=(len(unique),len(unique))),directed=False)
    lab=grp[inv[:,0]]
    for k in np.unique(lab):
        take=ids[lab==k];p=t[take][:,:,[h,2]]
        mins=p.min((0,1));maxs=p.max((0,1));area=np.sum(abs((p[:,1,0]-p[:,0,0])*(p[:,2,1]-p[:,0,1])-(p[:,2,0]-p[:,0,0])*(p[:,1,1]-p[:,0,1])))/2
        info.append([axis,len(take),round(float(area),1),*np.round(mins,2).tolist(),*np.round(maxs,2).tolist()])
        if area<50 or (maxs[0]-mins[0])<2:continue
        # Leave all original ceramic geometry intact; these cells will be repaired with an intact ceramic face.
        pieces.append(dict(axis=axis,ids=take.tolist(),bounds=[*mins,*maxs],area=area))
(R/'tile-groups.json').write_text(json.dumps(info),'utf8')
for axis in [0,1]:
    sig=[p for p in pieces if p['axis']==axis];print(axis,len(sig),'areas',np.percentile([p['area'] for p in sig],[0,10,25,50,90,100]))
    if axis==0:
        for spot in json.loads((R/'skirts-spots.json').read_text()):
            _,h,z=spot['world'];match=[p for p in sig if p['bounds'][0]-.5<h<p['bounds'][2]+.5 and p['bounds'][1]-.5<z<p['bounds'][3]+.5]
            print('bright',h,z,[(round(p['area']),len(p['ids']),np.round(p['bounds'],1).tolist()) for p in match])
