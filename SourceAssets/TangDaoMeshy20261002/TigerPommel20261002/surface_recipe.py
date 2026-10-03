"""Shared sculpt displacement and physically separated bronze/gilt/garnet PBR."""
from pathlib import Path
import numpy as np
P=Path(__file__).resolve().parent
try:
    from PIL import Image,ImageFilter
    _im=Image.open(P/'Ornament/TigerFace_HeightSource.png').convert('L')
    FORM=np.asarray(_im.filter(ImageFilter.GaussianBlur(7)),np.float32)/255
except ImportError:
    FORM=None
try:
    import bpy
    im=bpy.data.images.load(str(P/'Ornament/TigerFace_HeightSource.png'))
    im.colorspace_settings.name='Non-Color'
    values=np.empty(im.size[0]*im.size[1]*4,np.float32);im.pixels.foreach_get(values)
    SOURCE=values.reshape(im.size[1],im.size[0],4)[::-1,:,:3].mean(axis=2).copy()
    # Blender carries NumPy but not Pillow; separable Gaussian for the sculpt.
    if FORM is None:
        radius=21;weights=np.exp(-np.arange(-radius,radius+1,dtype=float)**2/(2*7**2));weights/=weights.sum()
        FORM=np.apply_along_axis(lambda a:np.convolve(np.pad(a,radius,mode='edge'),weights,mode='valid'),0,SOURCE)
        FORM=np.apply_along_axis(lambda a:np.convolve(np.pad(a,radius,mode='edge'),weights,mode='valid'),1,FORM)
except ImportError:
    from PIL import Image,ImageFilter
    SOURCE=np.asarray(Image.open(P/'Ornament/TigerFace_HeightSource.png').convert('L'),np.float32)/255

try:
    from PIL import Image,ImageFilter
    _body=Image.open(P/'Ornament/TigerBody_HeightSource.png').convert('L')
    BODY=np.asarray(_body,np.float32)/255
    BODY_FORM=np.asarray(_body.filter(ImageFilter.GaussianBlur(4)),np.float32)/255
except ImportError:
    _body=bpy.data.images.load(str(P/'Ornament/TigerBody_HeightSource.png'));_body.colorspace_settings.name='Non-Color'
    _values=np.empty(_body.size[0]*_body.size[1]*4,np.float32);_body.pixels.foreach_get(_values)
    BODY=_values.reshape(_body.size[1],_body.size[0],4)[::-1,:,:3].mean(axis=2).copy()
    _radius=12;_weights=np.exp(-np.arange(-_radius,_radius+1,dtype=float)**2/(2*4**2));_weights/=_weights.sum()
    BODY_FORM=np.apply_along_axis(lambda a:np.convolve(np.pad(a,_radius,mode='edge'),_weights,mode='valid'),0,BODY)
    BODY_FORM=np.apply_along_axis(lambda a:np.convolve(np.pad(a,_radius,mode='edge'),_weights,mode='valid'),1,BODY_FORM)

def smooth(a,b,x):
    q=np.clip((x-a)/(b-a),0,1);return q*q*(3-2*q)

def sample(a,u,v):
    x=np.clip(u,0,1)*(a.shape[1]-1);y=np.clip(v,0,1)*(a.shape[0]-1)
    ix=np.floor(x).astype(int);iy=np.floor(y).astype(int)
    xx=np.minimum(ix+1,a.shape[1]-1);yy=np.minimum(iy+1,a.shape[0]-1)
    fx=x-ix;fy=y-iy
    return a[iy,ix]*(1-fx)*(1-fy)+a[iy,xx]*fx*(1-fy)+a[yy,ix]*(1-fx)*fy+a[yy,xx]*fx*fy

def face_height(u,v):
    h=sample(FORM,u,v)
    # The reference drives raised cheek curls and cut whisker channels.
    # Larger anatomical volumes are authored separately in the mesh.
    return .0032*smooth(.08,.88,h)

def body_field(u,v,form=False):
    # Bake three planar projections into the skull atlas. A direct polar wrap
    # stretches cloud scrolls along the flanks and pinches them at the rear.
    theta=(np.asarray(u)%1-.5)*np.pi*2;beta=(np.clip(v,0,1)-.5)*np.pi
    x=.044*np.cos(beta)*np.sin(theta);y=.004-.044*np.sin(beta);z=-.0015+.044*np.cos(beta)*np.cos(theta)
    nx=x/.044**2;ny=(y-.004)/.044**2;nz=(z+.0015)/.044**2
    wx=np.abs(nx)**6;wy=np.abs(ny)**6;wz=np.abs(nz)**6;total=wx+wy+wz
    source=BODY_FORM if form else BODY
    sx=sample(source,(y+.040)/.088,.5-(z+.0015)/.088)
    sy=sample(source,.5+x/.088,.5-(z+.0015)/.088)
    sz=sample(source,.5+x/.088,(y+.040)/.088)
    return (wx*sx+wy*sy+wz*sz)/np.maximum(total,1e-12)

def body_height(u,v):return .0016*smooth(.09,.83,body_field(u,v,True))

CLOUD=SOURCE[int(SOURCE.shape[0]*.26):int(SOURCE.shape[0]*.44),int(SOURCE.shape[1]*.065):int(SOURCE.shape[1]*.285)]
def cloud(u,v):return sample(CLOUD,np.asarray(u)%1,np.asarray(v)%1)

def connector_field(u,v,form=False):
    """Six separately framed cloud ornaments across a cylindrical sleeve."""
    phase=(np.asarray(u)*6)%1;v=np.clip(v,0,1)
    h=sample(BODY_FORM if form else BODY,.16+.68*phase,.28+.34*v)
    borders=smooth(0,.10,phase)*(1-smooth(.90,1,phase))*smooth(0,.10,v)*(1-smooth(.90,1,v))
    return smooth(.10,.85,h)*borders

def encode(a):return np.where(a<=.0031308,12.92*a,1.055*np.maximum(a,0)**(1/2.4)-.055)
def normals(h,width,height):
    dy,dx=np.gradient(h)
    nn=np.stack([-dx/(width/(h.shape[1]-1)),dy/(height/(h.shape[0]-1)),np.ones_like(h)],2)
    nn/=np.linalg.norm(nn,axis=2)[...,None];return nn*.5+.5

if __name__=='__main__':
    import sys,json
    from PIL import Image,ImageFilter
    (P/'Textures').mkdir(exist_ok=True)
    recipe={'route':'imagegen relief source + local Blender volumetric sculpt and precise interface',
            'face_geometry_relief_m':.0032,'head_width_m':.082,'head_height_m':.09,
            'families':{},'runtime_tested':False}
    families=[('BronzeFace',4096),('Gilt',2048),('Garnet',512),('Mouth',512),('ChasedBody',2048),('Connector',2048)]
    if '--connector-only' in sys.argv:
        recipe=json.loads((P/'surface_recipe.json').read_text(encoding='utf-8-sig'))
        families=[('Connector',2048)]
    for family,n in families:
        output={key:Image.new('RGB',(n,n)) for key in ['BaseColor','ORM','Normal']}
        if family=='BronzeFace':
            source=Image.fromarray((SOURCE*255).astype('uint8')).resize((n,n),Image.Resampling.LANCZOS)
            blurred_source=source.filter(ImageFilter.GaussianBlur(3))
        for row in range(0,n,256):
            end=min(n,row+256);low=max(0,row-1);high=min(n,end+1)
            u,v=np.meshgrid(np.linspace(0,1,n,dtype=np.float32),np.arange(low,high,dtype=np.float32)/(n-1))
            rng=np.random.default_rng(742+row);grain=rng.random(u.shape,dtype=np.float32)-.5
            if family in ['BronzeFace','ChasedBody']:
                if family=='ChasedBody':
                    lum=body_field(u,v);blurred=body_field(u,v,True)
                else:
                    lum=np.asarray(source.crop((0,low,n,high)),np.float32)/255
                    blurred=np.asarray(blurred_source.crop((0,low,n,high)),np.float32)/255
                ridges=smooth(.23,.78,lum)
                color=np.array([.42,.255,.115] if family=='BronzeFace' else [.34,.22,.10],np.float32)[None,None,:]*(.085+.915*ridges[...,None])
                rough=.47-.095*ridges+.008*grain;metal=np.ones_like(u)
                h=(.00045*(smooth(.09,.83,lum)-smooth(.09,.83,blurred)) if family=='ChasedBody' else (lum-blurred)*.000007)+grain*.0000007
                ao=.65+.35*smooth(.07,.42,lum)
                dy,dx=np.gradient(h);nn=np.stack([-dx/((.082 if family=='BronzeFace' else .23)/(n-1)),dy/((.09 if family=='BronzeFace' else .055)/(n-1)),np.ones_like(h)],2)
            elif family=='Connector':
                ridges=connector_field(u,v);blurred=connector_field(u,v,True)
                color=np.array([.36,.225,.10],np.float32)[None,None,:]*(.12+.88*ridges[...,None])
                rough=.45-.07*ridges+.008*grain;metal=np.ones_like(u)
                h=.00016*(ridges-blurred)+grain*.0000005;ao=.72+.28*ridges
                dy,dx=np.gradient(h);nn=np.stack([-dx/(.10/(n-1)),dy/(.008/(n-1)),np.ones_like(h)],2)
            elif family=='Gilt':
                relief=cloud(u*6,v);ridges=smooth(.20,.8,relief)
                color=np.array([.34,.21,.095],np.float32)[None,None,:]*(.72+.28*ridges[...,None])
                rough=.43-.045*ridges+.008*grain;metal=np.ones_like(u)
                h=grain*.00000035;ao=.93+.07*ridges
                dy,dx=np.gradient(h);nn=np.stack([-dx/(.20/(n-1)),dy/(.016/(n-1)),np.ones_like(h)],2)
            else:
                color=np.broadcast_to(np.array([.22,.004,.009] if family=='Garnet' else [.0045,.0028,.0022],np.float32),(*u.shape,3)).copy()
                rough=np.full_like(u,.16 if family=='Garnet' else .53);metal=np.zeros_like(u);ao=np.ones_like(u)*(1 if family=='Garnet' else .82)
                nn=np.broadcast_to(np.array([0,0,1.],np.float32),(*u.shape,3)).copy()
            nn/=np.linalg.norm(nn,axis=2)[...,None]
            maps={'BaseColor':encode(color),'ORM':np.stack([ao,rough,metal],2),'Normal':nn*.5+.5}
            for key,a in maps.items():
                a=a[row-low:end-low]
                output[key].paste(Image.fromarray(np.clip(a*255+.5,0,255).astype('uint8')),(0,row))
        for key,im in output.items():im.save(P/'Textures'/f'TangDao_TigerPommel_{family}_{key}.png')
        recipe['families'][family]={'resolution':n,'metallic':1 if family in ['BronzeFace','Gilt','ChasedBody','Connector'] else 0}
        print('TIGER_POMMEL_PBR '+family,flush=True)
    recipe['connector_revision']='SteppedSocketV4_20261003'
    recipe['connector_geometry_relief_mm']=.55
    (P/'surface_recipe.json').write_text(json.dumps(recipe,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
