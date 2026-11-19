"""Build calibrated workwear surfaces from three original material captures."""
import json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit'
TEX=OUT/'Textures'
SOURCE=OUT/'Sources'
TEX.mkdir(parents=True,exist_ok=True)
SETTINGS={
    # Display-space albedo, base microsurface roughness, texture size and relative grain scale
    'Linen':('indigo_linen',(55,54,62),.84,2048,1),
    'Twill':('coal_twill',(49,46,45),.82,1024,3),
    'Apron':('apron_leather',(73,46,31),.65,2048,1),
    'Saddle':('apron_leather',(54,34,25),.48,1024,1),
    'Boot':('apron_leather',(49,35,30),.52,1024,2)
}
def smoothstep(a,b,x):
    t=np.clip((x-a)/(b-a),0,1)
    return t*t*(3-2*t)
def gauss(x,sigma):
    return gaussian_filter(x,sigma,mode='wrap')
def write(name,rgb):
    Image.fromarray(np.clip(np.rint(rgb),0,255).astype('uint8')).save(TEX/name)
def noise(rng,size,frequency):
    small=rng.normal(size=(frequency,frequency)).astype('float32')
    yy,xx=np.mgrid[:size,:size].astype('float32')*(frequency/size)
    data=cv2.remap(small,xx,yy,cv2.INTER_CUBIC,borderMode=cv2.BORDER_WRAP)
    return (data-data.mean())/max(data.std(),1e-7)
def seamless(filename):
    im=np.asarray(Image.open(filename).convert('RGB'),dtype=np.float32)
    # Crossfade only the square's opposite selvages through actual overlapping samples.
    overlap=70
    side=min(im.shape[:2])-overlap
    blend=smoothstep(0,overlap-1,np.arange(overlap)).astype('float32')
    horizontal=im[:,:side].copy()
    horizontal[:,:overlap]=im[:,side:side+overlap]*(1-blend[None,:,None])+im[:,:overlap]*blend[None,:,None]
    tile=horizontal[:side].copy()
    tile[:overlap]=horizontal[side:side+overlap]*(1-blend[:,None,None])+horizontal[:overlap]*blend[:,None,None]
    return tile
def sample(name,size,repeat,index):
    src=seamless(SOURCE/(name+'.png')); h=src.shape[0]
    yy,xx=np.mgrid[:size,:size].astype('float32');py=yy/size*2*np.pi;px=xx/size*2*np.pi
    u=xx*(h*repeat/size)+index*119
    v=yy*(h*repeat/size)+index*71
    if name=='apron_leather':
        u+=np.sin(2*py+.5)*9+np.sin(px+py)*6
        v+=np.sin(2*px)*10+np.sin(2*py-px)*3
    if repeat>1:src=gauss(src,(.34,.34,0))
    return cv2.remap(src,u,v,cv2.INTER_CUBIC,borderMode=cv2.BORDER_WRAP)
def normals(height,steepness):
    # The source is indexed down the image. Store the tangent normal in DirectX convention.
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.5*steepness
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.5*steepness
    n=np.stack([-dx,-dy,np.ones_like(dx)],axis=2)
    n/=np.linalg.norm(n,axis=2)[:,:,None]
    return 127.5*(n+1)
for index,(slot,(source,base,roughness,size,repeat)) in enumerate(SETTINGS.items()):
    rng=np.random.default_rng(540+index)
    im=sample(source,size,repeat,index)
    lum=np.maximum(im@np.array([.2126,.7152,.0722],dtype='float32'),3)
    # Retain the colour variation specific to raised yarns and leather grain; remove baked light.
    loglum=np.log(lum+11);loglum-=np.mean(loglum)
    local=gauss(loglum,2.0);middle=gauss(loglum,9.0)
    large=noise(rng,size,7);small=noise(rng,size,28)
    raw_chroma=(im-lum[:,:,None]);raw_chroma-=np.median(raw_chroma.reshape(-1,3),axis=0)
    cloth=slot in ('Linen','Twill')
    if cloth:
        light=.45*loglum+.05*middle+.030*large+.009*small
        height=3.1*(loglum-local)+1.85*(local-middle)+.30*middle
        rough=roughness-.10*local+.035*large+.013*small
        wear=smoothstep(.035,.34,local+.022*large)
        col=np.asarray(base)*np.exp(light[:,:,None])+np.array([3.5,2.9,2.2])*wear[:,:,None]+raw_chroma*.095
        ao=np.clip(.965+.10*(loglum-middle),.83,1)
        steepness=.96 if slot=='Linen' else .76
    else:
        oil=smoothstep(.00,1.8,-large*.8-middle*1.2)
        rub=smoothstep(.04,.36,local+.055*large)
        light=.60*loglum+.11*(local-middle)+.045*large-.065*oil
        col=np.asarray(base)*np.exp(light[:,:,None])+np.array([9.,6.,2.8])*rub[:,:,None]+.13*raw_chroma
        height=2.5*(loglum-local)+1.75*(local-middle)+.46*middle
        rough=roughness-.11*rub-.12*oil+.032*small
        ao=np.clip(.971+.095*(loglum-middle),.78,1)
        steepness={'Apron':1.21,'Saddle':.70,'Boot':.9}[slot]
    tag='T_Smith_'+slot+'_'
    write(tag+'BC.png',col)
    write(tag+'N.png',normals(height,steepness))
    write(tag+'ORM.png',255*np.stack([ao,np.clip(rough,.26,.98),np.zeros_like(ao)],axis=2))
# A separate, non-repeating contact map is located in centimetres on the front apron.
# R: ochre abrasion, G: greasy tool-side polish, B: dry charcoal and dust. All linear.
h,w=2048,1024
y,x=np.mgrid[:h,:w].astype('float32');x=(x/(w-1)*2-1);v=1-y/(h-1)
rng=np.random.default_rng(172)
def grain(f):
    a=rng.normal(size=(int(f*1.5),f)).astype('float32')
    a=cv2.resize(a,(w,h),interpolation=cv2.INTER_CUBIC)
    return a/max(a.std(),.001)
large=grain(6);soft=grain(27);fine=grain(116);speck=grain(440)
def burn(cx,cv,rx,rv,lean):
    return np.exp(-(((x-cx-(v-cv)*lean)/rx)**2+((v-cv)/rv)**2)*1.3)
rub=burn(-.36,.57,.57,.19,.8)*.67+burn(.33,.91,.41,.14,-.65)*.40+burn(-.30,.20,.34,.14,-.85)*.37
oil=burn(.58,.57,.31,.22,.55)*.92+burn(.25,.36,.26,.21,-.40)*.50
soot=burn(.0,.76,.66,.15,-.38)*.51+burn(-.61,.32,.25,.23,.6)*.58
bleed=1+.23*large+.18*soft+.12*fine
edge=(1-smoothstep(0,.032,1-np.abs(x)))*(.21+.095*soft)
rub=np.clip(rub*bleed*(.52+.44*smoothstep(-.25,1.10,fine+.3*speck))+edge,0,1)
oil=np.clip(oil*(.69+.10*large+.11*soft+.075*fine),0,1)
soot=np.clip(soot*(.54+.16*large+.14*soft+.09*fine),0,1)
write('T_Smith_Apron_Contact.png',255*np.stack([rub,oil,soot],2))
settings={'upgraded':list(SETTINGS),'reuse':['Brass','Thread','Sole'],'normal_format':'DirectX','surface_inputs':'Original image-generated colour plates. Height, normal, roughness and occlusion art-directed from aligned grain.','original_uv':True,'apron_contact':{'position_cm':'pre-skinned x,z','u':'0.5 + x/37.0','v':'(136.2-z)/81.0','wear_rgb_lift_linear':[.086,.045,.017],'oil_darkening':.39,'soot_darkening':.35,'rough_adjust':[.09,-.24,.14]},'specular':{'Linen':.26,'Twill':.28,'Saddle':.47,'Apron':.43,'Boot':.45},'size':{k:v[3] for k,v in SETTINGS.items()}}
(OUT/'material_settings.json').write_text(json.dumps(settings,indent=2))
