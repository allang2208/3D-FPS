"""Local mineral scuffs over existing triangular remnants; preserve the accepted ceramic geometry."""
from pathlib import Path
import json,gzip
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from PIL import Image
R=Path(__file__).resolve().parent;P=R.parent/'FreightOppositePlatform20261113'
env={'__file__':str(P/'bake_surfaces.py')}
exec(compile((P/'bake_surfaces.py').read_text('utf8').split('def wall(')[0],'noise','exec'),env)
field,step=env['field'],env['step']
g=json.load(gzip.open(R/'ceramic.json.gz'));t=(np.array(g['v'])+g['origin'])[g['t']];slot=np.array(g['slot']);cent=t.mean(1)
out=R/'PatinaTextures';out.mkdir(exist_ok=True);rows=[]
for number,(name,ax,plane,side,lo,hi) in enumerate([('West',0,6176.4,1,-3036,236),('East',0,10943.6,-1,-3036,236),('North',1,-3033.6,1,6174,10946),('South',1,233.6,-1,6174,10946)]):
    h=1-ax;ids=np.flatnonzero((slot==1)&(np.ptp(t[:,:,ax],axis=1)<.045)&(abs(cent[:,ax]-plane)<.5))
    uv=np.round(t[ids][:,:,[h,2]].reshape(-1,2),2);uniq,inv=np.unique(uv,axis=0,return_inverse=True);inv=inv.reshape(-1,3)
    i=np.concatenate([inv[:,0],inv[:,1],inv[:,2]]);j=np.concatenate([inv[:,1],inv[:,2],inv[:,0]])
    _,grp=connected_components(coo_matrix((np.ones(len(i)),(i,j)),shape=(len(uniq),len(uniq))),directed=False)
    labs=grp[inv[:,0]];patches=[]
    for k in np.unique(labs):
        pts=t[ids[labs==k]][:,:,[h,2]];a=pts.min((0,1));b=pts.max((0,1))
        area=np.sum(abs((pts[:,1,0]-pts[:,0,0])*(pts[:,2,1]-pts[:,0,1])-(pts[:,2,0]-pts[:,0,0])*(pts[:,1,1]-pts[:,0,1])))/2
        if not(30<area<380 and b[0]-a[0]>8 and b[1]-a[1]>8 and a[1]>15 and b[1]<148):continue
        if (name=='West' and a[0]<-1558) or (name=='North' and a[0]<7820):continue
        patches.append([*a,*b])
    W,H=4096,256;shape=(H,W);rng=np.random.default_rng(821+number*139)
    x,z=np.meshgrid(lo+(np.arange(W,dtype='f')+.5)*(hi-lo)/W,160-(np.arange(H,dtype='f')+.5)*160/H)
    coarse=field(rng,shape,54,12);fine=field(rng,shape,998,130);mid=field(rng,shape,350,70)
    alpha=np.zeros(shape,dtype='f')
    for a,z0,b,z1 in patches:
        cx=(a+b)*.5;cz=(z0+z1)*.5;ww=(b-a)*.86+2;hh=(z1-z0)*.88+2
        dist=(abs((x-cx)/ww)**4+abs((z-cz)/hh)**4)**.25
        mask=1-step(.83,1.12,dist+.12*mid+.055*fine)
        alpha=np.maximum(alpha,mask)
    # A mineral-toned broken paint bed, with quiet high-frequency variation and soft ragged margins.
    val=.365+.026*coarse+.028*mid+.022*fine
    rgb=val[:,:,None]*np.array([1.055,1.018,.88])
    rgba=np.dstack((rgb,alpha));rough=np.clip(.89+.04*mid+.025*fine,0,1)
    flip=(ax==0 and side==1) or (ax==1 and side==-1)
    def orient(a):
        a=np.rot90(a,-1)
        return np.flip(a,axis=0) if flip else a
    for typ,img in [('Color',rgba),('Rough',rough)]:
        Image.fromarray(np.uint8(np.clip(orient(img),0,1)*255+.5)).save(out/('T_Skirt'+name+'_'+typ+'.png'),compress_level=2)
    p=[0,0,80];p[ax]=plane+side*.30;p[h]=(lo+hi)/2
    yaw=(180 if side==1 else 0) if ax==0 else (-90 if side==1 else 90)
    rows.append(dict(name='Skirt'+name,pos=p,yaw=yaw,size=[2.8,(hi-lo)/2,80],clusters=len(patches)))
(R/'skirt-plan.json').write_text(json.dumps(rows,indent=1),'utf8')
print([{r['name']:r['clusters']} for r in rows])
