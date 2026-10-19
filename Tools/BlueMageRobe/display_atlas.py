"""Bake the production skirt shader into an atlas for Blender inventory rendering."""
import json,numpy as np
from PIL import Image
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018');T=R/'Textures';length=json.loads((R/'Authored/Body/Jason.json').read_text())['cloth_dimensions']['length_cm']
size=2048;v,u=np.mgrid[0:size,0:size].astype(np.float32)/size;circ=90+115*v;arc=np.minimum(np.abs((u+.5)%1-.5),np.abs(u-.5))*circ;hemcm=(1-v)*length
def smooth(a,b,x):t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
hem=1-smooth(3.4,3.65,hemcm);rails=(1-smooth(.34,.44,np.abs(arc-1.5)))*smooth(0,.025,v);trim=np.maximum(hem,rails)[...,None];tu=np.where(hem>rails,u*circ/44,v*length/22);tv=np.where(hem>rails,np.clip(hemcm/3.5,0,1),np.clip((arc-1.1)/.8,0,1))
def sample(family,channel,x,y,clamp=False):
    a=np.asarray(Image.open(T/('T_'+family+'_'+channel+'.png')).convert('RGB')).astype(np.float32)/255;hh,ww=a.shape[:2];ix=np.floor((x%1)*ww).astype(int);iy=np.minimum(hh-1,np.floor((np.clip(y,0,1) if clamp else y%1)*hh).astype(int));return a[iy,ix]
for channel in ('BaseColor','Normal','ORM'):
    fabric=sample('BlueMageFabric',channel,u*circ/4,(1-v)*length/4);thread=sample('BlueMageEmbroidery',channel,tu,tv,True);result=fabric*(1-trim)+thread*trim
    if channel=='BaseColor':result*=1-.38*((1-smooth(.65,.95,arc))*smooth(.02,.10,v))[...,None]
    Image.fromarray(np.uint8(np.clip(result,0,1)*255)).save(T/('T_BlueMageSkirtDisplay_'+channel+'.png'))
print('BLUE_ROBE_ICON_SHADER_ATLAS_SAVED')
