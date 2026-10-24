"""Package the six produced faces, unchanged, into the native DDS container."""
from pathlib import Path
import struct,json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parent
receipt=json.loads((ROOT/'bake-receipt.json').read_text())
if receipt['stage']!='six_faces_baked':raise RuntimeError('Incomplete production bake')
size=receipt['resolution'];faces=['PX','NX','PY','NY','PZ','NZ']
header=[124,0x2100f,size,size,size*4,0,1]+[0]*11
header += [32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]
header += [0x1008,0xfe00,0,0,0]
path=ROOT/'Authored/T_CyberpunkBayNight_Cube.dds'
with path.open('wb') as dst:
    dst.write(b'DDS ');dst.write(struct.pack('<31I',*header));dst.write(struct.pack('<5I',29,3,4,1,0))
    for face in faces:
        im=Image.open(ROOT/'Authored/CubeFaces'/(face+'.png')).convert('RGBA')
        if im.size!=(size,size):raise RuntimeError('Unexpected produced face size')
        dst.write(im.tobytes())
(ROOT/'cube.json').write_text(json.dumps(dict(file=str(path),size=size,faces=faces,
    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),format='DDS DX10 RGBA8 sRGB cube',
    coordinate_mapping='cube=(screen right, up, bay forward); UE world=(-X,Z,+Y)',
    source_dimensions=receipt['source_dimensions'],original_detail_not_upscaled=True),indent=2),encoding='utf-8')
print('BAY_CUBE_PACKAGED',path)
