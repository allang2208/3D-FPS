"""Fit visible relief against the registered front/depth surfaces and fix PBR in the original UV islands."""
from pathlib import Path
import json,sys
import numpy as np
import cv2
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from numba import njit

root=Path(__file__).resolve().parents[5]
home=root/'SourceAssets/HillsVillageStable'
dest=home/'StablemasterLikenessR6'
old=home/'StablemasterHeadR5'
author=home/'StablemasterMeshyR3/Authoring'
sys.path.insert(0,str(root/'Tools/VillageHerbalist/Face'))
import author_face_texture as raster
raster.W,raster.H,raster.SS=600,625,1
data=np.load(old/'HeadSurface.npz')
p,f,uv=data['pos'].copy(),data['tri'],data['uv']
faceverts=p[f].reshape(-1,3)
indices=np.arange(len(faceverts),dtype='i').reshape(-1,3)
def project(axis,sign):
    xy=np.column_stack((300+20*faceverts[:,axis],20*(168.8-faceverts[:,2]))).astype('f')
    dep,idx,_=raster.projection(xy,sign*faceverts[:,1-axis],uv.reshape(-1,2),indices)
    return dep,idx>=0
front,ok=project(0,-1)
side,side_ok=project(1,1)
h,w=front.shape
Y,X=np.mgrid[:h,:w]
def soft(lo,hi,v):
    v=np.clip((v-lo)/(hi-lo),0,1)
    return v*v*(3.-2*v)
def oval(cx,cy,rx,ry):
    return np.exp(-.5*((X-cx)**2/rx**2+(Y-cy)**2/ry**2))
def sample(a,x,y):
    return map_coordinates(a,[y,x],order=1,mode='nearest')
def smooth_depth(sigma):
    n=gaussian_filter(np.where(ok,front,0),sigma)
    d=gaussian_filter(ok.astype('f'),sigma)
    return n/np.maximum(.001,d)
smooth=smooth_depth(3.0)
broad=smooth_depth(10.5)
feature=np.maximum.reduce([oval(241,263,42,13),oval(368,263,42,13),oval(303,355,32,13),oval(303,407,49,12),.64*oval(232,327,32,35),.64*oval(377,327,32,35)])
skinshape=soft(141,205,Y)*(1-soft(439,489,Y))*(1-soft(.71,1,((X-304)/151)**2+((Y-317)/202)**2))
depth_change=np.clip((broad-smooth)*.72,-.19,.19)*feature*skinshape
fx=300+20*p[:,0];fy=(168.8-p[:,2])*20;sx=300+20*p[:,1]
readable=np.where(ok,front,-50)
surface=1-soft(.05,.32,np.abs(-p[:,1]-sample(readable,fx,fy)))
# Lock the frontmost contour in the supplied profile, including nasal tip, lips and chin.
profile_start=np.argmax(side_ok,axis=1)
profile_guard=soft(1.3,9,sx-np.interp(fy,np.arange(h),profile_start))
dz=sample(depth_change,fx,fy)*surface*profile_guard
# All displacements are in the camera-depth direction. Thus frontal landmark placement stays locked.
newpos=p.copy();newpos[:,1]-=dz
# Use a continuous facial normal field rather than independent glossy edges at UV/hair-card splits.
low=smooth_depth(12.5)
grad_y,grad_x=np.gradient(low)
target=np.stack([-20*sample(grad_x,fx,fy),-np.ones(len(p)),20*sample(grad_y,fx,fy)],axis=1)
target/=np.maximum(.001,np.linalg.norm(target,axis=1,keepdims=True))
nweight=sample(skinshape*(.24+.67*feature),fx,fy)*surface
# Around the protruding brow line retain the outer outline but suppress doubled shadows from scanned layers.
def rgb(path):return np.asarray(Image.open(path).convert('RGB')).copy()
color=rgb(author/'T_Stablemaster_Body_0_Color.png')
temples=rgb(old/'T_Stablemaster_Head_R5_Color.png')
normal=rgb(author/'T_Stablemaster_Body_0_Normal.png');old_mask=rgb(author/'T_Stablemaster_Body_0_ORM.png')
normal_hw=normal.shape[:2];mask_hw=old_mask.shape[:2]
base_size=(color.shape[1],color.shape[0])
normal=cv2.resize(normal,base_size,interpolation=cv2.INTER_LINEAR)
old_mask=cv2.resize(old_mask,base_size,interpolation=cv2.INTER_LINEAR)
fr=rgb(dest/'front.png');sd=rgb(dest/'side.png')
# Smooth side-view shading in 3D as well. The frontal depth field does not cover
# the oblique cheek, lower jaw or the thin overlapping sheets around the bun.
from scipy.spatial import cKDTree
unique,inv=np.unique(np.round(p,3),axis=0,return_inverse=True)
tree=cKDTree(unique)
norm3=np.zeros((len(unique),3),dtype='f')
for start in range(0,len(unique),768):
    q=unique[start:start+768];ds,nb=tree.query(q,k=100)
    cloud=unique[nb];wgt=np.exp(-.5*(ds/.61)**2)
    ctr=(cloud*wgt[:,:,None]).sum(1)/np.maximum(.00001,wgt.sum(1)[:,None])
    local=cloud-ctr[:,None,:]
    cov=np.einsum('bki,bk,bkj->bij',local,wgt,local)
    _,axes=np.linalg.eigh(cov);nn=axes[:,:,0]
    outward=q-np.array([0.,0.,156.2],dtype='f')
    nn*=np.where((nn*outward).sum(1)>=0,1.,-1.)[:,None]
    norm3[start:start+len(q)]=nn
skin_m=np.zeros(len(p),dtype='f');hair_m=np.zeros_like(skin_m)
ux=np.clip((uv[:,:,0]*color.shape[1]).astype(int),0,color.shape[1]-1)
uy=np.clip((uv[:,:,1]*color.shape[0]).astype(int),0,color.shape[0]-1)
tone=color[uy,ux].astype('f')
sw=soft(36,130,tone[:,:,0])*soft(3,24,tone[:,:,0]-tone[:,:,1])
hw=(1-soft(42,92,tone[:,:,0]))*soft(148.,154.,p[f,2])
np.maximum.at(skin_m,f.ravel(),sw.ravel());np.maximum.at(hair_m,f.ravel(),hw.ravel())
skin_m*=soft(145.7,147.8,p[:,2]);hair_m*=1-.88*skin_m
side_dermis=skin_m*soft(3.0,6.9,np.abs(p[:,0]))*(1-soft(163,165,p[:,2]))
extra=side_dermis*.77
# Cap normals on hair cards follow the skull and the separate lower bun volumes.
core=np.array([0.,.5,158.1]);bun=np.array([0.,8.8,151.3])
cap=(p-core)/np.array([8.0**2,10.5**2,10.1**2])
bun_n=(p-bun)/np.array([6.5**2,5.6**2,5.4**2])
blend_bun=soft(4.7,9.8,p[:,1])*(1-soft(153.,159.,p[:,2]))
cap=cap*(1-blend_bun[:,None])+bun_n*blend_bun[:,None]
cap/=np.maximum(.001,np.linalg.norm(cap,axis=1,keepdims=True))
hairw=.65*hair_m*(1-soft(.50,.88,nweight))
np.savez_compressed(dest/'facial_fit.npz',pos=newpos.astype('f'),normal=target.astype('f'),weight=nweight.astype('f'),
                    side_normal=norm3[inv],side_weight=extra,hair_normal=cap.astype('f'),hair_weight=hairw.astype('f'))
def extend(pixels,occupied):
    dist,ids=cv2.distanceTransformWithLabels(1-occupied,cv2.DIST_L2,5,labelType=cv2.DIST_LABEL_PIXEL)
    seam=(dist>0)&(dist<=4)
    pixels[seam]=pixels[occupied!=0][ids[seam]-1]
@njit
def clamp(v,lo,hi):return min(hi,max(lo,v))
@njit
def bake(positions,tri,coords,albedo,temple,norm,orm,front_ref,side_ref,frontdepth,sidedepth):
    H,W=albedo.shape[:2];out=albedo.copy();sn=norm.copy()
    # R = subsurface distance multiplier, G = perceptual roughness, B = dielectric specular parameter.
    props=np.empty_like(norm);props[:,:,0]=0;props[:,:,1]=orm[:,:,1];props[:,:,2]=120
    occupied=np.zeros((H,W),np.uint8)
    for i in range(len(tri)):
        u=coords[i,:,0]*W-.5;v=coords[i,:,1]*H-.5
        det=(u[1]-u[0])*(v[2]-v[0])-(v[1]-v[0])*(u[2]-u[0])
        if abs(det)<1.e-8:continue
        for y in range(max(0,int(np.ceil(v.min()))),min(H,int(np.floor(v.max()))+1)):
            for x in range(max(0,int(np.ceil(u.min()))),min(W,int(np.floor(u.max()))+1)):
                b=((x-u[0])*(v[2]-v[0])-(y-v[0])*(u[2]-u[0]))/det
                c=((y-v[0])*(u[1]-u[0])-(x-u[0])*(v[1]-v[0]))/det;a=1-b-c
                if min(a,b,c)<-1e-6:continue
                occupied[y,x]=1
                q=positions[tri[i,0]]*a+positions[tri[i,1]]*b+positions[tri[i,2]]*c
                fx=int(clamp(round(300+20*q[0]),0,599));sx=int(clamp(round(300+20*q[1]),0,599))
                py=int(clamp(round((168.8-q[2])*20),0,624))
                r,g,blue=float(albedo[y,x,0]),float(albedo[y,x,1]),float(albedo[y,x,2])
                pigment=clamp((r-g-4)/25,0.,1.)*clamp((r-49)/85,0.,1.)
                neck=clamp((q[2]-145.6)/2.6,0.,1.)
                skin=pigment*neck
                ff=clamp(1-abs(frontdepth[py,fx]+q[1])/.23,0.,1.)*clamp((9.2-abs(q[0]))/2.8,0.,1.)
                ss=clamp(1-abs(sidedepth[py,sx]-q[0])/.22,0.,1.)*clamp((abs(q[0])-4.1)/3.,0.,1.)
                # Transfer the two supplied views only where the corresponding surface is visible.
                # Use the original atlas elsewhere, including the unseen side of the head.
                # Under the project's tone curve the dark pigment of the full-body atlas
                # crushes into black. Fit a bounded pigment response on scalp and bun only.
                hairline=135.+min(170.,.0045*(fx-303.)**2)
                cap=max(clamp((hairline-py+8.)/19.,0.,1.),clamp((q[1]+.7)/2.8,0.,1.))
                dark_hair=cap*clamp((88.-r)/47.,0.,1.)*neck
                for j in range(3):
                    base=.54*albedo[y,x,j]+.46*temple[y,x,j]
                    warm_lift=min(34.,.92*base+5.)*(1. if j==0 else .94 if j==1 else .85)
                    neutral_lift=min(31.,.90*g+6.)*(.79 if j==0 else 1.25 if j==1 else 1.38)
                    # Interpolate the two measured studio responses around the reference's dark brown.
                    base+=dark_hair*(.49*warm_lift+.51*neutral_lift)
                    base+=skin*(3.8 if j==0 else -2.4 if j==1 else -3.0)
                    s1=front_ref[py,fx,j];s2=side_ref[py,sx,j]
                    weight=.40*neck
                    delta=(clamp(float(s1)-albedo[y,x,j],-15.,15.)*ff+clamp(float(s2)-albedo[y,x,j],-15.,15.)*ss)/max(1.,ff+ss)
                    out[y,x,j]=int(clamp(round(base+weight*delta),0.,255.))
                eyelid=0.
                for ex in (244.,364.):
                    e=((fx-ex)/36.)**2+((py-281.)/14.)**2
                    eyelid=max(eyelid,np.exp(-.7*e)*ff)
                skin=max(skin,.85*eyelid)
                hair=clamp((81.-r)/48.,0.,1.)*neck
                brow=ff*np.exp(-((py-258.)/13.)**2)*clamp((96.-r)/48.,0.,1.)
                # The face's nonmetallic response differs from both the cloth atlas and the braided hair.
                props[y,x,0]=round(255*skin*(1-.79*eyelid))
                props[y,x,1]=round(clamp(orm[y,x,1]*(1-skin)+skin*(168.-59.*eyelid)+hair*9,0.,255.))
                props[y,x,2]=round(120.-skin*44.+eyelid*64.-hair*48.)
                strength=clamp(1.-.67*skin-.53*max(hair,brow),.21,1.)
                nx=(norm[y,x,0]/127.5-1)*strength;ny=(norm[y,x,1]/127.5-1)*strength
                length=np.sqrt(max(0.,1.-nx*nx-ny*ny))
                sn[y,x,0]=round(127.5*(nx+1));sn[y,x,1]=round(127.5*(ny+1));sn[y,x,2]=round(127.5*(length+1))
    return out,sn,props,occupied
al,nm,props,mask=bake(p,f,uv,color,temples,normal,old_mask,fr,sd,readable,np.where(side_ok,side,-50))
for label,img in [('Color',al),('Normal',nm),('Surface',props)]:
    extend(img,mask)
    if label in ('Normal','Surface'):
        hh,ww=normal_hw if label=='Normal' else mask_hw
        img=cv2.resize(img,(ww,hh),interpolation=cv2.INTER_AREA)
    Image.fromarray(img).save(dest/('T_Stablemaster_FaceR6_'+label+'.png'))
stats={'input_vertices':len(p),'moved_vertices_over_0.1mm':int(np.sum(np.abs(dz)>.01)),'peak_displacement_mm':float(10*np.max(np.abs(dz))),'normals_refitted':int(np.sum(nweight>.05)),'front_pixels_per_cm':20,'front_shape_locked':'X,Z','profile_landmarks_locked':'left silhouette per scanline','reference_views':['front','side']}
(dest/'fit.json').write_text(json.dumps(stats,indent=2))
print(stats)
