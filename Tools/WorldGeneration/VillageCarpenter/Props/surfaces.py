"""Cross-cut timber and brushed pigment maps authored for the carpenter's props."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageCarpenter/Props/Authored'
OUT.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(171803)
def noise(nx,ny,w,h):
    src=Image.fromarray((rng.random((ny,nx))*255).astype('uint8'))
    return np.asarray(src.resize((w,h),Image.Resampling.BICUBIC),dtype=np.float32)/255
def save(name,data):
    Image.fromarray(np.uint8(np.clip(data,0,1)*255)).save(OUT/(name+'.png'))

n=1024
y,x=np.mgrid[0:n,0:n].astype(np.float32)/n
dx=(x-.476)*1.04;dy=(y-.512)*.97
theta=np.arctan2(dy,dx)
dist=np.sqrt(dx*dx+dy*dy)*(1+.017*np.sin(theta*3+.2)+.013*np.sin(theta*7-.7))
dist+=.014*(noise(9,10,n,n)-.5)
wave=np.cos(dist*2*np.pi*69+1.1*np.sin(dist*72))
late=np.clip((wave-.40)/.60,0,1)**1.4
micro=rng.normal(0,.018,(n,n));fibres=noise(509,686,n,n)
checking=np.zeros((n,n),dtype=np.float32)
for a,r0,r1 in [(-1.77,.11,.47),(.47,.29,.49),(2.32,.19,.46),(-.55,.35,.52)]:
    direction=theta-a-.035*np.sin(dist*37+a)
    checking+=np.clip(1-np.abs(direction)*dist/.0027,0,1)*np.clip((dist-r0)*80,0,1)*np.clip((r1-dist)*90,0,1)
checking=np.clip(checking,0,1)
saw=np.sin((x*.23+y)*1850+.9*noise(11,48,n,n))
height=.027*late+.01*saw+.08*fibres-.17*checking
grain=.83-.18*late+.15*noise(20,16,n,n)+micro-.50*checking
save('Cut_Color',grain[:,:,None]*[.65,.51,.347])
gy,gx=np.gradient(height);norm=np.sqrt(gx*gx+gy*gy+1)
save('Cut_Normal',np.stack((.5-gx/norm*.5,.5-gy/norm*.5,.5+.5/norm),axis=2))
save('Cut_ORM',np.stack((.95-.26*checking,.78+.13*fibres,np.zeros_like(height)),axis=2))

w,h=2048,768
im=Image.new('L',(w,h),0);draw=ImageDraw.Draw(im)
font=ImageFont.truetype('C:/Windows/Fonts/simkai.ttf',int(h*.48))
draw.text((w*.596,h*.50),'木工工坊',font=font,anchor='mm',fill=237)
# The stock of a hand plane, its tilted iron and shaving form the maker's mark.
draw.polygon([(125,416),(153,450),(406,450),(445,416),(441,392),(374,385),
              (346,367),(320,367),(309,388),(178,389),(165,373),(145,373)],fill=227)
draw.polygon([(255,387),(286,321),(307,326),(287,389)],fill=226)
draw.line([(156,456),(408,455)],fill=213,width=6)
draw.arc((303,305,389,386),193,418,fill=220,width=11)
draw.arc((321,324,372,370),191,426,fill=218,width=7)
alpha=np.asarray(im,dtype=np.float32)/255
wear=noise(640,248,w,h)*.64+noise(130,23,w,h)*.36
alpha*=np.clip((wear-.27)*3.5,0,1)
save('CarpenterPaint',alpha)
