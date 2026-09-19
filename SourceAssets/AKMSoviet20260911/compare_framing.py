import re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/AKMSoviet20260911'
def pick(run,stage):
 log=(P/f'SourceAssets/AKMIntegration20260910/runtime-{run}.log').read_text(errors='replace')
 ids=[int(i) for s,i in re.findall(r'AKM_FRAME stage=(\d+) index=(\d+)',log) if int(s)==stage]
 return P/f'Saved/AKMIntegrationAudit/{run}/frame_{(ids[-2] if stage==7 else ids[-1]):04d}.png'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',22)
out=Image.new('RGB',(960,1740),(20,24,30))
for i,(label,run,stage) in enumerate([('M4（装备末段参考）','akm-soviet-v1',7),('AKM 调整前','akm-soviet-v1',8),('AKM 整体前移 6 cm','akm-soviet-ads-v2',8)]):
 out.paste(Image.open(pick(run,stage)).convert('RGB'),(0,i*580));ImageDraw.Draw(out).text((15,i*580+544),label,font=font,fill='white')
out.save(O/'framing_comparison.png')

