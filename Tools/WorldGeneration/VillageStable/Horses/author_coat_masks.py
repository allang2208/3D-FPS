from pathlib import Path
import json,struct
import numpy as np
from PIL import Image
import cv2
PROJECT=Path(__file__).resolve().parents[4]
EXCHANGE=PROJECT/'SourceAssets/HillsVillageStable/HorsesR7/Exchange'

def surface_texels(size):
    data=(EXCHANGE/'Warhorse_Stable.glb').read_bytes()
    chunk=struct.unpack_from('<I',data,12)[0]
    doc=json.loads(data[20:20+chunk]); buf=data[28+chunk:]
    def read(index):
        a=doc['accessors'][index];v=doc['bufferViews'][a['bufferView']]
        width={'VEC2':2,'VEC3':3,'VEC4':4,'SCALAR':1}[a['type']]
        dt=np.dtype({5126:'<f4',5123:'<u2',5125:'<u4',5121:'u1'}[a['componentType']])
        return np.ndarray((a['count'],width),dtype=dt,buffer=buf,offset=v.get('byteOffset',0)+a.get('byteOffset',0),strides=(v.get('byteStride',width*dt.itemsize),dt.itemsize))
    prim=doc['meshes'][0]['primitives'][0];at=prim['attributes']
    pos=read(at['POSITION']); tex=read(at['TEXCOORD_0'])*size-.5
    tail_bones=[i for i,k in enumerate(doc['skins'][0]['joints']) if doc['nodes'][k]['name'].startswith('tail_')]
    tail=(np.isin(read(at['JOINTS_0']),tail_bones)*read(at['WEIGHTS_0'])).sum(axis=1)
    vertices=np.column_stack((pos,tail)).astype('float32')
    out=np.full((size,size,4),np.nan,np.float32)
    for face in read(prim['indices']).reshape(-1,3):
        t=tex[face];lo=np.maximum(np.floor(t.min(0)).astype(int),0);hi=np.minimum(np.ceil(t.max(0)).astype(int),size-1)
        if (lo>hi).any():continue
        a,b=t[1:]-t[0];det=a[0]*b[1]-a[1]*b[0]
        if abs(det)<1e-6:continue
        yy,xx=np.ogrid[lo[1]:hi[1]+1,lo[0]:hi[0]+1];x=xx-t[0,0];y=yy-t[0,1]
        u=(x*b[1]-y*b[0])/det;v=(y*a[0]-x*a[1])/det
        inside=(u>=0)&(v>=0)&(u+v<=1)
        d=vertices[face];out[lo[1]:hi[1]+1,lo[0]:hi[0]+1][inside]=d[0]+u[inside,None]*(d[1]-d[0])+v[inside,None]*(d[2]-d[0])
    return out

def author(dest):
    size=2048
    surface=surface_texels(size)
    valid=np.isfinite(surface[:,:,0])
    x,h,f,tail=np.moveaxis(np.nan_to_num(surface),-1,0)
    # Protective matte painted in the scan's side projection. Each pixel here
    # corresponds to 1/300 m; both flanks share the same saddlery layout.
    gear=np.zeros((660,790),np.uint8)
    def polygon(points):
        cv2.fillPoly(gear,[np.asarray(points,np.int32)],255,lineType=cv2.LINE_AA)
    def strap(points,width):
        cv2.polylines(gear,[np.asarray(points,np.int32)],False,255,width,cv2.LINE_AA)
    polygon([(268,261),(274,155),(290,151),(294,113),(307,111),(327,141),(410,132),(419,100),(442,98),(450,142),(462,155),(467,230),(461,264)])
    polygon([(397,250),(419,250),(432,319),(435,389),(403,394),(395,356),(392,339),(401,317)])
    polygon([(389,355),(394,326),(418,318),(431,339),(434,366),(390,367)])
    polygon([(446,139),(460,131),(483,154),(510,179),(553,206),(585,233),(601,251),(593,303),(586,326),(580,275),(559,251),(523,229),(479,206),(454,198)])
    strap([(448,130),(478,149),(515,183),(563,214),(590,241),(612,251),(637,252),(664,247),(692,233),(711,215),(726,193)],9)
    # Bridle leather, bit, soft muzzle, eyes, and hoof horn retain their original PBR.
    strap([(674,53),(691,81),(703,118),(723,161),(736,178)],8)
    strap([(690,180),(708,178),(729,168),(750,158)],10)
    cv2.ellipse(gear,(710,97),(16,13),12,0,360,255,-1)
    polygon([(709,183),(734,163),(755,153),(781,165),(784,229),(723,228)])
    gear=cv2.GaussianBlur(gear,(0,0),1.45)
    u=np.clip(np.rint((f+1.30)*300).astype(int),0,789)
    v=np.clip(np.rint((2.16-h)*300).astype(int),0,659)
    coat=(1.-gear[v,u]/255.)*np.clip((h-.095)/.07,0,1)
    hair=np.clip((tail-.05)/.58,0,1)
    # Protect the dense original crest underneath the R17 root pelt.
    crown=np.clip((.065-np.abs(x))/.03,0,1)*np.clip((f-.17)/.08,0,1)*np.clip((1.-f)/.1,0,1)*np.clip((h-(1.51+.50*(f-.18)))/.065,0,1)
    coat*=1.-np.maximum(hair,crown)
    # Reference position in RGB, signed coat/tail coverage in alpha. This atlas
    # stays in bind space through skin cache, LOD changes, and animated poses.
    mask=np.uint8(np.rint(255*np.clip(np.stack((x+.5,h/2.2,(f+1.3)/2.6,
                                               .5+.5*(coat-hair)),axis=-1),0,1)))
    # Fill UV gutters with the nearest authored texel before the GPU builds mipmaps.
    from scipy.ndimage import distance_transform_edt
    indices=distance_transform_edt(~valid,return_distances=False,return_indices=True)
    Image.fromarray(mask[tuple(indices)]).save(dest/'T_Warhorse_Regions.png')
    # Periodic two-channel multiscale pigment field. The material samples this
    # tile on oblique rest-space planes using each individual's scale and phase.
    from scipy.ndimage import map_coordinates
    rng=np.random.default_rng(26815);grid=np.indices((256,256),dtype=float)
    channels=[]
    for i in range(2):
        value=np.zeros((256,256))
        for scale,gain in ((4,1.),(8,.43),(16,.17),(32,.07)):
            tile=rng.random((scale,scale))
            value+=gain*map_coordinates(tile,grid*(scale/256),order=3,mode='grid-wrap')
        channels.append(np.uint8(np.clip((value-value.mean())/(3.5*value.std())+.5,0,1)*255))
    Image.fromarray(np.stack((*channels,channels[0]),axis=-1)).save(dest/'T_Warhorse_Pigment.png')

if __name__=='__main__':
    author(PROJECT/'SourceAssets/HillsVillageStable/AppearanceR30')
