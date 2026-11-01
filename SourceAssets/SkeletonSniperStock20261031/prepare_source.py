import json,struct,shutil,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
source=Path(r'C:\Users\allan\Downloads\Meshy_AI_Adjustable_Tactical_R_1031040412_texture.glb')
for name in ('Original','Textures','Exports','Inputs','Icons','Before'):(O/name).mkdir(exist_ok=True)
target=O/'Original'/source.name
if not target.exists():shutil.copy2(source,target)
blob=target.read_bytes();n,t=struct.unpack_from('<II',blob,12);j=json.loads(blob[20:20+n]);start=20+n+8
for im in j['images']:
    v=j['bufferViews'][im['bufferView']];a=start+v.get('byteOffset',0)
    (O/'Textures'/(im['name']+'.png')).write_bytes(blob[a:a+v['byteLength']])
(O/'source.json').write_text(json.dumps(dict(source=str(source),archived=str(target),sha256=hashlib.sha256(blob).hexdigest(),gltf=j,mesh_modified=False),indent=2))
print('Archived source and extracted embedded PBR images')
