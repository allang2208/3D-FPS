"""Authoring coordinate worksheet from input vertices/texture; no gameplay rendering."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent/'RigV1'
d=np.load(BASE/'source_geometry.npz');v=d['vertices'];uv=d['uv'];tex=np.asarray(Image.open(BASE/'BaseColor.png').convert('RGB'))
out=Image.new('RGB',(1600,820),(45,45,45));draw=ImageDraw.Draw(out)
ids=np.flatnonzero((v[:,0]>1.30)&(abs(v[:,1])<.85)&(v[:,2]<.85))
ids=ids[np.argsort(v[ids,0])]
for variant in range(2):
    for i in ids:
        p=v[i];x=int((p[1]+.85)*800/1.7)+variant*800;y=int((.85-p[2])*800/.85)
        vv=uv[i,1] if variant==0 else 1-uv[i,1]
        color=tuple(tex[int(np.clip(vv*tex.shape[0],0,tex.shape[0]-1)),int(np.clip(uv[i,0]*tex.shape[1],0,tex.shape[1]-1))])
        draw.ellipse((x-2,y-2,x+2,y+2),fill=color)
    for gy in np.arange(-.8,.81,.1):
        xx=int((gy+.85)*800/1.7)+variant*800;draw.line((xx,0,xx,800),fill=(70,70,70),width=1);draw.text((xx+1,802),f'{gy:.1f}',fill='white')
    for gz in np.arange(.1,.81,.1):
        yy=int((.85-gz)*800/.85);draw.line((variant*800,yy,(variant+1)*800,yy),fill=(70,70,70),width=1);draw.text((variant*800,yy),f'z{gz:.1f}',fill='white')
out.save(ROOT/'eye_authoring_coordinates.png')
print('Authoring worksheet saved')
