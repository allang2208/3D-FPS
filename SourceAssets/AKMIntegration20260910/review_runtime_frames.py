from pathlib import Path
from PIL import Image,ImageDraw
import re
O=Path(__file__).parent
run='akm-source-matched-fab-v1'
log=(O/f'runtime-{run}.log').read_text(errors='replace')
for stage in [5,6]:
 ids=[int(i) for i in re.findall(r'AKM_FRAME stage='+str(stage)+r' index=(\d+)',log)]
 chosen=[ids[round(k*(len(ids)-1)/19)] for k in range(20)]
 sheet=Image.new('RGB',(1280,1000),(20,20,20));draw=ImageDraw.Draw(sheet)
 for k,i in enumerate(chosen):
  im=Image.open(O.parents[1]/f'Saved/AKMIntegrationAudit/{run}/frame_{i:04d}.png').convert('RGB').resize((320,180))
  x=k%4*320;y=k//4*200;sheet.paste(im,(x,y));draw.text((x+5,y+182),f'frame {i}',fill='white')
 sheet.save(O/f'SourceMatched/Delivery/reload_stage_{stage}.png')
