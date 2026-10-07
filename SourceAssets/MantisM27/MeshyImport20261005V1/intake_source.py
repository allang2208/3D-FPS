"""Archive and read the user-supplied M27 GLB; preserve original geometry."""
import array
import hashlib
import json
import shutil
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = Path('C:/Users/allan/Downloads/Meshy_AI_M_27_Mawbound_Horror_1005150638_texture.glb')
raw = SOURCE.read_bytes()
magic, version, length = struct.unpack_from('<III', raw)
if magic != 0x46546C67 or version != 2 or length != len(raw):
    raise ValueError('Incomplete or unsupported GLB')
offset = 12
doc = binary = None
while offset < len(raw):
    size, kind = struct.unpack_from('<II', raw, offset)
    payload = raw[offset + 8:offset + 8 + size]
    if len(payload) != size:
        raise ValueError('Truncated GLB chunk')
    if kind == 0x4E4F534A:
        doc = json.loads(payload)
    elif kind == 0x004E4942:
        binary = payload
    offset += size + 8
if doc is None or binary is None:
    raise ValueError('Missing GLB JSON/BIN')

primitives = []
for mesh in doc.get('meshes', []):
    for prim in mesh['primitives']:
        attrs = prim['attributes']
        pos = doc['accessors'][attrs['POSITION']]
        ind = doc['accessors'][prim['indices']]
        view = doc['bufferViews'][ind['bufferView']]
        start = view.get('byteOffset', 0) + ind.get('byteOffset', 0)
        codes = {5121: 'B', 5123: 'H', 5125: 'I'}
        indices = array.array(codes[ind['componentType']])
        indices.frombytes(binary[start:start + ind['count'] * indices.itemsize])
        invalid = sum(i >= pos['count'] for i in indices)
        if invalid or prim.get('mode', 4) != 4 or len(indices) % 3:
            raise ValueError('Invalid triangle indices or unsupported primitive')
        primitives.append({
            'name': mesh.get('name'), 'vertices_with_uv_seam_splits': pos['count'],
            'triangles': len(indices) // 3, 'invalid_indices': invalid,
            'attributes': list(attrs), 'bounds_min_m': pos.get('min'),
            'bounds_max_m': pos.get('max'), 'material_index': prim.get('material'),
        })

archived = ROOT / 'Source' / SOURCE.name
archived.parent.mkdir(parents=True, exist_ok=True)
if archived.exists() and archived.read_bytes() != raw:
    raise FileExistsError('Different archived source exists')
if not archived.exists():
    shutil.copy2(SOURCE, archived)
textures = []
for image in doc.get('images', []):
    view = doc['bufferViews'][image['bufferView']]
    start = view.get('byteOffset', 0)
    payload = binary[start:start + view['byteLength']]
    if image.get('mimeType') != 'image/png':
        raise ValueError('Unexpected embedded texture type')
    width, height = struct.unpack_from('>II', payload, 16)
    texture_path = ROOT / 'Source' / (image['name'] + '.png')
    texture_path.write_bytes(payload)
    textures.append({'name': image['name'], 'width': width, 'height': height,
                     'bytes': len(payload), 'extracted_file': str(texture_path)})

report = {
    'name': '螳螂-M27', 'asset_id': 'MantisM27', 'date': '2026-10-05',
    'provided_by': 'User; Meshy retopology reported by user',
    'source_path': str(SOURCE), 'archived_source': str(archived),
    'source_sha256': hashlib.sha256(raw).hexdigest(), 'source_bytes': len(raw),
    'generator_metadata': doc['asset'], 'primitives': primitives,
    'materials': doc.get('materials', []), 'textures': textures,
    'skins': len(doc.get('skins', [])), 'animations': len(doc.get('animations', [])),
    'mesh_nodes': doc.get('nodes', []), 'extensions_required': doc.get('extensionsRequired', []),
    'source_height_cm': (primitives[0]['bounds_max_m'][1] - primitives[0]['bounds_min_m'][1]) * 100,
    'concept_height_cm': 210,
    'scope': 'Direct static appearance import; no remeshing, decimation, rigging or gameplay registration.',
    'assessment': 'Complete textured static GLB. No JOINTS/WEIGHTS, skin, skeleton or animation. Retopology alone does not make an animated monster.',
    'rights': 'User-supplied Meshy output; no public redistribution performed or permission inferred.',
    'runtime_tested': False, 'rendered': False,
}
(ROOT / 'source_inspection.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'triangles': sum(p['triangles'] for p in primitives), 'skins': report['skins'],
                  'animations': report['animations'], 'source_height_cm': report['source_height_cm'],
                  'source_sha256': report['source_sha256']}, ensure_ascii=False))
