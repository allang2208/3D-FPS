"""Physical-scale woven surface fields for the approved charcoal sports cap."""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

P = Path(__file__).resolve().parents[2]
R = P / 'SourceAssets/SportsCap20261024'
T = R / 'Textures'
T.mkdir(parents=True, exist_ok=True)
rng = np.random.default_rng(20261024)


def png(path, data):
    Image.fromarray(np.uint8(np.clip(data, 0, 1)*255+.5)).save(path)


def field(name, n, span, color, rough, kind):
    y, x = np.mgrid[:n, :n].astype('f')/n
    grain = gaussian_filter(rng.normal(size=(n,n)).astype('f'), .65, mode='wrap')
    grain /= grain.std()
    cloud = gaussian_filter(grain, 18, mode='wrap'); cloud /= cloud.std()
    count = {'nylon':112,'lining':96,'webbing':88,'rubber':48,'reflective':128}[kind]
    warp, weft = np.cos(2*np.pi*count*x), np.cos(2*np.pi*count*y)
    if kind == 'webbing':
        relief = .000022*(.70*warp+.24*weft+.08*grain)
        variation = .04*warp+.02*weft+.018*cloud
    elif kind == 'rubber':
        relief = .000006*grain+.000002*cloud
        variation = .014*grain+.015*cloud
    elif kind == 'reflective':
        relief = .000004*(warp*weft+.15*grain)
        variation = .025*warp*weft+.01*cloud
    else:
        checker = np.cos(np.pi*(np.floor(x*count)+np.floor(y*count)))
        relief = .000018*(.48*(warp+weft)+.24*checker*(warp-weft)+.08*grain)
        variation = .026*(warp+weft)+.014*grain+.025*cloud
    color_field = np.array(color)[None,None,:]*(1+variation[...,None])
    dx=(np.roll(relief,-1,1)-np.roll(relief,1,1))/(2*span/n)
    dy=(np.roll(relief,-1,0)-np.roll(relief,1,0))/(2*span/n)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    png(T/f'T_{name}_BaseColor.png', color_field)
    png(T/f'T_{name}_Normal.png', normal*.5+.5)
    png(T/f'T_{name}_ORM.png', np.stack((np.clip(1-np.maximum(-grain,0)*.012,.93,1),np.clip(rough+.024*grain+.017*cloud,.25,.94),np.zeros_like(x)),axis=-1))
    amplitude=float(np.max(np.abs(relief)))
    Image.fromarray(np.uint16((np.clip(relief/(2*amplitude)+.5,0,1)*65535).round())).save(T/f'T_{name}_Height.png')
    np.savez_compressed(T/f'HIGH_{name}_SurfaceField.npz',height_m=relief,tile_m=span)
    return dict(name=name,resolution=n,tile_m=span,height_range_m=[-amplitude,amplitude],normal_convention='OpenGL',height_source='original woven surface field',kind=kind)


rows=[field('Cap_CharcoalNylon',2048,.04,[.19,.20,.215],.77,'nylon'),
      field('Cap_SmokeVentNylon',2048,.04,[.22,.235,.25],.80,'nylon'),
      field('Cap_BlackSweatband',1024,.04,[.065,.073,.084],.89,'lining'),
      field('Cap_BlackWebbing',1024,.04,[.064,.067,.074],.74,'webbing'),
      field('Cap_BlackPolymer',1024,.04,[.055,.059,.066],.48,'rubber'),
      field('Cap_CyanBinding',1024,.04,[.045,.53,.76],.65,'nylon'),
      field('Cap_ReflectiveTape',512,.02,[.58,.60,.62],.38,'reflective')]
(R/'textures.json').write_text(json.dumps(dict(completed=True,original_procedural_sources=True,maps=rows,texture_streaming_required=True,ue_normal_flip_green=True),indent=2)+'\n',encoding='utf-8')
print('SPORTS_CAP_SURFACES',len(rows)*4,'maps',flush=True)
