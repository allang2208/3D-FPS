from pathlib import Path
import struct,json,hashlib,shutil
P=Path(__file__).resolve().parent
src=Path('C:/Users/allan/Downloads/Meshy_AI_Valkyrie_Forge_Chestp_1101102421_texture.glb')
(P/'Original').mkdir(parents=True,exist_ok=True)
(P/'Textures').mkdir(exist_ok=True)
dst=P/'Original'/src.name
if not dst.exists():shutil.copy2(src,dst)
raw=dst.read_bytes();pos=12;chunks={}
while pos<len(raw):
    size,kind=struct.unpack_from('<II',raw,pos);pos+=8
    chunks[kind]=raw[pos:pos+size];pos+=size
data=json.loads(chunks[0x4e4f534a]);blob=chunks[0x004e4942]
for i,img in enumerate(data.get('images',[])):
    view=data['bufferViews'][img['bufferView']]
    ext='.png' if img['mimeType']=='image/png' else '.jpg'
    path=P/'Textures'/('MeshySource_'+str(i)+ext)
    path.write_bytes(blob[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']])
    img['extracted_to']=str(path)
(P/'Original/gltf_metadata.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
(P/'Original/source_receipt.json').write_text(json.dumps(dict(source=str(src),copy=str(dst),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw)),indent=2),encoding='utf-8')
print(json.dumps({key:data.get(key) for key in ['asset','nodes','meshes','materials','textures','images']},indent=2))
print('POSITION_ACCESSORS',[(i,a) for i,a in enumerate(data['accessors']) if a.get('type')=='VEC3' and 'min' in a])
