"""Transfer calibrated design landmarks to the visible facial UV islands and match neck skin."""
from pathlib import Path
import sys,json
import cv2
import numpy as np
from PIL import Image
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import cKDTree
from numba import njit
P=Path(__file__).resolve().parents[5]
sys.path.insert(0,str(P/'Tools/VillageHerbalist/Face'))
import author_face_texture as raster
W,H,SS=600,625,2
raster.W,raster.H,raster.SS=W,H,SS
R=P/'SourceAssets/HillsVillageStable';OUT=R/'StablemasterMeshyR4';OLD=R/'StablemasterMeshyR3/Authoring'
def atlas(role):
    return np.asarray(Image.open(OLD/f'T_Stablemaster_{role}_0_Color.png').convert('RGB')).copy()
base=atlas('Head');body=atlas('Body')
data=np.load(OUT/'face_projection.npz')
tri=data['triangles'];p=data['positions'][tri].reshape(-1,3)
uv=data['uv'].reshape(-1,2);ids=np.arange(len(p),dtype='i').reshape(-1,3)
xy=np.stack((300+p[:,0]*20,(168.8-p[:,2])*20),axis=1)
depth=-p[:,1];zbuf,faces,coords=raster.projection(xy,depth,uv,ids)
old=raster.render_texels(base,coords,faces)
# Pairs are the same landmarks in the Meshy frontal projection and the R2 design.
pairs=[
 ((310,113),(243,172)),((210,143),(138,201)),((400,145),(340,201)),
 ((178,210),(109,277)),((437,211),(380,277)),
 ((198,257),(120,333)),((227,245),(153,320)),((249,246),(179,323)),((278,251),(211,329)),
 ((330,249),(270,327)),((365,242),(307,318)),((394,245),(341,320)),((413,250),(359,328)),
 ((212,277),(142,356)),((229,267),(161,345)),((246,263),(181,341)),((263,268),(195,345)),((275,278),(209,357)),
 ((246,273),(178,352)),((244,282),(176,363)),
 ((338,277),(276,354)),((352,267),(294,343)),((369,262),(309,340)),((387,265),(330,343)),((400,272),(342,350)),
 ((368,272),(309,350)),((370,282),(311,361)),
 ((307,269),(241,346)),((303,313),(238,398)),((307,347),(241,433)),
 ((280,355),(211,441)),((293,360),(222,449)),((310,363),(242,454)),((327,360),(257,447)),((337,352),(273,436)),
 ((258,408),(190,496)),((283,398),(214,488)),((301,394),(235,482)),((310,398),(243,486)),
 ((319,393),(252,482)),((341,396),(275,487)),((360,407),(300,492)),
 ((310,408),(245,497)),((308,421),(243,514)),
 ((198,359),(114,449)),((419,358),(370,442)),((209,421),(132,513)),((406,421),(349,510)),
 ((229,468),(158,551)),((308,493),(244,582)),((385,465),(327,549)),
 ((182,300),(95,371)),((434,302),(391,371)),((310,454),(244,551))
]
source,ref=map(np.asarray,zip(*pairs))
Y,X=np.mgrid[:H*SS,:W*SS].astype('f')/SS
warp=LinearNDInterpolator(source,ref,fill_value=0)
mapped=warp(X,Y).astype('f');reference=np.asarray(Image.open(R/'StablemasterR2/FaceTurnaround.png').convert('RGB'))
design=cv2.remap(reference,mapped,None,cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
outline=np.array([(180,209),(211,146),(265,125),(315,120),(372,130),(405,150),(436,211),(432,303),(418,365),(405,417),(380,462),(346,482),(310,490),(269,479),(230,461),(210,418),(198,366),(182,301)])
mask=np.zeros(Y.shape,'uint8');cv2.fillPoly(mask,[(outline*SS).astype('i')],255)
mask=cv2.distanceTransform(mask,cv2.DIST_L2,5)
weight=np.clip(mask/(17.*SS),0,1)
weight=weight*weight*(3-2*weight)*.93*(faces>=0)*(mapped[:,:,0]>0)
# Remove the broad studio light from the reference; retain eyelid, iris, lip
# and eyebrow contrast. The original PBR normals still respond to village light.
d=design.astype('f');a=old.astype('f')
diff=cv2.GaussianBlur((a-d)*weight[:,:,None],(0,0),19*SS)
norm=cv2.GaussianBlur(weight.astype('f'),(0,0),19*SS)
target=np.clip(d+.78*diff/np.maximum(.25,norm[:,:,None]),0,255).astype('f')
@njit
def paint(xy,depth,uv,faces,zbuf,visible,target,weight,base):
    h,w=base.shape[:2];out=base.copy();change=np.zeros((h,w),np.uint8)
    for fi in visible:
        ind=faces[fi];a,b,c=uv[ind[0]],uv[ind[1]],uv[ind[2]]
        det=raster.det(a,b,c)
        if abs(det)<1.e-8:continue
        for y in range(max(0,int(np.ceil(min(a[1],b[1],c[1])))),min(h,int(np.floor(max(a[1],b[1],c[1])))+1)):
            for x in range(max(0,int(np.ceil(min(a[0],b[0],c[0])))),min(w,int(np.floor(max(a[0],b[0],c[0])))+1)):
                u,v,t=raster.barycentric(x,y,a,b,c,det)
                if min(u,v,t)<-1e-6:continue
                q=(u*xy[ind[0]]+v*xy[ind[1]]+t*xy[ind[2]])*SS
                sx,sy=round(q[0]),round(q[1])
                if not (0<=sx<weight.shape[1] and 0<=sy<weight.shape[0]):continue
                z=u*depth[ind[0]]+v*depth[ind[1]]+t*depth[ind[2]]
                if abs(z-zbuf[sy,sx])>.085:continue
                f=weight[sy,sx]
                if f<=0:continue
                for ch in range(3):out[y,x,ch]=round(base[y,x,ch]*(1-f)+target[sy,sx,ch]*f)
                change[y,x]=1
    return out,change
fac=np.unique(faces[(weight>.0001)&(faces>=0)])
atlas_xy=uv*np.array([base.shape[1],base.shape[0]],'f')-.5
after,modified=paint(xy,depth,atlas_xy,ids,zbuf,fac,target,weight,base)
# Sample both UV charts along corresponding physical edges, then diffuse the
# color difference a few centimetres up the neck. The face and hair stay separate.
rims=json.loads((OUT/'rim_samples.json').read_bytes())
def rim(role,img):
    centers=[];colors=[]
    for a,b,ua,ub in rims[role]:
        for f in (.125,.375,.625,.875):
            q=np.array(a)*(1.-f)+np.array(b)*f
            u,v=np.array(ua)*(1.-f)+np.array(ub)*f
            centers.append(q);colors.append(img[round((1-v)*(len(img)-1)),round(u*(img.shape[1]-1))].copy())
    return np.asarray(centers),np.asarray(colors,dtype='f')
pos,cl=rim('Head',after);q,body_col=rim('Body',body)
tree=cKDTree(pos);correction=body_col[cKDTree(q).query(pos)[1]]-cl
fit=json.loads((OUT/'fit.json').read_bytes())
neck=np.load(OUT/'neck_projection.npz')
for verts,uvs in zip(neck['positions'][neck['triangles']],neck['uv']):
    dz=verts[:,2]-fit['neck_slope']*verts[:,1]-fit['neck_base']
    if dz.min()>3.9 or dz.max()<-.07 or verts[:,1].min()>8.:continue
    # Never draw over the bun where it drops behind the neck.
    ds,near=tree.query(verts,k=6)
    if ds.min()>4.5:continue
    uvs=uvs*np.array([base.shape[1],base.shape[0]])-.5
    a,b,c=uvs;lo=np.maximum(np.ceil(uvs.min(0)).astype(int),0);hi=np.minimum(np.floor(uvs.max(0)).astype(int),[base.shape[1]-1,base.shape[0]-1])
    if np.any(lo>hi):continue
    xs,ys=np.meshgrid(np.arange(lo[0],hi[0]+1),np.arange(lo[1],hi[1]+1))
    mat=np.vstack((uvs.T,np.ones(3)))
    if abs(np.linalg.det(mat))<1e-5:continue
    bary=np.linalg.solve(mat,np.array([xs.ravel(),ys.ravel(),np.ones(xs.size)]))
    ok=bary.min(0)>-1e-7
    if not ok.any():continue
    bary=bary[:,ok];yy=ys.ravel()[ok];xx=xs.ravel()[ok];points=bary.T@verts
    distance,index=tree.query(points,k=8);d=distance[:,0]
    influence=1./np.maximum(.025,distance)**2
    color=(correction[index]*influence[:,:,None]).sum(1)/influence.sum(1)[:,None]
    radial=np.linalg.norm(points[:,:2]-pos[index[:,0],:2],axis=1)
    t=np.clip(1-np.maximum(bary.T@dz,0)/3.75,0,1)*np.clip((2.6-radial)/1.5,0,1)
    t=t*t*(3-2*t)
    after[yy,xx]=np.clip(base[yy,xx]+color*t[:,None],0,255).astype('uint8')
    modified[yy[t>0],xx[t>0]]=1
raster.extend_seams(base,after,modified,atlas_xy,ids)
Image.fromarray(after).save(OUT/'T_Stablemaster_Head_R4_Color.png')
