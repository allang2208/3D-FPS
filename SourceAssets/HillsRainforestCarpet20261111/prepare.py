"""Pack the Fab grass PBR maps and three compact models from its GLTF."""
import json
import struct
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Prepared'
OUT.mkdir(exist_ok=True)
source = ROOT / 'GreenSward'

def ground(kind):
    return Image.open(next(source.glob('*_2K_' + kind + '.jpg')))

ground('Normal').save(OUT/'T_LivingGrass_Normal.png')
# Balance the scan's olive/straw tones against the living tuft atlas. Retain
# measured luminance and variation between individual blades.
rgb=np.asarray(ground('BaseColor').convert('RGB'),dtype=np.float32)/255
linear=np.where(rgb<=.04045,rgb/12.92,((rgb+.055)/1.055)**2.4)
graded=linear*np.array([.72,1.20,1.08],dtype=np.float32)
luma=np.array([.2126,.7152,.0722],dtype=np.float32)
graded*=(linear@luma/np.maximum(graded@luma,1.e-6))[...,None]
srgb=np.where(graded<=.0031308,graded*12.92,1.055*np.maximum(graded,0)**(1/2.4)-.055)
Image.fromarray(np.uint8(np.clip(srgb,0,1)*255+.5)).save(OUT/'T_LivingGrass_BaseColor.png')
height = np.array(ground('Displacement').convert('L'), dtype=float)
lo, hi = np.percentile(height, [1, 99])
height = Image.fromarray((255 * np.clip((height-lo)/max(hi-lo,1),0,1)).astype('uint8'))
Image.merge('RGB', (ground('AO').convert('L'), ground('Roughness').convert('L'), height)).save(OUT/'T_LivingGrass_ARH.png')

plant = ROOT/'WildTufts'
atlas = next((plant/'Textures').glob('*_1K_B-O.png'))
Image.open(atlas).save(OUT/'T_WildTuft_ColorOpacity.png')
doc = json.loads(next(plant.glob('*.gltf')).read_text())
buf = (plant/doc['buffers'][0]['uri']).read_bytes()

def accessor(index):
    a = doc['accessors'][index]
    view = doc['bufferViews'][a['bufferView']]
    num = {'SCALAR':1,'VEC2':2,'VEC3':3}[a['type']]
    dtype = np.dtype({5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']])
    offset = view.get('byteOffset',0) + a.get('byteOffset',0)
    stride = view.get('byteStride',dtype.itemsize*num)
    return np.ndarray((a['count'],num),dtype,buffer=buf,offset=offset,strides=(stride,dtype.itemsize)).copy()

def make_tuft(variant, width, height_m):
    name = 'SM_WetGrass_' + variant
    source_node = next(n for n in doc['nodes'] if n['name'].endswith('Var'+variant+'_LOD1'))
    prim = doc['meshes'][source_node['mesh']]['primitives'][0]
    # Quixel's node rotates +90 degrees about X. Bake that rotation and the
    # centimetre-to-metre conversion so each exported glTF has an identity root.
    pos = accessor(prim['attributes']['POSITION'])[:,[0,2,1]].copy()
    pos[:,1] *= -1
    low, high = pos.min(0), pos.max(0)
    pos -= [(low[0]+high[0])*.5,low[1],(low[2]+high[2])*.5]
    pos[:,[0,2]] *= width/max(high[0]-low[0],high[2]-low[2])
    pos[:,1] *= height_m/(high[1]-low[1])
    uv = accessor(prim['attributes']['TEXCOORD_0'])
    indices = accessor(prim['indices']).astype('<u2')
    # Up-biased foliage normals retain leaf lighting on two-sided blade cards.
    norms = np.column_stack((pos[:,0],np.full(len(pos),.48),pos[:,2]))
    norms /= np.linalg.norm(norms,axis=1)[:,None]
    tip = np.column_stack((np.clip(pos[:,1]/height_m,0,1),np.zeros(len(pos))))
    data = bytearray()
    views, accessors = [], []
    def add(array,shape,dtype,ctype,target,is_position=False):
        data.extend(b'\x00' * (-len(data)%4))
        chunk=array.astype(dtype).tobytes()
        views.append({'buffer':0,'byteOffset':len(data),'byteLength':len(chunk),'target':target})
        data.extend(chunk)
        a={'bufferView':len(views)-1,'componentType':ctype,'count':len(array),'type':shape}
        if is_position:a.update(min=array.min(0).tolist(),max=array.max(0).tolist())
        accessors.append(a)
        return len(accessors)-1
    attr={'POSITION':add(pos,'VEC3','<f4',5126,34962,True),'NORMAL':add(norms,'VEC3','<f4',5126,34962),
          'TEXCOORD_0':add(uv,'VEC2','<f4',5126,34962),'TEXCOORD_1':add(tip,'VEC2','<f4',5126,34962)}
    idx=add(indices,'SCALAR','<u2',5123,34963)
    data.extend(b'\x00'*(-len(data)%4))
    gltf={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],
          'nodes':[{'name':name,'mesh':0}],'meshes':[{'name':name,'primitives':[{'attributes':attr,'indices':idx}]}],
          'accessors':accessors,'bufferViews':views,'buffers':[{'byteLength':len(data)}]}
    js=json.dumps(gltf,separators=(',',':')).encode(); js+=b' '*(-len(js)%4)
    (OUT/(name+'.glb')).write_bytes(struct.pack('<4sII','glTF'.encode(),2,28+len(js)+len(data))
        +struct.pack('<I4s',len(js),b'JSON')+js+struct.pack('<I4s',len(data),b'BIN\0')+data)

for variant,width,height_m in [('B',.72,.22),('D',.58,.34),('E',.65,.19)]:
    make_tuft(variant,width,height_m)
