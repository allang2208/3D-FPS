"""Losslessly package six baked RGBA faces into a native DDS cubemap container."""
from pathlib import Path
import struct,json,hashlib
from PIL import Image
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Authored';size=2048
faces=['PX','NX','PY','NY','PZ','NZ']
# DDS DX10: one 2D cubemap, six square slices, RGBA8 sRGB, original face pixels.
header=[124,0x2100f,size,size,size*4,0,1]+[0]*11
header += [32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]
header += [0x1008,0xfe00,0,0,0]
path=OUT/'T_Reception_IndustrialNightCube.dds'
with path.open('wb') as dst:
    dst.write(b'DDS ');dst.write(struct.pack('<31I',*header));dst.write(struct.pack('<5I',29,3,4,1,0))
    for face in faces:
        im=Image.open(OUT/'CubeFaces'/(face+'.png')).convert('RGBA')
        if im.size!=(size,size):raise RuntimeError('Bake size mismatch: '+face)
        dst.write(im.tobytes())
(ROOT/'cube.json').write_text(json.dumps(dict(file=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),size=size,faces=faces,format='DDS DX10 RGBA8 sRGB cubemap',coordinate_mapping='cube=(Blender X, Blender Z, Blender Y); UE local view=(-Y,+Z,-X)',pixel_resampling=False),indent=2),encoding='utf8')
print('CUBEMAP_PACKAGED',str(path))
