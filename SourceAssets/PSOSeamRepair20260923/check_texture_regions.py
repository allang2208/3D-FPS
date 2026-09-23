"""Check the requested repair's bake output and sample recovered collar regions."""
import json,numpy as np
from PIL import Image
from pathlib import Path
O=Path(__file__).parent;data=json.loads((O/'authoring.json').read_text());rows=[]
for t in data['textures']:
 a=np.asarray(Image.open(t['source']).convert('RGB'));b=np.asarray(Image.open(t['result']).convert('RGB'))
 if a.shape!=b.shape:raise RuntimeError('Atlas resolution changed')
 delta=np.max(abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)
 row={'host':t['host'],'kind':t['kind'],'size':list(b.shape[:2]),'changed_pixels':int(np.count_nonzero(delta)),'changed_over_2':int(np.count_nonzero(delta>2)),'fraction_changed':float(np.mean(delta>2))}
 if not 0<row['fraction_changed']<.15:raise RuntimeError('Unexpected atlas edit coverage '+str(row))
 rows.append(row)
(O/'texture_checks.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
