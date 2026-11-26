"""Continue the gate trail into the original White Cliffs working yard, in world metres."""
import json
import sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import distance_transform_edt, gaussian_filter1d, map_coordinates, maximum_filter
from scipy.spatial import cKDTree
from generate_slope_grass import grid_at
from generate_reference_hill import smooth
from trail_variation import bends,road_paint

CENTER=(-484.,290.)


def prepare(out,base):
    read=lambda name,dtype,shape: np.fromfile(base/name,dtype).reshape(shape)
    z=read('region.i16','<i2',(1025,1025)).astype('f8')*.01
    weights=read('paint.rg8','u1',(1025,1025,2)).astype('f8')/255.
    survey=np.fromfile(out/'quarry-ground.f32','<f4').reshape(241,241)*.01
    yy,xx=np.mgrid[-320:705,-624:401]
    cx,cy=CENTER
    u,v=yy-cy,cx-xx  # Local +Y points along the westbound haul road.
    original=lambda u,v:map_coordinates(survey,[v+120.,u+120.],order=1,mode='nearest')
    datum=float(z[int(cy+320),int(cx+72+624)]-original(np.array([0.]),np.array([-72.]))[0])
    block=np.maximum(abs(u)/74.,np.maximum(-v/76.,v/72.))
    mix=1.-smooth(1.,1.21,block)
    z+=mix*(datum+original(u,v)-z)
    # The switchback at the gate and the existing forest trail are retained. Branch where
    # the surveyed centreline already runs west and trace the foot of the hill.
    gate=np.loadtxt(base/'gate-road.csv',delimiter=',',skiprows=1)
    k=np.argmin(abs(gate[:,0]+87.))
    first=gate[k,:2]
    anchors=np.array([first,[-110,261.2],[-145,266.8],[-182,265.5],[-219,271.2],
                      [-252,273.5],[-282,286.7],[-309,298.3],[-340,300.],
                      [-377,293.6],[cx+81,cy],[cx+60,cy],[cx+29,cy]])
    sx=np.arange(first[0],anchors[-1,0]-.01,-.45)
    sx=np.r_[sx,anchors[-1,0]]
    sy=PchipInterpolator(-anchors[:,0],anchors[:,1])(-sx)
    run=first[0]-sx
    # Pin both tangents at the junction and the surveyed entrance. Unequal runs
    # alternate around the hill foot without becoming a repeated sine wave.
    envelope=smooth(3.,22.,run)*(1.-smooth(run[-1]-76.,run[-1]-53.,run))
    sy+=envelope*(bends(run,237855,44.,10.8)+bends(run,9437,19.,2.1))
    sy=np.maximum(sy,257.+2.*envelope)
    stations=np.r_[0.,np.cumsum(np.hypot(np.diff(sx),np.diff(sy)))]
    surface=grid_at(z,sx,sy)
    profile=gaussian_filter1d(surface,20.,mode='nearest')
    # A bidirectional grade envelope keeps a traversable cut/fill through the foothill.
    profile[0],profile[-1]=surface[0],surface[-1]
    max_grade=.135
    for i in range(1,len(sx)):
        step=max_grade*(stations[i]-stations[i-1])
        remaining=max_grade*(stations[-1]-stations[i])
        lower=max(profile[i-1]-step,surface[-1]-remaining)
        upper=min(profile[i-1]+step,surface[-1]+remaining)
        profile[i]=np.clip(profile[i],lower,upper)
    # A final smoothing pass keeps both ends pinned; the pit beyond the entry owns its own grade.
    filtered=gaussian_filter1d(profile,5.,mode='nearest')
    ramp=smooth(0.,8.,np.minimum(stations,stations[-1]-stations))
    profile+=(filtered-profile)*ramp
    editable=smooth(0.,8.,stations)
    d,idx=cKDTree(np.c_[sx,sy]).query(np.c_[xx.ravel(),yy.ravel()])
    d=d.reshape(xx.shape); idx=idx.reshape(xx.shape)
    delta=np.abs(profile[idx]-z)
    approach=1.-smooth(2.1,np.clip(5.8+1.5*delta,6.,19.),d)
    boundary=np.where(abs(xx)<=252,smooth(252.,258.,yy),1.)
    preserve_fork=1.-weights[...,0]*(1.-smooth(0.,20.,stations[idx]))
    z+=approach*editable[idx]*boundary*preserve_fork*(1.-smooth(-29.,-25.,v))*(profile[idx]-z)
    road=road_paint(np.c_[sx,sy],stations,idx,xx,yy,d,5231)
    verge=1.-smooth(5.3,13.3,d)
    # Continue the dirt paint down the original cut between the actual banks.
    banks=Path(__file__).resolve().parents[3]/'Source/FPSGAME/WorldGeneration/TemperateQuarryBanks.inl'
    sections=np.array([list(map(float,line.strip().strip('{},').split(','))) for line in banks.read_text().splitlines() if line.strip().startswith('{')])*.01
    lane=np.interp(v,sections[:,0],sections[:,5])
    yard_lane=(1.-smooth(1.9,3.6,np.abs(u-lane)))*smooth(-36.,-29.,v)*(1.-smooth(37.,51.,v))
    original_mask=banks.parents[3]/'SourceAssets/HillsQuarryCutYard/Approach/T_QuarryWorkGround.png'
    with Image.open(original_mask) as atlas:
        worked=np.asarray(atlas.getchannel('R'),dtype='f4')/255.
    workpaint=map_coordinates(worked,[(v+40.)/92.*worked.shape[0]-.5,(u+35.)/70.*worked.shape[1]-.5],
                              order=1,mode='constant',cval=0.)
    weights[...,0]=np.maximum.reduce((weights[...,0],road*boundary,yard_lane,workpaint))
    weights[...,1]=np.maximum(weights[...,1],verge*boundary)
    paint=np.rint(weights.clip(0,1)*255.).astype('u1')
    cm=np.rint(z*100.).astype('<i2')
    paint.tofile(out/'paint.rg8')
    cm.tofile(out/'region.i16')
    changed=(cm!=read('region.i16','<i2',cm.shape))|np.any(paint!=read('paint.rg8','u1',paint.shape),axis=2)
    changed=maximum_filter(changed,size=3)
    tiles=[f'SM_ForestGround_{i:02d}_{j:02d}' for j in range(8) for i in range(8)
           if changed[128*j:128*j+129,128*i:128*i+129].any()]
    # The actual bank stations bound the pit. Forest resumes outside the dressed rims.
    capped=np.clip(v,-34.,41.)
    west,east=[np.interp(capped,sections[:,0],sections[:,i]) for i in (1,2)]
    middle=(west+east)*.5
    work=((u-middle)/((east-west)*.5+11.))**2+((v-capped)/12.)**2<=1.
    props=np.genfromtxt(out/'quarry.csv',delimiter=',',names=True,dtype=None,encoding='utf8')
    props=props[(props['detail']==0)&(np.abs(props['x'])<=7300)&(props['y']>=-7400)&(props['y']<=7100)]
    for p in props:
        a,b=p['x']*.01,p['y']*.01
        radius=3.2
        work|=((u-a)**2+(v-b)**2<radius**2)
    fringe=1.-smooth(0.,5.+1.8*np.sin(.28*u-.17*v),distance_transform_edt(~work))
    np.rint(255.*fringe).astype('u1').tofile(out/'quarry-clear.u8')
    allowed=read('Grass/pond_allowed.u8','u1',(1025,1025)).astype(bool)
    allowed &= (maximum_filter(weights[...,0],size=7)<.25)&~work&(mix<.02)&(np.hypot(*np.gradient(z))<.45)
    allowed.astype('u1').tofile(out/'Grass/pond_allowed.u8')
    np.savetxt(out/'quarry-road.csv',np.c_[sx,sy,grid_at(z,sx,sy)],delimiter=',',header='x_m,y_m,z_m',comments='',fmt='%.3f')
    full=np.vstack([gate[k:,:2][::-1],np.c_[sx,sy][1:]])
    data=dict(center_cm=[cx*100.,cy*100.,datum*100.],bend_length_m=round(stations[-1],1),
              gate_to_entry_m=round(np.hypot(*np.diff(full,axis=0).T).sum(),1),protected_m2=int(work.sum()),ground_tiles=tiles)
    (out/'quarry.json').write_text(json.dumps(data,indent=2))
    print(data)

if __name__=='__main__': prepare(Path(sys.argv[1]),Path(sys.argv[2]))
