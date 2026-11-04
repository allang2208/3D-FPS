"""Archive the user-selected GLB and extract its original PBR images, without mesh edits."""
import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path(r'C:\Users\allan\Downloads\Meshy_AI_Tactical_Hatchet_1101133535_texture.glb')
(ROOT / 'Original').mkdir(parents=True, exist_ok=True)
(ROOT / 'Textures').mkdir(exist_ok=True)
target = ROOT / 'Original' / SOURCE.name
if not target.exists():
    shutil.copy2(SOURCE, target)
raw = target.read_bytes()
magic, version, length = struct.unpack_from('<III', raw)
if magic != 0x46546C67 or version != 2:
    raise RuntimeError('Expected glTF 2 binary source')
offset = 12
chunks = {}
while offset < len(raw):
    size, kind = struct.unpack_from('<II', raw, offset)
    chunks[kind] = raw[offset + 8:offset + 8 + size]
    offset += size + 8
doc = json.loads(chunks[0x4E4F534A])
binary = chunks[0x004E4942]
images = []
for index, image in enumerate(doc.get('images', [])):
    view = doc['bufferViews'][image['bufferView']]
    ext = '.png' if image['mimeType'] == 'image/png' else '.jpg'
    name = 'source_image_%02d%s' % (index, ext)
    start = view.get('byteOffset', 0)
    (ROOT / 'Textures' / name).write_bytes(binary[start:start + view['byteLength']])
    images.append(dict(index=index, file=name, mime=image['mimeType']))
geometry = []
for mesh in doc['meshes']:
    for prim in mesh['primitives']:
        p = doc['accessors'][prim['attributes']['POSITION']]
        indices = doc['accessors'][prim['indices']]
        geometry.append(dict(name=mesh.get('name'), vertices=p['count'], triangles=indices['count']//3,
                             bounds_min=p.get('min'), bounds_max=p.get('max'), material=prim.get('material'),
                             attributes=list(prim['attributes'])))
manifest = dict(source=str(SOURCE), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                meshes=geometry, materials=doc.get('materials'), textures=doc.get('textures'),
                images=images, nodes=doc.get('nodes'), scenes=doc.get('scenes'),
                status='source_prepared', source_license='User-supplied Meshy export; not published', runtime_tested=False)
(ROOT / 'source_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(manifest, indent=2, ensure_ascii=False))
