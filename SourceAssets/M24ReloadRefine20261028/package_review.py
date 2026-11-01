import json
from pathlib import Path
from PIL import Image,ImageDraw
O=Path(__file__).resolve().parent;folder=O/'MotionReview'
for role in ('reload','reload_empty_mag10'):
 files=sorted(folder.glob(role+'_*.png'));frames=[]
 for f in files:
  im=Image.open(f).convert('RGB');d=ImageDraw.Draw(im);d.rectangle((0,0,720,26),fill=(22,25,29));d.text((10,8),role+' | authoring view | silent',fill='white');frames.append(im)
 frames[0].save(O/(role+'.gif'),save_all=True,append_images=frames[1:],duration=67,loop=0)
chosen=[('reload',k) for k in (6,12,18,22,27,30,33,37)]+[('reload_empty_mag10',k) for k in (12,18,27,30,38,45,51,60)]
sheet=Image.new('RGB',(1440,1040),(22,25,29));draw=ImageDraw.Draw(sheet)
for i,(role,k) in enumerate(chosen):
 f=folder/f'{role}_{k:03d}.png';im=Image.open(f).convert('RGB');im.thumbnail((360,240));x=i%4*360;y=i//4*260;sheet.paste(im,(x,y+20));draw.text((x+8,y+5),f'{role} {k/15:.2f}s',fill='white')
sheet.save(O/'motion-contact-sheet.jpg')
build=json.loads((O/'build-receipt.json').read_text(encoding='utf-8-sig'));saved=json.loads((O/'install_receipt.json').read_text());review=json.loads((O/'source_review.json').read_text())
delivery={'asset_saved':saved['complete'],'build':build,'source_hand_review':review,'normal_seconds':2.8,'empty_seconds':134/30,'preserved':['gun and magazine tracks','wrist and full arm transforms','right-hand bolt animation','existing common optics and damage formula'],'runtime_tested':False,'previews':[str(O/'reload.gif'),str(O/'reload_empty_mag10.gif')]}
(O/'delivery.json').write_text(json.dumps(delivery,indent=2))
print(json.dumps({'assets_saved':saved['complete'],'build_mode':build['mode'],'build_exit':build['exit_code'],'source_review':review},indent=2))
