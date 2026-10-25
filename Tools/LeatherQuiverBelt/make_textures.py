"""Physical-scale leather, suede and brass surfaces for the editable model."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt

R=Path(__file__).resolve().parents[2]/'SourceAssets/LeatherQuiverBelt20261025'
T=R/'Textures';T.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(2026102503)
def png(path,a):Image.fromarray(np.uint8(np.clip(a,0,1)*255+.5)).save(path)
def srgb(a):return np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
def field(name,color,rough,metal,kind,n=2048):
    span=.04
    noise=gaussian_filter(rng.normal(size=(n,n)).astype('f'),1.3,mode='wrap');noise/=noise.std()
    cloud=gaussian_filter(noise,35,mode='wrap');cloud/=cloud.std()
    if kind=='leather':
        seeds=rng.random((n,n))>.0028
        d,idx=distance_transform_edt(np.pad(seeds,64,mode='wrap'),return_indices=True)
        labels=idx[0]*idx.shape[2]+idx[1]
        edge=(labels!=np.roll(labels,1,0))|(labels!=np.roll(labels,1,1))
        edge=gaussian_filter(edge.astype('f'),1.8)[64:-64,64:-64]
        dome=gaussian_filter(d[64:-64,64:-64].astype('f'),3,mode='wrap');dome/=max(dome.max(),1)
        pores=gaussian_filter((rng.random((n,n))<.002).astype('f'),1.0,mode='wrap')
        h=.000026*dome-.000050*edge+.000003*noise-.00004*pores
        variation=.035*cloud+.012*noise-.055*edge
    elif kind=='suede':
        fibers=gaussian_filter(noise,(.7,3.2),mode='wrap');fibers/=fibers.std()
        h=.000006*fibers+.000003*noise;variation=.055*cloud+.055*fibers
    elif kind=='edge':
        lines=gaussian_filter(noise,(1.0,12),mode='wrap');lines/=lines.std()
        h=.000003*lines+.000002*noise;variation=.06*cloud+.025*lines
    else:
        brush=gaussian_filter(noise,(.6,20),mode='wrap');brush/=brush.std()
        h=.0000015*brush+.000001*noise;variation=.055*cloud+.025*brush
    h=gaussian_filter(h,.9,mode='wrap')
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*span/n)
    dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*span/n)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    base=np.array(color)[None,None,:]*np.clip(1+variation[...,None],.55,1.5)
    roughness=np.clip(rough+.045*cloud+.015*noise,.20,.98)
    metallic=np.clip(metal-.08*np.maximum(cloud-.5,0),0,1) if metal else np.zeros_like(noise)
    png(T/f'T_{name}_BaseColor.png',srgb(base))
    png(T/f'T_{name}_Normal.png',normal*.5+.5)
    png(T/f'T_{name}_ORM.png',np.stack((np.clip(1-np.maximum(-h,0)*1200,.92,1),roughness,metallic),axis=-1))
    limit=float(np.max(np.abs(h)));Image.fromarray(np.uint16(np.clip(h/(2*limit)+.5,0,1)*65535)).save(T/f'T_{name}_Height.png')
    np.savez_compressed(T/f'HIGH_{name}.npz',height_m=h,span_m=span)
    return dict(name=name,resolution=n,tile_m=span,height_range_m=[-limit,limit],kind=kind,base_linear=color,normal_convention='OpenGL')
rows=[field('Leather_Chestnut',[.067,.024,.010],.57,0,'leather'),
      field('Leather_BurnishedEdge',[.067,.024,.011],.36,0,'edge',1024),
      field('Leather_Suede',[.037,.016,.007],.96,0,'suede'),
      field('Metal_AgedBrass',[.43,.265,.095],.36,.93,'metal'),
      field('Metal_OxidizedBrass',[.16,.095,.038],.48,.84,'metal',1024),
      field('Leather_Reinforcement',[.042,.013,.005],.59,0,'leather')]
(R/'textures.json').write_text(json.dumps(dict(completed=True,maps=rows,physical_sources=True,ue_flip_normal_green=True,base_color_encoding='linear albedo converted once to sRGB'),indent=2)+'\n',encoding='utf-8')
print('LEATHER_SURFACES_SAVED',len(rows)*4,flush=True)
