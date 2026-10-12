from pathlib import Path
import json, numpy as np
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;R=O/'Renders';labels={'base':'默认护木','vertical':'垂直握把','canted':'45°侧倾握把','prism':'棱镜阻手器','angled':'共振二代前握把'}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19);small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
report=json.loads((O/'analysis.json').read_text());index={c['key']:c for c in report['cases']}
def get(family,kind,frame,view='default'):
 return Image.open(R/f'{family}_{kind}_7_{view}_{float(frame):.1f}.png'.replace('.0.png','p0.png').replace('.5.png','p5.png')).convert('RGB')
for kind in ['normal','empty']:
 frames=[108,125,136,144,148] if kind=='normal' else [125,136,144,154,164]
 canvas=Image.new('RGB',(1920,1000),(22,28,38));draw=ImageDraw.Draw(canvas)
 draw.text((20,12),('普通' if kind=='normal' else '空仓')+'快装：五种握持的回握段｜前五列为默认视野，末列为宽视野最差帧；显示画面下部放大',font=font,fill='white')
 for row,(family,label) in enumerate(labels.items()):
  y=54+row*186;draw.text((12,y),label,font=font,fill='white')
  for col,frame in enumerate(frames+[index[f'{family}_{kind}_7']['views'][1]['clearance_frame']]):
   view='default' if col<5 else 'wide';im=get(family,kind,frame,view);im=im.crop((0,im.height//2,im.width,im.height));im.thumbnail((316,135))
   x=col*320;canvas.paste(im,(x,y+44));draw.text((x+6,y+25),f'{"默认" if col<5 else "宽视野"} f{frame:g}',font=small,fill=(220,230,240) if col<5 else (255,183,98))
 canvas.save(O/f'{kind}-comparison.png')
 images=[];frames2=range(108,(148 if kind=='normal' else 164)+1,2)
 for frame in frames2:
  can=Image.new('RGB',(1152,500),(22,28,38));d=ImageDraw.Draw(can)
  for n,(family,label) in enumerate(labels.items()):
   x=(n%3)*384;y=(n//3)*250;im=get(family,kind,frame).resize((384,216));can.paste(im,(x,y+26));d.text((x+8,y+3),label+f'  f{frame}',font=small,fill='white')
  d.text((785,296),'默认 75° 垂直视野\n真实资产 + 运行时姿态\n几何检查渲染，非 PIE 截图',font=small,fill='white');images.append(can)
 images[0].save(O/f'{kind}-regrip.gif',save_all=True,append_images=images[1:],duration=[40]*(len(images)-1)+[500],loop=0,optimize=False)
# Read each half-frame pose on all counts; verify rendered seven-shell arm is representative.
C=O/'Capture';geom=json.loads((C/'geometry.json').read_text());left=[i for i,n in enumerate(geom['names']) if n.endswith('_l')]
max_delta=0.
for family in labels:
 for kind in ['normal','empty']:
  reference=json.loads((C/f'{family}_{kind}_7.json').read_text())
  ref=np.array([s['bones'] for s in reference['samples']])[:,left,:]
  for count in range(1,7):
   data=json.loads((C/f'{family}_{kind}_{count}.json').read_text());poses=np.array([s['bones'] for s in data['samples']])[:,left,:]
   max_delta=max(max_delta,float(np.abs(poses-ref).max()))
(O/'visual_receipt.json').write_text(json.dumps(dict(rendered_families=list(labels),left_pose_max_component_difference_between_counts=max_delta,source='Capture, current saved assets evaluated by the native graph',geometry_only=True,game_run=False),indent=2))
print('VISUALS_COMPLETE',max_delta,flush=True)
