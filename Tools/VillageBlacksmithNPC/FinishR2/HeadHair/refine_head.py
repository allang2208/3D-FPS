"""Refine the existing smith crown and upper lids in their original welded surface and UVs."""
import shutil, math
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter
from surface_maps import *

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)
def norm(x):
    return x/np.maximum(np.linalg.norm(x,axis=-1,keepdims=True),1e-8)
def image_sample(im,uv):
    h,w=im.shape[:2]
    return im[np.clip((uv[:,1]*h).astype(int),0,h-1),np.clip((uv[:,0]*w).astype(int),0,w-1)]
def face_normals(p, f):
    sn=np.zeros_like(p)
    c=np.cross(p[f[:,2]]-p[f[:,0]],p[f[:,1]]-p[f[:,0]])
    for col in range(3):np.add.at(sn,f[:,col],c)
    return norm(sn)
def strand_field():
    # Each stroke is an individual taper with broad guide flow and independent variation.
    rng=np.random.default_rng(61118)
    ratio=86
    h,w=3650,2240
    heights=np.zeros((h,w),np.float32)
    silver=np.zeros_like(heights)
    for i in range(3200):
        start_u=rng.uniform(-13.8,13.8)
        start_v=rng.uniform(-24.,20.5)
        length=rng.uniform(3.1,15.3)
        v=np.linspace(start_v,start_v+length,45)
        t=(v-start_v)/length
        phase=rng.uniform(-3.14,3.14);amp=rng.uniform(.028,.15)
        u=start_u+.44*np.sin(.27*v+.37*start_u)+.23*np.sin(.54*v+.14*start_u)
        u+=.57*np.tanh((v+4)/3.)*np.exp(-((start_u-1.)/4.)**2)+amp*np.sin(t*3.7+phase)
        xy=np.column_stack((u*ratio+w/2,v*ratio+h/2)).astype(np.int32)
        width=int(rng.choice([1,1,1,2,2,3]));val=rng.uniform(.3,.95)
        rare=rng.uniform()<.13
        for a,b,s,e in [(0,6,.42,width),(5,33,1.,width),(32,40,.69,max(1,width-1)),(39,45,.32,1)]:
            cv2.polylines(heights,[xy[a:b]],False,float(val*s),e,cv2.LINE_AA)
            if rare:cv2.polylines(silver,[xy[a:b]],False,float(val*s),max(1,e-1),cv2.LINE_AA)
    return gaussian_filter(heights,.58),gaussian_filter(silver,.52),ratio
def hair_coords(p):
    x,y,z=p[:,0]/8.2,(p[:,1]+.85)/9.5,(p[:,2]-171.0)/10.0
    return np.stack((8.2*np.arctan2(x,np.sqrt(y*y+z*z)),9.5*np.arctan2(y,z)),axis=1)
def lock_relief(uv):
    u,v=uv.T
    root=u-.76*np.sin(v*.30+u*.29)-.49*np.sin(v*.51-u*.16)
    root-=.74*np.tanh((v+3.)/2.8)*np.exp(-((u-1.)/3.4)**2)
    phase=16.8*root+1.15*np.sin(2.8*root+.23*v)+.53*np.sin(1.11*v+1.14*u)
    group=np.cos(phase)+.30*np.cos(2*phase+.5)
    mid=np.cos(37.2*root+1.75*np.sin(phase*.54)+.37*v)
    filament=np.cos(79.0*root+1.55*np.sin(phase+.64*v)+.9*np.sin(3.*u-.55*v))
    return .030*group+.014*mid+.0055*filament, .48*group+.32*mid+.20*filament
def fibre_sample(field,scale,coords):
    h,w=field.shape
    x=np.clip(coords[:,0]*scale+w/2,0,w-2);y=np.clip(coords[:,1]*scale+h/2,0,h-2)
    ix=x.astype(int);iy=y.astype(int);dx=x-ix;dy=y-iy
    return (1-dy)*((1-dx)*field[iy,ix]+dx*field[iy,ix+1])+dy*((1-dx)*field[iy+1,ix]+dx*field[iy+1,ix+1])
def reference_hair():
    sheet=np.asarray(Image.open(ROOT/'Design/head_finished.png').convert('RGB')).astype(np.float32)
    ret=[]
    for panel in np.split(sheet,3,axis=1):
        gray=cv2.cvtColor(panel,cv2.COLOR_RGB2GRAY)
        medium=cv2.GaussianBlur(gray,(0,0),8)
        broad=cv2.GaussianBlur(gray,(0,0),22)
        chroma=panel[:,:,0]-panel[:,:,2]
        # Gate out skin, background and their silhouettes from the reference.
        hair=(1-smooth(19,40,chroma))*(1-smooth(87,123,medium))
        hair=cv2.erode(hair,np.ones((11,11),np.uint8))
        ret.append(((gray-medium)*1.2+.55*(medium-broad),hair))
    return ret
def sample_reference(ref,p):
    h,w=ref[0][0].shape
    sx,sy=p[:,0],p[:,1]+.85
    view_scores=[np.maximum(sy/10,0)**2+.08,np.abs(sx/8.2)**2+.10,np.maximum(-sy/10,0)**2+.08]
    details=np.zeros(len(p));weights=np.zeros(len(p))
    for (field,gate),x,y,score in zip(ref,[337+24*sx,390-23.1*(sy-.85),382-23.7*sx],
                                      [16+22.5*(181-p[:,2]),18+22.4*(181-p[:,2]),14+22.8*(181-p[:,2])],view_scores):
        coords=np.stack([x-w/2,y-h/2],axis=1)
        wt=score*fibre_sample(gate,1,coords)
        details+=wt*fibre_sample(field,1,coords);weights+=wt
    return details/np.maximum(weights,.22)
def main():
    d=load_face(); p=np.array(d['p']); n=np.array(d['n']);uv=np.array(d['uv'],np.float32)
    alltri=np.array(d['tri']);tri=alltri[np.array(d['m'])==0]
    colors=np.array(Image.open(OLD/'Textures'/(PREFIX+'BC.png')).convert('RGB'))
    val=image_sample(colors,uv).astype(float)
    # Merge coincident corners before smoothing so UV and normal seams stay welded.
    up,idx,back=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True)
    tree=cKDTree(up);uf=back[tri];un=face_normals(up,uf)
    aligned=np.median((un[back][np.unique(tri)]*n[np.unique(tri)]).sum(axis=1))
    if aligned<0:un*=-1
    chroma=val[:,0]-val[:,2]
    looks_hair=(1-smooth(18,37,chroma))*smooth(169.7,173.4,p[:,2])
    vw=np.zeros(len(up));np.maximum.at(vw,back,looks_hair)
    region=np.flatnonzero((up[:,2]>171.1))
    dist,near=tree.query(up[region],k=76);kw=np.exp(-.5*(dist/.48)**2);kw/=kw.sum(1)[:,None]
    hair_prob=(vw[near]*kw).sum(1)
    feather=smooth(172.0,175.3,up[region,2])*smooth(.36,.90,hair_prob)
    feather=np.maximum(feather,smooth(176.9,178.5,up[region,2]))
    mask=np.zeros(len(up));mask[region]=feather
    # Project the clumped silhouette toward a locally fitted scalp patch; broad skull curvature survives.
    smooth_n=norm((un[near]*kw[:,:,None]).sum(1));diff=up[near]-up[region,None,:]
    t1=norm(np.cross(smooth_n,[1.,0.,0.]));t2=np.cross(smooth_n,t1)
    tx=(diff*t1[:,None]).sum(2);ty=(diff*t2[:,None]).sum(2);hh=(diff*smooth_n[:,None]).sum(2)
    X=np.stack((np.ones_like(tx),tx,ty,tx*tx,tx*ty,ty*ty),axis=2)
    normal_eq=np.einsum('nki,nk,nkj->nij',X,kw,X)+np.eye(6)[None]*.0005
    rhs=np.einsum('nki,nk,nk->ni',X,kw,hh)
    fitted=np.linalg.solve(normal_eq,rhs[...,None])[:,0,0]
    # A second broad guide removes stair-stepped highlights across neighboring original clumps.
    broad=(diff*smooth_n[:,None]).sum(2)
    level=.52*fitted+.48*(broad*kw).sum(1)
    unew=up.copy()
    amount=np.clip(level,-.44,.34)*feather*.92
    unew[region]+=smooth_n*amount[:,None]
    # Some source locks are folded surfaces, with separate upper and lower sides.
    # Fit the outer crown in angular space, where the two sides have the same guide direction.
    axis_origin=np.array([0.,-.85,170.05])
    delta=up[region]-axis_origin
    radial=np.linalg.norm(delta,axis=1);direction=delta/radial[:,None]
    scalp=cKDTree(direction)
    angle=.115
    kd,ki=scalp.query(direction,k=186)
    outer=np.quantile(radial[ki],.73,axis=1)
    gw=np.exp(-.5*(kd/(angle*.66))**2);gw/=gw.sum(1)[:,None]
    outer=(outer[ki]*gw).sum(1)
    u0,v0=hair_coords(up[region]).T
    flow=u0+.42*np.sin(.27*v0+.37*u0)+.18*np.sin(.55*v0+.2*u0)
    sculpted=.041*np.cos(flow*15.8+np.sin(.73*v0))+.022*np.cos(flow*24.3+.48*np.sin(1.2*v0+u0))
    guide=axis_origin+direction*(outer+sculpted)[:,None]
    blend=(feather*.866)[:,None]
    unew[region]=(1-blend)*unew[region]+blend*guide
    # Measured lash rims from an orthographic color/depth projection of this specific fitted mesh.
    # Front projection coefficients are centimetres; lower lids and canthi are pinned.
    upper_lines=[
        ([-4.64,-4.34,-3.95,-3.55,-3.13,-2.75,-2.44,-2.17,-1.92,-1.66],
         [168.65,168.73,168.85,168.99,169.045,169.057,169.025,168.92,168.75,168.62],
         [168.65,168.68,168.62,168.55,168.51,168.52,168.55,168.60,168.64,168.62],.165),
        ([1.46,1.77,2.13,2.50,2.89,3.24,3.61,3.95,4.22,4.48],
         [168.60,168.92,169.11,169.23,169.24,169.19,169.14,169.03,168.93,168.91],
         [168.60,168.65,168.68,168.69,168.70,168.73,168.78,168.83,168.87,168.91],.145)]
    lid=np.zeros(len(up))
    for xs,zup,zlo,rise in upper_lines:
        xx,zz=up[:,0],up[:,2];upper=np.interp(xx,xs,zup);lower=np.interp(xx,xs,zlo)
        # The closed upper margin rolls upwards and back. Feather to zero before the brow ridge.
        along=np.sin(np.pi*np.clip((xx-xs[0])/(xs[-1]-xs[0]),0,1))**.72
        visible=smooth(3.3,5.7,up[:,1])
        ap=np.clip((zz-lower)/np.maximum(upper-lower,.05),0,1)
        disp=rise*along*(ap**.9)*(1-smooth(.04,.60,zz-upper))*visible
        lid+=disp
    unew[:,2]+=lid;unew[:,1]-=.20*lid
    newp=p+(unew-up)[back]
    geom_norm=face_normals(unew,uf)
    if aligned<0:geom_norm*=-1
    # Keep source shading away from the edited regions; smooth custom normals only on crown clumps.
    gmean=norm((geom_norm[near]*kw[:,:,None]).sum(1))
    crown_norm=geom_norm.copy()
    outer_guide=norm(direction*.76+gmean*.24)
    crown_norm[region]=norm(.15*geom_norm[region]+.32*gmean+.53*outer_guide)
    blend=np.maximum(mask*.90,np.clip(lid/.11,0,1)*.68)[back,None]
    newn=norm(n*(1-blend)+crown_norm[back]*blend)
    d['p']=newp.round(6).tolist();d['n']=newn.round(7).tolist()
    # Use the existing UV material, and edit only mapped crown texels plus their island padding.
    height_f,silver_f,scale=strand_field()
    photo=reference_hair()
    texuv=uv[tri]
    dp=p[tri[:,1:]]-p[tri[:,0],None];duv=texuv[:,1:]-texuv[:,0,None]
    den=duv[:,0,0]*duv[:,1,1]-duv[:,0,1]*duv[:,1,0]
    den=np.where(abs(den)<1e-9,1,den)[:,None]
    tangent=norm((dp[:,0]*duv[:,1,1,None]-dp[:,1]*duv[:,0,1,None])/den)
    bitangent=norm((dp[:,0]*duv[:,1,0,None]-dp[:,1]*duv[:,0,0,None])/den)
    keep=np.max(mask[back[tri]],axis=1)>.0001
    fs=tri[keep];tan=tangent[keep];bitan=bitangent[keep]
    h,w=colors.shape[:2];ids,barys,_=raster(uv*np.array([w,h])-.5,np.zeros(len(p)),fs,w,h)
    rows,cols=np.nonzero(ids>=0);matte=np.zeros((h,w),np.float32)
    standard_n=np.array(Image.open(OLD/'Textures'/(PREFIX+'N.png')).convert('RGB'))
    # Carry all three channels through a tiled bake to limit working memory.
    base_luma=cv2.cvtColor(colors,cv2.COLOR_RGB2GRAY)
    low=cv2.GaussianBlur(base_luma,(0,0),4)
    rough=np.array(Image.open(OLD/'Textures'/(PREFIX+'R.png')).convert('L'))
    rough_h,rough_w=rough.shape;rbuf=cv2.resize(rough,(w,h),interpolation=cv2.INTER_LINEAR)
    outputbc=colors.copy();outputn=standard_n.copy();outputrough=rbuf.copy()
    for a in range(0,len(rows),180000):
        sy=rows[a:a+180000];sx=cols[a:a+180000];ii=ids[sy,sx];bc=barys[sy,sx]
        world=interp(ii,bc,fs,p);weight=interp(ii,bc,fs,mask[back]);matte[sy,sx]=weight
        co=hair_coords(world);fine=fibre_sample(height_f,scale,co);salt=fibre_sample(silver_f,scale,co)
        _,locks=lock_relief(co)
        rgb=colors[sy,sx].astype(np.float32);luma=base_luma[sy,sx].astype(float);soft=low[sy,sx].astype(float)
        # Restrict baked broad gray reflection while retaining native salt-and-pepper variation and hairline.
        bands=luma-soft
        photo_fibre=sample_reference(photo,world)
        lum=.77*soft+.62*bands+3.+24.*fine+28.*salt+1.35*photo_fibre+16.*locks
        hair_color=rgb*.42+(lum-.42*luma)[:,None]*np.array([1.022,1.0,.976])
        outputbc[sy,sx]=np.clip(rgb+(hair_color-rgb)*weight[:,None],0,255).astype(np.uint8)
        encoded=standard_n[sy,sx].astype(float)/127.5-1
        xy=encoded[:,:2]*.40
        for k,dirs in enumerate((tan[ii],bitan[ii])):
            positive=hair_coords(world+.010*dirs);negative=hair_coords(world-.010*dirs)
            plus=fibre_sample(height_f,scale,positive);minus=fibre_sample(height_f,scale,negative)
            slope=(lock_relief(positive)[0]-lock_relief(negative)[0])/.020
            xy[:,k]-=(plus-minus)*.27+.67*slope
        hn=norm(np.column_stack([xy,np.sqrt(np.maximum(.03,1-(xy*xy).sum(1)))]))
        nb=norm(encoded*(1-weight[:,None])+hn*weight[:,None])
        outputn[sy,sx]=np.clip((nb+1)*127.5,0,255).astype(np.uint8)
        rough_tgt=np.clip(212.+.09*soft-18*fine-10*salt-.40*photo_fibre-10.*locks,172,234)
        outputrough[sy,sx]=np.clip(rbuf[sy,sx]+(rough_tgt-rbuf[sy,sx])*weight,0,255)
    # Dilate the changed delta beyond UV boundaries, without altering neighboring skin.
    valid=np.uint8(ids>=0)
    padded=cv2.dilate(valid,np.ones((7,7),np.uint8)) & (1-valid)
    if padded.any():
        _,lab=cv2.distanceTransformWithLabels(1-valid,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
        nearest=lab[padded>0]-1
        py,px=np.where(padded>0);iy,ix=rows[nearest],cols[nearest]
        alpha=matte[iy,ix]
        take=alpha>.03
        for dest in (outputbc,outputn,outputrough,matte):dest[py[take],px[take]]=dest[iy[take],ix[take]]
    color_skin_response=np.dstack([outputbc,np.uint8((1-np.clip(matte,0,1))*255)])
    for suffix,array in [('BC',color_skin_response),('N',outputn),('R',cv2.resize(outputrough,(rough_w,rough_h),interpolation=cv2.INTER_AREA))]:
        Image.fromarray(array).save(TEX/(PREFIX+suffix+'.png'))
    shutil.copy2(OLD/'fit.json',OUT/'fit.json')
    with gzip.open(OUT/'face.json.gz.tmp','wt',encoding='utf8',compresslevel=3) as stream:json.dump(d,stream,separators=(',',':'))
    (OUT/'face.json.gz.tmp').replace(OUT/'face.json.gz')
    (OUT/'sculpt.json').write_text(json.dumps({'original_mesh':'../../HeadHair/face.json.gz','crown_affected_vertices':int(sum(mask>.02)),'crown_peak_reduction_cm':round(float(-min(amount)),3),'eye_rise_cm':[round(float(max(lid[up[:,0]<0])),3),round(float(max(lid[up[:,0]>0])),3)],'triangles':len(alltri),'uses_original_uv_weights':True},indent=2))
    projection(OUT,'eye_landmarks_after')
if __name__=='__main__':main()
