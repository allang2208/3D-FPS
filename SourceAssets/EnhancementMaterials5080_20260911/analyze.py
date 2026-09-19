import json, struct, hashlib
from pathlib import Path
P=Path(__file__).parent
rows=[]
for file in P.glob('*.glb'):
    data=file.read_bytes(); size,kind=struct.unpack_from('<II',data,12)
    assert kind==0x4e4f534a
    gltf=json.loads(data[20:20+size]); acc=gltf['accessors']
    row={'file':file.name,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'triangles':0,'vertices':0,'materials':gltf.get('materials',[]),'images':gltf.get('images',[])}
    for mesh in gltf['meshes']:
        for primitive in mesh['primitives']:
            row['vertices']+=acc[primitive['attributes']['POSITION']]['count']
            row['triangles']+=acc[primitive['indices']]['count']//3
    rows.append(row)
history=[]
for file in P.glob('*_history.json'):
    h=json.loads(file.read_text()); messages=h['status']['messages']; start=next((v['timestamp'] for k,v in messages if k=='execution_start'),None); end=next((v['timestamp'] for k,v in messages if k in ('execution_success','execution_error')),None)
    history.append({'task':file.stem,'status':h['status']['status_str'],'seconds':round((end-start)/1000,2) if start and end else None})
(P/'asset_audit.json').write_text(json.dumps({'models':rows,'execution':history},indent=2))
print(json.dumps({'models':[{k:r[k] for k in ('file','triangles','vertices','bytes')} for r in rows],'execution':history},indent=2))
