"""Extract the embedded PNGs by glTF material role without recompression."""
import json
import struct
from pathlib import Path
source = Path(__file__).resolve().parent
with next((source / 'Original').glob('*.glb')).open('rb') as f:
    f.seek(12)
    n, _ = struct.unpack('<II', f.read(8))
    doc = json.loads(f.read(n))
    f.read(8)
    binary = f.tell()
    mat = doc['materials'][0]
    pbr = mat['pbrMetallicRoughness']
    for name, slot in [('BaseColor', pbr['baseColorTexture']), ('Normal', mat['normalTexture']),
                       ('ORM', pbr['metallicRoughnessTexture'])]:
        im = doc['images'][doc['textures'][slot['index']]['source']]
        view = doc['bufferViews'][im['bufferView']]
        f.seek(binary + view.get('byteOffset', 0))
        (source / 'Export' / ('T_WoodenTorch_' + name + '.png')).write_bytes(f.read(view['byteLength']))
