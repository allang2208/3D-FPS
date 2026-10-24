"""Tileable authored material relief and original low-level ambience loops."""
from pathlib import Path
import numpy as np,json,wave,runpy
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter
R=Path(__file__).resolve().parent;O=R/'Textures';O.mkdir(exist_ok=True)
rng=np.random.default_rng(221007);n=1024;y,x=np.mgrid[:n,:n].astype(float)/n
def save_surface(name,h,color,rough,metal=0,strength=1):
 dy,dx=np.gradient(h);v=np.stack([-dx*strength,dy*strength,np.ones_like(h)],-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
 Image.fromarray(np.uint8(np.clip(v*.5+.5,0,1)*255)).save(O/f'T_AP7_{name}_N.png')
 c=np.broadcast_to(np.array(color)[None,None,:],(n,n,3))*np.clip(.85+h[:,:,None]*.3,.65,1.2)
 c=np.clip(c,0,1);c=np.where(c<=.0031308,c*12.92,1.055*c**(1/2.4)-.055)
 Image.fromarray(np.uint8(c*255)).save(O/f'T_AP7_{name}_BC.png')
 orm=np.stack([np.clip(.75+h*.25,0,1),np.clip(rough+(.5-h)*.12,0,1),np.full_like(h,metal)],-1)
 Image.fromarray(np.uint8(orm*255)).save(O/f'T_AP7_{name}_ORM.png')
# Interlocked towel loops rather than a generic linen weave.
u=x*64;v=y*64;rad=np.sqrt(((u%1)-.5)**2+(((v+(np.floor(u)%2)*.5)%1)-.5)**2)
terry=np.exp(-((rad-.27)/.09)**2)*.7+gaussian_filter(rng.random((n,n)),.7,mode='wrap')*.15
save_surface('Terry',terry,(.45,.47,.48),.91,strength=3.2)
soil=gaussian_filter(rng.random((n,n)),3,mode='wrap');soil=(soil-soil.min())/(soil.max()-soil.min())
soil=.65*soil+.35*gaussian_filter(rng.random((n,n)),.65,mode='wrap')
save_surface('Soil',soil,(.045,.032,.022),.93,strength=5)
# Laser marks / shallow panel machining are a shared 0.4 m physical repeat.
h=np.full((n,n),.50);rough=np.full((n,n),.48)
im=Image.new('L',(n,n),128);d=ImageDraw.Draw(im)
for k in range(12):
 yy=60+k*78;d.rounded_rectangle((42,yy,982,yy+3),radius=1,fill=112)
for xx in [32,992]:
 for yy in [32,992]:d.ellipse((xx-8,yy-8,xx+8,yy+8),fill=110)
save_surface('Machined',np.asarray(im)/255,(.042,.05,.063),.46,metal=.65,strength=3)

# Revised six facade families share layout dimensions with the existing geometry.
# Independent illumination masks preserve dark windows and block occupancy.
for idx,name in enumerate(['Corporate','Financial','Housing','Terraces','Data','Harbor']):
 size=2048;bc=Image.new('RGB',(size,size),(21,28,36));em=Image.new('RGB',(size,size));hh=Image.new('L',(size,size),150);orm=Image.new('RGB',(size,size),(245,158,90))
 b,e,d,q=[ImageDraw.Draw(z) for z in [bc,em,hh,orm]]
 rr=np.random.default_rng(700+idx)
 for row in range(32):
  for col in range(24):
   x0=round(col*size/24);x1=round((col+1)*size/24);y0=row*64
   warm=idx in [2,3,5];panel=(29,33,37) if warm else (22,32,43)
   b.rectangle((x0+1,y0+1,x1-1,y0+63),fill=panel)
   inset=12 if warm else 7;z=(x0+inset,y0+9,x1-inset,y0+48)
   b.rectangle(z,fill=(8,15,22));d.rectangle(z,fill=65);q.rectangle(z,fill=(220,53,170))
   b.rectangle(z,outline=(53,57,61),width=2);d.rectangle(z,outline=175,width=3)
   # Office partitions / terrace recesses / data-centre louvres are distinct.
   if idx==4:
    for line in range(y0+13,y0+47,6):b.line((z[0],line,z[2],line),fill=(60,66,75),width=2);d.line((z[0],line,z[2],line),fill=190,width=2)
   elif idx==3:
    b.rectangle((x0+2,y0+49,x1-2,y0+57),fill=(34,46,40));d.rectangle((x0+2,y0+49,x1-2,y0+57),fill=200)
   if rr.random()<(.48 if warm else .62) and not (idx==4 and col%4==3):
    tone=np.array((223,168,105) if warm else (139,184,205))*rr.uniform(.45,.95)
    if idx==4:tone=np.array((66,153,175))*rr.uniform(.35,.8)
    e.rectangle((z[0]+4,z[1]+4,z[2]-4,z[3]-4),fill=tuple(tone.astype(int)))
    for off in [int((x0+x1)/2)]:e.line((off,z[1],off,z[3]),fill=(0,0,0),width=3)
    if rr.random()<.32:
     for line in range(y0+18,y0+46,7):e.line((z[0],line,z[2],line),fill=tuple((tone*.2).astype(int)),width=2)
   if col%[3,4,2,3,4,2][idx]==0:
    b.rectangle((x0+1,y0,x0+4,y0+63),fill=(65,63,57) if idx==1 else (46,54,65));d.rectangle((x0+1,y0,x0+4,y0+63),fill=210)
 for suffix,img in [('BC',bc),('E',em),('ORM',orm)]:img.save(O/f'T_AP7_{name}_{suffix}.png')
 height=np.asarray(hh,dtype=float)/255;dy,dx=np.gradient(height);norm=np.stack([-dx*2.2,dy*2.2,np.ones_like(height)],-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
 Image.fromarray(np.uint8((norm*.5+.5)*255)).save(O/f'T_AP7_{name}_N.png')

font='C:/Windows/Fonts/consola.ttf'
for name in ['OfficeUI','WorkoutUI']:
 # Reuse existing approved device artwork; change the small status footer only.
 im=Image.open(R.parent/'RefinementV3/Textures'/('T_AP_'+name+'.png')).convert('RGB');d=ImageDraw.Draw(im)
 d.rectangle((36,790,1490,831),fill=(8,13,20));d.text((55,799),'AUTO WAKE  /  LOCAL LINK  /  STANDBY WHEN AWAY',font=ImageFont.truetype(font,20),fill=(84,137,151))
 im.save(O/f'T_AP7_{name}_BC.png')

# Original, seamless procedural room ventilation, electronics and distant harbor.
# No audition or external audio download; no rain layer (UDW already owns rain).
audio=R/'Audio';audio.mkdir(exist_ok=True);rate=48000;seconds=24;count=rate*seconds;t=np.arange(count)/rate
def band_noise(low,high,seed):
 rr=np.random.default_rng(seed);freq=np.fft.rfftfreq(count,1/rate);z=rr.normal(size=len(freq))+1j*rr.normal(size=len(freq))
 mask=(1-np.exp(-(freq/max(low,1))**4))*np.exp(-(freq/high)**4);a=np.fft.irfft(z*mask,n=count);return a/max(np.std(a),1e-9)
for name in ['Ventilation','Electronics','Harbor']:
 if name=='Ventilation':a=.12*band_noise(55,900,17)+.045*np.sin(2*np.pi*96*t)+.024*np.sin(2*np.pi*192*t)
 elif name=='Electronics':a=.06*band_noise(160,1400,19)+.04*np.sin(2*np.pi*144*t)*(1+.1*np.sin(2*np.pi*t/6))
 else:
  a=.10*band_noise(45,450,23)*(1+.2*np.sin(2*np.pi*t/12))+.045*band_noise(600,1500,24)
  a+=.018*np.sin(2*np.pi*137*t)*(np.sin(2*np.pi*t/24)*.5+.5)**6
 a=np.tanh(a*.8)*.65;st=np.stack([a,np.roll(a,139 if name=='Harbor' else 31)],-1)
 with wave.open(str(audio/f'S_AP7_{name}.wav'),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(rate);w.writeframes(np.int16(st*32767).tobytes())
(R/'surface-source.json').write_text(json.dumps(dict(stage='authored',normal_convention='DirectX',textures='Original relief masters + existing device UI + retained library PBR',audio='Original periodic synthesis, 48 kHz stereo, 24 s seamless loops',auditioned=False),indent=2),encoding='utf8')
print('AP7_SURFACES_AUDIO_AUTHORED')
