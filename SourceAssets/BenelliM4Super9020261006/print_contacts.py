import json, numpy as np
from pathlib import Path
O=Path(r'D:/FPS3D/FPSGAME/SourceAssets/BenelliM4Super9020261006');d=json.loads((O/'source_contact_tracks.json').read_text())
for name,rows in d.items():
 if 'Idle' in name:continue
 print(name)
 for row in rows:
  main=np.array(row['Main']);inv=np.linalg.inv(main);p={k:(inv@np.array(row[k]))[:3,3].round(3).tolist() for k in ('Shell','Slider','Load','hand_L')}
  print(round(row['t'],3),p)
