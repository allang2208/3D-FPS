"""Author a rigid mount from the bag's actual rear surface and full torso profile."""
import numpy as np
from scipy.interpolate import RegularGridInterpolator
from scipy.spatial.transform import Rotation


def calibrate(author, body):
    equations, _ = author.envelope(body, None)
    xs=np.arange(-26.,26.01,.5);zs=np.arange(82.,153.01,.5)
    xx,zz=np.meshgrid(xs,zs,indexing='ij')
    origins=np.column_stack([xx.ravel(),np.zeros(xx.size),zz.ravel()])
    rear=np.full(len(origins),np.inf)
    for cell,(low,high) in zip(equations['cells'],equations['bands']):
        ids=np.flatnonzero((origins[:,2]>=low-.36)&(origins[:,2]<=high+.36))
        for start in range(0,len(ids),1024):
            batch=ids[start:start+1024]
            distance=author.contact_offset(origins[batch],np.tile([0.,-1.,0.],(len(batch),1)),{'cells':[cell]},.35)
            rear[batch]=np.minimum(rear[batch],-distance)
    rear[~np.isfinite(rear)]=np.nan
    surface=RegularGridInterpolator((xs,zs),rear.reshape(len(xs),len(zs)),bounds_error=False,fill_value=np.nan)
    source=np.load(author.R/'Authored/worn_body.npz')['positions'].astype(float)
    candidates=[]
    for angle in np.arange(-18.,12.01,.5):
        rotation=Rotation.from_euler('x',angle,degrees=True).as_matrix().T
        points=source@rotation+author.BAG_CENTRE
        limit=surface(points[:,[0,2]])
        delta=points[:,1]-limit
        valid=np.isfinite(delta)
        shift=float(np.max(delta[valid]))
        # Equal-area rear pad stations avoid dense folded belt geometry
        # dominating the mount. Full geometry still sets nonpenetration above.
        pad=valid&(abs(points[:,0])<10)&(points[:,2]>106+author.SHOULDER_SHIFT)&(points[:,2]<141+author.SHOULDER_SHIFT)
        ids=np.flatnonzero(pad)
        bins=np.floor(points[ids][:,[0,2]]/2).astype(int)
        _,group=np.unique(bins,axis=0,return_inverse=True)
        nearest=np.full(group.max()+1,-np.inf)
        np.maximum.at(nearest,group,delta[ids])
        gaps=shift-nearest
        score=float(np.mean(gaps)+.35*np.quantile(gaps,.90))
        candidates.append({'angle_degrees':float(angle),'backward_shift_cm':shift,'mean_pad_gap_above_margin_cm':float(np.mean(gaps)),
                           'p90_pad_gap_above_margin_cm':float(np.quantile(gaps,.90)),'score':score})
    best=min(candidates,key=lambda row:row['score'])
    author.write(author.R/('mount_calibration_'+author.RIG+'.json'),{'method':'full posterior torso and waist surface; actual worn rear geometry; equal-area pad fit',
                 'local_tilt_degrees':best['angle_degrees'],'shoulder_shift_cm':author.SHOULDER_SHIFT,'clearance_cm':.35,'selected':best,'candidates':candidates})
    return best['angle_degrees']
