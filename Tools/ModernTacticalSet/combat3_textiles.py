"""Production PBR: photographic weave, calibrated height, ripstop reinforcement."""
import json,numpy as np
from PIL import Image
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3');sources=json.loads((R/'Sources/textiles.json').read_text());size=2048;tile_cm=28.8;out={}
def linear(v):return np.where(v<=.04045,v/12.92,((v+.055)/1.055)**2.4)
def srgb(v):return np.where(v<=.0031308,v*12.92,1.055*np.maximum(v,0)**(1/2.4)-.055)
def load(asset,channel,mode):return np.array(Image.open(sources[asset]['files'][channel]['file']).convert(mode).resize((size,size))).astype('float64')
for name,asset,tint,reinforce in [('CombatRipstop','stretch_poplin',[132,102,69],True),('CombatCarrier','stretch_poplin',[111,83,54],True),('CombatStretch','bi_stretch',[76,56,39],False),('CombatCuff','bi_stretch',[96,71,48],False),('CombatLining','bi_stretch',[53,40,29],False),('CombatThread','stretch_poplin',[149,116,78],False)]:
    colour=linear(load(asset,'Diffuse','RGB')/255);luma=colour@np.array([.2126,.7152,.0722]);dye=luma/max(float(luma.mean()),1e-8);base=dye[:,:,None]*linear(np.array(tint)/255)
    normal=load(asset,'nor_gl','RGB')/127.5-1;normal[:,:,0:2]*=.8;normal/=np.maximum(np.linalg.norm(normal,axis=2,keepdims=True),1e-8);arm=load(asset,'arm','RGB')/255
    original=Image.open(sources[asset]['files']['Displacement']['file']);height=np.array(original.resize((size,size)),dtype='float64');height=(height-height.min())/max(float(height.max()-height.min()),1e-8);dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*tile_cm/size);slope=-normal[:,:,0]/np.maximum(normal[:,:,2],.25);scale=float(np.clip(abs(np.sum(dx*slope)/max(np.sum(dx*dx),1e-8)),.003,.04));height=(height-.5)*scale
    grid=np.zeros((size,size))
    if reinforce:
        y,x=np.mgrid[:size,:size]*tile_cm/size
        for axis in [x,y]:
            phase=(axis+.3)%.6-.3
            for shift in [-.025,.025]:grid+=np.exp(-((phase-shift)/.014)**2)
        grain=.8+.2*dye;extra=grid*.0045*grain;height+=extra;gx=(np.roll(extra,-1,1)-np.roll(extra,1,1))/(2*tile_cm/size);gy=(np.roll(extra,-1,0)-np.roll(extra,1,0))/(2*tile_cm/size);normal[:,:,0]-=gx;normal[:,:,1]+=gy;normal/=np.linalg.norm(normal,axis=2,keepdims=True);base*=1+.028*grid[:,:,None]
    arm[:,:,1]=np.clip(.61+.27*arm[:,:,1]+.025*grid,.64,.93);arm[:,:,2]=0
    for channel,values in [('BaseColor',np.clip(srgb(base),0,1)),('NormalGL',normal*.5+.5),('ORM',arm)]:Image.fromarray(np.round(np.clip(values,0,1)*255).astype('uint8')).save(R/'Textures'/(name+'_'+channel+'.png'))
    np.savez_compressed(R/'Bakes'/(name+'_height_field.npz'),height_cm=height.astype('float32'),tile_cm=tile_cm)
    out[name]=dict(source=asset,license='CC0',page=sources[asset]['page'],tile_cm=tile_cm,resolution=size,uv_multiplier=8/tile_cm,height_scale_cm=scale,reinforcement_pitch_cm=.6 if reinforce else None,method='Photographic weave maps; height calibration against supplied normal; paired ripstop yarn field; matte Cloth shading with fuzz')
(R/'Bakes/textile-fields.json').write_text(json.dumps(out,indent=2));print('TS01_R3_PHOTOGRAPHIC_CLOTH',len(out),flush=True)
