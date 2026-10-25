import numpy as np
from scipy.ndimage import distance_transform_edt,gaussian_filter,map_coordinates
def contact_field(v,mask,field):
    z=field['polar_z'];radii=field['radius'];centers=field['centers'];bins=radii.shape[1]
    def polar(q):
        c=np.column_stack([np.interp(q[:,2],z,centers[:,axis]) for axis in [0,1]])
        d=q[:,:2]-c;radius=np.linalg.norm(d,axis=1);directions=d/np.maximum(radius[:,None],.001)
        angle=np.mod(np.arctan2(d[:,1],d[:,0]),2*np.pi)*bins/(2*np.pi)
        return radius,directions,angle
    radius,directions,angles=polar(v)
    target=map_coordinates(np.c_[radii,radii[:,0]],np.vstack([(v[:,2]-z[0])/(z[1]-z[0]),angles]),order=1,mode='nearest')
    valid=(mask<.15)&np.isfinite(target)&(v[:,2]>=z[0])&(v[:,2]<=z[-1])
    z0=np.floor(v[:,2].min())-2;count=int(np.ceil(v[:,2].max())-z0)+3
    grid=np.full((count,bins),-np.inf);zi=np.rint(v[:,2]-z0).astype(int);ai=np.rint(angles).astype(int)%bins
    wanted=np.clip(target+.45-radius,-6.,6.)
    np.maximum.at(grid,(zi[valid],ai[valid]),wanted[valid])
    present=np.isfinite(grid)
    if not present.any():raise RuntimeError('No fixed harness contact stations')
    tiled=np.tile(grid,(1,3));missing=~np.isfinite(tiled)
    nearest=distance_transform_edt(missing,return_distances=False,return_indices=True)
    filled=tiled[tuple(nearest)][:,bins:bins*2]
    smooth=gaussian_filter(filled,(1.4,1.2),mode=('nearest','wrap'))
    # Keep inner faces outside the requested contact surface; the same smooth
    # displacement field moves padding, edges and buckles together.
    smooth=np.maximum(smooth,filled-.12)
    field_grid=np.c_[smooth[:,-2:],smooth,smooth[:,:2]]
    def deform(q):
        _,direction,angle=polar(q)
        amount=map_coordinates(field_grid,np.vstack([q[:,2]-z0,angle+2]),order=1,mode='nearest')
        return np.column_stack([direction*amount[:,None],np.zeros(len(q))])
    return deform
