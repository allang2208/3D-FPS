"""Authoring chart of source geometry; no posing or acceptance render."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]/'SourceAssets/InfectedDogMeshy20260924/LocalRig'
v=np.load(ROOT/'anatomy_source.npz')['vertices']
img=Image.new('RGB',(1650,1050),'#f0f0f0'); d=ImageDraw.Draw(img)
def panel(rect,a,b,title,subset=None):
    x,y,w,h=rect; arr=v if subset is None else v[subset]
    bounds=[(-.85,.85),(0,1.05)] if a==1 else [(-.3,.3),(0,1.05)]
    if b==1:bounds=[(-.3,.3),(-.85,.85)]
    lo,hi=bounds[0]; bot,top=bounds[1]
    def xy(p,q):return x+(p-lo)/(hi-lo)*w,y+h-(q-bot)/(top-bot)*h
    d.text((x,y-22),title,fill='black')
    for tick in np.arange(np.ceil(lo*10)/10,hi,.1):
        u,_=xy(tick,0);d.line((u,y,u,y+h),fill='#cccccc');d.text((u,y+h+3),f'{tick:.1f}',fill='black')
    for tick in np.arange(np.ceil(bot*10)/10,top,.1):
        _,z=xy(0,tick);d.line((x,z,x+w,z),fill='#cccccc');d.text((x-25,z),f'{tick:.1f}',fill='black')
    for p in arr:
        u,z=xy(p[a],p[b]);d.point((round(u),round(z)),fill='#26382e')
panel((50,40,900,940),1,2,'SIDE: horizontal Y (nose negative), vertical Z',v[:,0]>0)
panel((1010,40,260,940),0,2,'FRONT X/Z')
panel((1340,40,260,940),0,1,'TOP X/Y')
img.save(ROOT/'source_landmark_chart.png')
