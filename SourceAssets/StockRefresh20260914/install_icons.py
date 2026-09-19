import json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent
D=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/AttachmentIcons20260913')
B=P/'Before/Icons';B.mkdir(exist_ok=True)
keys=['false','skeleton','qr_performance','core_stock','tactical_telescopic']
for key in keys:
 name='stock_'+key
 for ext in ['.png','.uasset','.uexp','.ubulk']:
  old=D/(name+ext);backup=B/(name+ext)
  if old.is_file() and not backup.exists():shutil.copy2(old,backup)
 shutil.copy2(P/'Icons'/(name+'.png'),D/(name+'.png'))
(P/'icon_delivery.json').write_text(json.dumps({'directory':str(D),'icons':['stock_'+k+'.png' for k in keys],'source':'actual current M4 representative stock meshes','direction':'mounting/front end left, buttpad right; horizontal orthographic side view','size':[1024,1024],'format':'RGBA PNG with transparent background','runtime_tested':False},indent=2))
print('STOCK_ICONS_INSTALLED',len(keys))
