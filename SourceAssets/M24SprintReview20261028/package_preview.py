from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).resolve().parent
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
frames=[]
for i,f in enumerate(sorted((O/'Playback').glob('frame_*.png'))):
 if i%2:continue
 a=Image.open(f).convert('RGB');a=a.resize((640,360));d=ImageDraw.Draw(a)
 d.rectangle((0,0,640,27),fill=(20,24,29));d.text((10,3),'M24 离线动作复核：起跑 → 循环 → 回落 → 中途取消',font=font,fill='white')
 d.line((315,180,325,180),fill=(130,145,155));d.line((320,175,320,185),fill=(130,145,155));frames.append(a)
frames[0].save(O/'M24_sprint_review.gif',save_all=True,append_images=frames[1:],duration=67,loop=0)
ref=Image.open(O.parent/'M24SprintSupport20261028/Reference/ref_011.png').convert('RGB').resize((640,360))
stage='compressed' if (O/'compressed/game_1.00_0.25.png').exists() else 'before'
own=Image.open(O/stage/'game_1.00_0.25.png').convert('RGB').resize((640,360))
sheet=Image.new('RGB',(1280,400),(20,24,29));sheet.paste(ref,(0,40));sheet.paste(own,(640,40));d=ImageDraw.Draw(sheet)
d.text((12,10),'视频参考 1:05.75（M200）',font=font,fill='white');d.text((652,10),'M24 第一人称视角重建',font=font,fill='white')
sheet.save(O/'reference-comparison.jpg',quality=85)
print('M24_SPRINT_REVIEW_PREVIEW_PACKAGED')
