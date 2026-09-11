"""Encode real exported-FBX renders; no synthetic frames or painted corrections."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
import json,math
root=Path('D:/FPS3D/FPSGAME/SourceAssets/PoisonMaggot20260911/previews')
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
def frames(name):
 return [Image.open(p).convert('RGB') for p in sorted((root/name).glob('*.png')) if int(p.stem)%3==2]
clips={name:frames(name) for name in ['Idle','Move','Spit','Death','Hit']}
counts={'Idle':30,'Move':25,'Spit':30,'Death':18,'Hit':6}
for name,images in clips.items():
 assert len(images)==counts[name],(name,len(images))
 images[0].save(root/(name+'.gif'),save_all=True,append_images=images[1:],duration=[100]*(len(images)-1)+([1200] if name in ['Death','Hit'] else [100]),loop=0,optimize=True)
overview=[]
# All three periods meet again after 15 seconds; do not truncate Move mid-cycle.
for index in range(math.lcm(counts['Idle'],counts['Move'],counts['Spit'])):
 canvas=Image.new('RGB',(1200,315),(237,239,239));draw=ImageDraw.Draw(canvas)
 for col,name in enumerate(['Idle','Move','Spit']):
  frame=clips[name][index%len(clips[name])].resize((400,267),Image.Resampling.LANCZOS)
  canvas.paste(frame,(col*400,40));draw.text((col*400+18,8),name+'  '+{'Idle':'3.0 s','Move':'2.5 s','Spit':'3.0 s'}[name],font=font,fill=(36,42,39))
 overview.append(canvas)
overview[0].save(root/'PoisonMaggot_Actions.gif',save_all=True,append_images=overview[1:],duration=100,loop=0,optimize=True)
(root/'gif_manifest.json').write_text(json.dumps({name:{'frames':len(f),'fps':10,'source':'reimported FBX render','playback':'preview repeats; Death/Hit hold last pose for 1.2 s'} for name,f in clips.items()},indent=2))
print('MAGGOT_GIFS_COMPLETE')
