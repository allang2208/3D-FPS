"""Arrange actual runtime frames for review; no generated or retouched imagery."""
from pathlib import Path
import json
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;P=O.parents[2];root=P/'Saved/SVCHPoseAudit'
before=root/'svch-left-reload-20261019-before';after=root/'svch-left-reload-20261019-after-final'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',25)
board=Image.new('RGB',(1600,980),(22,25,29));draw=ImageDraw.Draw(board)
for row,name in enumerate(['reload_normal_00037.png','reload_normal_00043.png']):
 for col,(folder,label) in enumerate([(before,'修正前'),(after,'修正后')]):
  frame=Image.open(folder/'Frames'/name).convert('RGB').resize((800,450),Image.Resampling.LANCZOS)
  board.paste(frame,(col*800,row*490+40));draw.text((col*800+18,row*490+5),label+' · '+('插匣前' if row==0 else '松手回握'),font=font,fill=(240,240,240))
board.save(O/'reload_before_after.jpg',quality=92)
rows=[json.loads(x) for x in (after/'frames.jsonl').read_text().splitlines()]
for stage in ('reload_normal','reload_empty'):
 selected=[r for r in rows if r['stage']==stage and r['action_alpha']>.05]
 imgs=[Image.open(after/'Frames'/r['image']).convert('RGB').resize((800,450),Image.Resampling.LANCZOS) for r in selected]
 imgs[0].save(O/(stage+'_review.gif'),save_all=True,append_images=imgs[1:],duration=133,loop=0,optimize=False)
print('SVCH_LEFT_RELOAD_REVIEW_MEDIA_SAVED')
