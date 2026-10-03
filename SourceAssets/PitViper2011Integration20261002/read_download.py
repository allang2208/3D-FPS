"""Read the official GLB and extract its author textures for production."""
import json, struct
from pathlib import Path
O=Path(__file__).resolve().parent
raw=(O/'Original/PitViper2011_Official.glb').read_bytes()
at=12;doc=None;binary=None
while at<len(raw):
    length,kind=struct.unpack_from('<II',raw,at);chunk=raw[at+8:at+8+length];at+=8+length
    if kind==0x4E4F534A:doc=json.loads(chunk)
    elif kind==0x004E4942:binary=chunk
textures=O/'SourceTextures';textures.mkdir(exist_ok=True)
images=[]
for i,image in enumerate(doc.get('images',[])):
    if 'bufferView' not in image:
        images.append({'index':i,'source':image});continue
    view=doc['bufferViews'][image['bufferView']];start=view.get('byteOffset',0)
    mime=image.get('mimeType','image/png');extension={ 'image/png':'.png','image/jpeg':'.jpg' }.get(mime,'.bin')
    file=textures/('Source_'+str(i)+extension);file.write_bytes(binary[start:start+view['byteLength']])
    images.append({'index':i,'file':str(file.relative_to(O)),'mime':mime,'bytes':file.stat().st_size})
report={'asset':doc.get('asset'),'extensions_required':doc.get('extensionsRequired',[]),
        'nodes':doc.get('nodes',[]),'meshes':[],'materials':doc.get('materials',[]),'textures':doc.get('textures',[]),'images':images}
for mesh in doc.get('meshes',[]):
    entry={'name':mesh.get('name'),'primitives':[]}
    for p in mesh['primitives']:
        a=doc['accessors'][p['attributes']['POSITION']]
        entry['primitives'].append({'vertices':a['count'],'min':a.get('min'),'max':a.get('max'),'material':p.get('material'),'attributes':list(p['attributes']),'indices':doc['accessors'][p['indices']]['count'] if 'indices' in p else None})
    report['meshes'].append(entry)
(O/'source_layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False,indent=2))
