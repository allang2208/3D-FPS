from pathlib import Path
import io, struct, json, hashlib
from PIL import Image, ImageOps
root=Path(__file__).resolve().parent
source=next((root/'Input').glob('*.glb'))
with source.open('rb') as f:
    f.seek(12)
    n,_=struct.unpack('<II',f.read(8)); gltf=json.loads(f.read(n))
    n,_=struct.unpack('<II',f.read(8)); data=f.read(n)
mat=gltf['materials'][0]; pbr=mat['pbrMetallicRoughness']
meta={'source':source.name,'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'textures':{}}
for key,entry in [('BaseColor',pbr['baseColorTexture']),('MetalRough',pbr['metallicRoughnessTexture']),('NormalDX',mat['normalTexture'])]:
    image=gltf['images'][gltf['textures'][entry['index']]['source']]
    view=gltf['bufferViews'][image['bufferView']]; start=view.get('byteOffset',0)
    pix=Image.open(io.BytesIO(data[start:start+view['byteLength']])).convert('RGB')
    if key=='NormalDX':
        r,g,b=pix.split();pix=Image.merge('RGB',(r,ImageOps.invert(g),b))
    dest=root/'Exports'/('T_M24_Meshy1105135808_'+key+'.png')
    pix.save(dest,compress_level=3)
    meta['textures'][key]={'file':dest.name,'size':pix.size}
(root/'source.json').write_text(json.dumps(meta,indent=2))
