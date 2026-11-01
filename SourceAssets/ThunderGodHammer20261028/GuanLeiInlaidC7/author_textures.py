"""UV-space PBR authoring on the actual carved mesh; original atlas stays aligned."""
from pathlib import Path
import json,sys,numpy as np
from PIL import Image
from numba import njit
P=Path(__file__).resolve().parent;sys.path.insert(0,str(P))
from design import STYLES,fields
R=4096
@njit(cache=True)
def raster(uv,pos,tan,bit,tri,select,size):
 data=np.zeros((size,size,9),np.float32);valid=np.zeros((size,size),np.uint8)
 for ti in range(len(tri)):
  if not select[ti]:continue
  ia,ib,ic=tri[ti];u=uv[ia]*(size-1);v=uv[ib]*(size-1);w=uv[ic]*(size-1)
  ax=u[0];ay=size-1-u[1];bx=v[0];by=size-1-v[1];cx=w[0];cy=size-1-w[1]
  det=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
  if abs(det)<1e-10:continue
  for y in range(max(0,int(min(ay,by,cy))-1),min(size,int(max(ay,by,cy))+2)):
   for x in range(max(0,int(min(ax,bx,cx))-1),min(size,int(max(ax,bx,cx))+2)):
    a=((by-cy)*(x+.5-cx)+(cx-bx)*(y+.5-cy))/det
    b=((cy-ay)*(x+.5-cx)+(ax-cx)*(y+.5-cy))/det;c=1-a-b
    if min(a,b,c)<-1e-6:continue
    valid[y,x]=1
    for k in range(3):
     data[y,x,k]=a*pos[ia,k]+b*pos[ib,k]+c*pos[ic,k]
     data[y,x,k+3]=a*tan[ia,k]+b*tan[ib,k]+c*tan[ic,k]
     data[y,x,k+6]=a*bit[ia,k]+b*bit[ib,k]+c*bit[ic,k]
 return data,valid
def load_image(name):
 return np.array(Image.open(P.parent/'Textures'/(name+'.jpg')).convert('RGB').resize((R,R),Image.Resampling.LANCZOS))
def srgb_to_linear(v):return np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
def linear_to_srgb(v):return np.where(v<=.0031308,v*12.92,1.055*np.maximum(v,0)**(1/2.4)-.055)
receipt=[]
for s in STYLES:
 a=np.load(P/'Data'/(s['id']+'.npz'));p=a['position'];uv=a['uv'];tris=a['triangles'];t=a['tangent'];b=a['bitangent']
 f=fields(p,s);active=(np.abs(f[0])>1e-8)|(f[1]>.001)|(f[4]>.001);select=np.any(active[tris],axis=1)
 data,valid=raster(uv,p,t,b,tris,select,R);yy,xx=np.nonzero(valid);q=data[yy,xx];del data,valid,p,uv,tris,t,b,f,active,select
 position=q[:,:3].astype(np.float64);depth,silver,channel,seam,shoulder=fields(position,s)
 silver=np.clip(silver,0,1);channel=np.clip(channel,0,1);seam=np.clip(seam,0,1)
 xyz=position;phase1=xyz[:,0]*28000+xyz[:,2]*32000;phase2=xyz[:,0]*95000-xyz[:,2]*44000
 grain=.96+.04*np.sin(phase1)*np.sin(phase2)
 c=load_image('BaseColor');col=srgb_to_linear(c[yy,xx].astype(np.float64)/255)
 darkening=.28 if s['id']=='storm_drive_seat' else .16
 col*=1-shoulder[:,None]*darkening
 recess=(channel*(1-silver))[:,None];col=col*(1-recess*.70)+np.array([.075,.085,.095])*recess*.70
 silver_color=np.array([.58,.59,.60])*grain[:,None]
 col=col*(1-silver[:,None])+silver_color*silver[:,None]
 col=col*(1-seam[:,None]*.83)+np.array([.018,.020,.022])*seam[:,None]*.83
 c[yy,xx]=np.uint8(np.clip(linear_to_srgb(col)*255+.5,0,255));Image.fromarray(c).save(P/'Textures'/('T_GuanLeiC7_'+s['id']+'_BaseColor.png'));del c,col
 orm=load_image('MetallicRoughness');v=orm[yy,xx].astype(np.float64)/255
 v[:,0]*=1-.20*channel*(1-silver)
 v[:,1]=v[:,1]*(1-channel*.55)+.56*channel*.55;v[:,1]=v[:,1]*(1-silver)+(.31+.055*(1-grain))*silver
 v[:,2]=v[:,2]*(1-silver)+.96*silver
 v[:,1]=v[:,1]*(1-seam)+.78*seam;v[:,2]=v[:,2]*(1-seam)+.12*seam
 orm[yy,xx]=np.uint8(np.clip(v*255+.5,0,255));Image.fromarray(orm).save(P/'Textures'/('T_GuanLeiC7_'+s['id']+'_ORM.png'));del orm,v
 image=load_image('Normal');normal=image[yy,xx].astype(np.float64)/255*2-1
 tangent=q[:,3:6].astype(np.float64);bitangent=q[:,6:9].astype(np.float64)
 tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-8);bitangent/=np.maximum(np.linalg.norm(bitangent,axis=1,keepdims=True),1e-8)
 gradient=np.zeros_like(position);gradient[:,0]=.000004*28000*np.cos(phase1)+.0000015*95000*np.cos(phase2);gradient[:,2]=.000004*32000*np.cos(phase1)-.0000015*44000*np.cos(phase2)
 fine=np.column_stack((-np.sum(gradient*tangent,axis=1),-np.sum(gradient*bitangent,axis=1),np.ones(len(yy))))
 fine/=np.linalg.norm(fine,axis=1,keepdims=True)
 weight=np.clip(silver+seam*.7+channel*.18,0,1)[:,None];normal=normal*(1-weight)+fine*weight;normal/=np.maximum(np.linalg.norm(normal,axis=1,keepdims=True),1e-8)
 image[yy,xx]=np.uint8(np.clip((normal+1)*127.5+.5,0,255));Image.fromarray(image).save(P/'Textures'/('T_GuanLeiC7_'+s['id']+'_Normal.png'))
 receipt.append(dict(id=s['id'],size=[R,R],authored_texels=len(yy),silver_texels=int(np.sum(silver>.5)),normal='Original OpenGL normal retained; new silver micro-engraving gradient transformed using actual mesh tangent frame',method='UV-space material authoring, not high-poly projection bake'))
 del image,q,position,xyz,normal,fine,gradient,tangent,bitangent,weight,yy,xx,depth,silver,channel,seam,shoulder,phase1,phase2,grain
 print('PBR_COMPLETE',s['id'],flush=True)
(P/'texture_manifest.json').write_text(json.dumps(dict(complete=True,parts=receipt),ensure_ascii=False,indent=2),encoding='utf-8')
