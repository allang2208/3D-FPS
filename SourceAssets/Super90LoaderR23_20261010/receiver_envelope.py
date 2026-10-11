"""Native receiver outer envelope for the requested hand/body overlap check."""
import json
from pathlib import Path
import numpy as np
from scipy.interpolate import RegularGridInterpolator
O=Path(__file__).parent
path=O/'receiver_envelope.npz'
if not path.exists():
    body=json.loads((O/'geometry.json').read_text())['meshes']['Super90_body'];bv=np.array(body['positions'])
    ys=np.arange(-.28,.101,.001);zs=np.arange(-.97,-.689,.001)
    right=np.full((len(ys),len(zs)),-1.);left=np.full_like(right,1.)
    for face in body['faces']:
        for k in range(1,len(face)-1):
            tri=bv[[face[0],face[k],face[k+1]]];a,b,c=tri
            den=(b[2]-c[2])*(a[1]-c[1])+(c[1]-b[1])*(a[2]-c[2])
            if abs(den)<1e-12:continue
            iy=np.flatnonzero((ys>=tri[:,1].min())&(ys<=tri[:,1].max()));iz=np.flatnonzero((zs>=tri[:,2].min())&(zs<=tri[:,2].max()))
            if not len(iy) or not len(iz):continue
            y,z=np.meshgrid(ys[iy],zs[iz],indexing='ij')
            u=((b[2]-c[2])*(y-c[1])+(c[1]-b[1])*(z-c[2]))/den
            vv=((c[2]-a[2])*(y-c[1])+(a[1]-c[1])*(z-c[2]))/den;ww=1-u-vv
            mask=(u>=0)&(vv>=0)&(ww>=0);xx=u*a[0]+vv*b[0]+ww*c[0]
            right[np.ix_(iy,iz)]=np.maximum(right[np.ix_(iy,iz)],np.where(mask,xx,-1.))
            left[np.ix_(iy,iz)]=np.minimum(left[np.ix_(iy,iz)],np.where(mask,xx,1.))
    np.savez_compressed(path,ys=ys,zs=zs,right=right,left=left)
grid=np.load(path)
right=RegularGridInterpolator((grid['ys'],grid['zs']),grid['right'],bounds_error=False,fill_value=-1.)
left=RegularGridInterpolator((grid['ys'],grid['zs']),grid['left'],bounds_error=False,fill_value=1.)
def penetration(points):
    return np.maximum(0,np.minimum(right(points[:,1:3])-points[:,0],points[:,0]-left(points[:,1:3])))
