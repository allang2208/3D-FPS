import sys,json,hashlib
from pathlib import Path
import numpy as np
O=Path(__file__).parent
sys.path.insert(0,str(O.parent/'ClothReload44/Diagnostics'))
import diag_lib as D
S=json.loads((O/'source.json').read_text());L=json.loads((O.parent/'BeltRebuild52/layout.json').read_text())
T=D.load_tracks(O.parent/'ClothReload44/Tracks/base_tracks.json.gz');W=D.worlds(T)
for side in range(2):
 prefix='New_' if side else '';C=np.array([(W[:,D.BI[prefix+'LMG201_Belt_%02d'%i]]@np.r_[L['centers_bone_local'][side][i],1])[:,:3] for i in range(6)]).transpose(1,0,2)
 print('SIDE',side,'distance max cm',np.linalg.norm(C[:,0]-C[:,5],axis=1).max(),'rest sum cm',np.linalg.norm(np.diff(C[0],axis=0),axis=1).sum())
for key,row in S['clips'].items():
 old=json.loads((O.parent/'ClothReload44/delivery.json').read_text())['saved'][row['path']]['sha256']
 print(key,'matches current author receipt',row['sha256']==old)
