from pathlib import Path
import struct,json
from PIL import Image
R=Path(__file__).resolve().parent;size=2048;path=R/'T_AP17_CityReflection.dds'
header=[124,0x2100f,size,size,size*4,0,1]+[0]*11
header += [32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]+[0x1008,0xfe00,0,0,0]
with path.open('wb') as file:
 file.write(b'DDS ');file.write(struct.pack('<31I',*header));file.write(struct.pack('<5I',29,3,4,1,0))
 for name in ['PX','NX','PY','NY','PZ','NZ']:
  with Image.open(R/'ReflectionFaces'/(name+'.png')) as im:
   if im.size!=(size,size):raise RuntimeError('Incomplete production cube')
   file.write(im.convert('RGBA').tobytes())
(R/'reflection-packed.json').write_text(json.dumps(dict(path=str(path),size=size,city_only=True),indent=2),encoding='utf8')
print('AP17_REFLECTION_PACKED')
