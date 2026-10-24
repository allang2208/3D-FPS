from pathlib import Path
import struct,json
from PIL import Image
ROOT=Path(__file__).resolve().parent
receipt=json.loads((ROOT/'sky-bake.json').read_text())
if receipt['stage']!='city_alpha_baked':raise RuntimeError('City capture incomplete')
for key,data in receipt['captures'].items():
 size=data['size'];header=[124,0x2100f,size,size,size*4,0,1]+[0]*11
 header+=[32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]+[0x1008,0xfe00,0,0,0]
 with (ROOT/'Sky'/('T_City'+key+'.dds')).open('wb') as f:
  f.write(b'DDS ');f.write(struct.pack('<31I',*header));f.write(struct.pack('<5I',29,3,4,1,0))
  for face in ('PX','NX','PY','NY','PZ','NZ'):f.write(Image.open(ROOT/'Sky'/key/(face+'.png')).convert('RGBA').tobytes())
print('CITY_ALPHA_CUBES_PACKAGED')
