"""DDS packaging of unchanged, freshly rendered production faces."""
import struct,json,hashlib
from PIL import Image
from design import *
receipt=json.loads((ROOT/'bake-receipt.json').read_text())
if receipt['stage']!='production_cubes_baked':raise RuntimeError('Production capture incomplete')
results={}
for key,data in receipt['captures'].items():
 size=data['size'];path=ROOT/('T_Bay'+key+'.dds')
 header=[124,0x2100f,size,size,size*4,0,1]+[0]*11
 header += [32,4,struct.unpack('<I',b'DX10')[0],0,0,0,0,0]+[0x1008,0xfe00,0,0,0]
 with path.open('wb') as f:
  f.write(b'DDS ');f.write(struct.pack('<31I',*header));f.write(struct.pack('<5I',29,3,4,1,0))
  for face in ['PX','NX','PY','NY','PZ','NZ']:
   im=Image.open(ROOT/'CubeFaces'/key/(face+'.png')).convert('RGBA')
   f.write(im.tobytes())
 results[key]=dict(path=str(path),size=size,sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),
  capture_origin=data['origin'],bc7_full_mip_estimate_mib=6*size*size*4/3/1024**2)
(ROOT/'cubes.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print('BAY_CUBES_PACKAGED',json.dumps({k:v['size'] for k,v in results.items()}))
