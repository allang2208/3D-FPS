"""Directional cheek mane in the same UV domain used by the solid relief."""
from pathlib import Path
from importlib.util import spec_from_file_location, module_from_spec
import json
import numpy as np

P=Path(__file__).resolve().parent
spec=spec_from_file_location('tiger_original_surface',P.parent/'surface_recipe.py')
base=module_from_spec(spec);spec.loader.exec_module(base)
SOURCE=base.SOURCE
sample=base.sample
smooth=base.smooth
face_height=base.face_height
connector_field=base.connector_field
cloud=base.cloud
SIDE=SIDE_FORM=None
if (P/'Ornament/SideManeUV.npy').exists():
    SIDE=np.load(P/'Ornament/SideManeUV.npy')
    SIDE_FORM=np.load(P/'Ornament/SideManeUV_Form.npy')

def body_height(u,v):
    return .0018*smooth(.08,.92,sample(SIDE_FORM,np.asarray(u)%1,np.asarray(v)))

def catmull(points,steps=12):
    pts=np.asarray(points,dtype=float)/1000
    result=[]
    for i in range(len(pts)-1):
        a,b,c,d=pts[max(0,i-1)],pts[i],pts[i+1],pts[min(len(pts)-1,i+2)]
        for t in np.linspace(0,1,steps,endpoint=False):
            result.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.asarray(result+[pts[-1]])

# y (forward), z (up), millimetres in the original curved skull domain.
# Ribbons flow from the temple/jowl toward the rear/lower mane.
PATHS=[
    ([[29,30],[16,31],[8,27],[15,24],[8,20],[-1,21]],2.6),
    ([[27,22],[16,17],[3,16],[-2,10],[6,6],[2,-1],[-8,-9],[-4,-17]],3.3),
    ([[27,11],[18,8],[12,1],[16,-6],[8,-15],[-1,-22],[-4,-30]],3.1),
    ([[27,-1],[24,-11],[15,-18],[15,-23],[7,-30],[2,-39]],3.0),
    ([[7,27],[-5,23],[-14,16],[-13,9],[-20,1],[-17,-8],[-12,-18],[-7,-25]],3.0),
    ([[-3,30],[-16,25],[-24,15],[-25,4],[-23,-7],[-18,-18],[-10,-28]],2.2),
]

def mane_field(u,v):
    theta=(u%1-.5)*np.pi*2;beta=(v-.5)*np.pi
    x=.044*np.cos(beta)*np.sin(theta)
    y=.004-.044*np.sin(beta)
    z=-.0015+.044*np.cos(beta)*np.cos(theta)
    nx=np.abs(x/.044)
    side=smooth(.32,.73,nx)
    flow=np.zeros_like(u);grooves=np.zeros_like(u)
    locks=[]
    for points,width in PATHS:
        for offset in (-1.6,0,1.6):
            shifted=[[p[0]+offset,p[1]+offset*.2] for p in points]
            locks.append((shifted,width*.43))
    for points,width in locks:
        path=catmull(points,steps=9)
        closest=np.full_like(u,1e6);phase=np.zeros_like(u)
        for i,(a,b) in enumerate(zip(path,path[1:])):
            dy,dz=b-a
            t=np.clip(((y-a[0])*dy+(z-a[1])*dz)/(dy*dy+dz*dz),0,1)
            ddy=y-a[0]-t*dy;ddz=z-a[1]-t*dz
            ds=ddy*ddy+ddz*ddz
            take=ds<closest
            phase=np.where(take,(i+t)/(len(path)-1),phase)
            closest=np.minimum(closest,ds)
        taper=(.28+.72*np.sin(np.pi*np.clip(phase,0,1))**.35)
        radius=width*.001*taper
        dist=np.sqrt(closest)/radius
        ridge=np.exp(-2.4*dist**2)*(.82+.18*(1-phase))
        # Shallow parallel chased lines on each substantial, curved lock.
        strand=np.exp(-1.2*dist**2)*(.5+.5*np.cos(dist*15+phase*3))*0.13
        flow=np.maximum(flow,ridge)
        grooves=np.maximum(grooves,strand)
    old=base.body_field(u,v)
    # The old cloud motif survives on the back and in negative spaces. Side locks
    # dominate the profile instead of a uniform floral pattern across the cheek.
    side_form=np.clip(.08+.46*old+.47*flow-.10*grooves,0,1)
    return old*(1-side)+side_form*side

if __name__=='__main__':
    from PIL import Image,ImageFilter
    n=2048
    field=np.empty((n,n),np.float32)
    for row in range(0,n,128):
        end=min(n,row+128)
        u,v=np.meshgrid(np.linspace(0,1,n,dtype=np.float32),np.arange(row,end,dtype=np.float32)/(n-1))
        field[row:end]=mane_field(u,v)
    # Match the periodic seam before baking geometry and PBR.
    seam=(field[:,0]+field[:,-1])*.5;field[:,0]=seam;field[:,-1]=seam
    im=Image.fromarray(np.clip(field*255,0,255).astype('uint8'))
    form=np.asarray(im.filter(ImageFilter.GaussianBlur(2)),np.float32)/255
    np.save(P/'Ornament/SideManeUV.npy',field)
    np.save(P/'Ornament/SideManeUV_Form.npy',form)
    im.save(P/'Ornament/SideManeUV_HeightSource.png')
    ridges=smooth(.16,.78,field)
    color=np.array([.37,.235,.105],np.float32)[None,None,:]*(.13+.87*ridges[...,None])
    rough=.47-.10*ridges
    ao=.69+.31*smooth(.10,.49,field)
    h=(field-form)*.00020
    dy,dx=np.gradient(h)
    normal=np.stack([-dx/(.23/(n-1)),dy/(.055/(n-1)),np.ones_like(h)],2)
    normal/=np.linalg.norm(normal,axis=2)[...,None]
    maps={'BaseColor':base.encode(color),'ORM':np.stack([ao,rough,np.ones_like(field)],2),'Normal':normal*.5+.5}
    (P/'TexturesRaw').mkdir(exist_ok=True)
    for key,value in maps.items():
        im=Image.fromarray(np.clip(value*255+.5,0,255).astype('uint8'))
        for folder in ('TexturesRaw','Textures'):
            im.save(P/folder/('TangDao_TigerPommel_ChasedBody_'+key+'.png'))
    (P/'surface_recipe.json').write_text(json.dumps({'route':'local directional mane relief and shared-domain PBR',
        'geometry_height_mm':1.8,'resolution':n,'paths_yz_mm':PATHS,'front_and_connector_textures':'reuse parent',
        'runtime_tested':False},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('V6_DIRECTIONAL_SIDE_MANE_PBR_SAVED',flush=True)
