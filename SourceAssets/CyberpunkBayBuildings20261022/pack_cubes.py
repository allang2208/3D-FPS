"""Package original city-only production faces for Unreal TextureCube import."""
import struct,json
from PIL import Image
from design import *
out=ROOT/'Sky';out.mkdir(parents=True,exist_ok=True);records={}
for key,size in [('Far',FAR_FACE_SIZE),('Reflection',REFLECTION_FACE_SIZE)]:
 path=out/('T_City'+key+'.dds')
 header=[124,0x2100f,size,size,size*4,0,1]+[0]*11
 header += [32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]+[0x1008,0xfe00,0,0,0]
 with path.open('wb') as f:
  f.write(b'DDS ');f.write(struct.pack('<31I',*header));f.write(struct.pack('<5I',29,3,4,1,0))
  for face in ['PX','NX','PY','NY','PZ','NZ']:
   with Image.open(ROOT/'CubeFaces'/key/(face+'.png')) as im:
    if im.size!=(size,size):raise RuntimeError('Incomplete production cube '+key)
    f.write(im.convert('RGBA').tobytes())
 records[key]=dict(path=str(path),size=size,transparent=True)
(ROOT/'cubes.json').write_text(json.dumps(records,indent=2),encoding='utf8')
print('DETAILED_BAY_CUBES_PACKAGED',flush=True)
