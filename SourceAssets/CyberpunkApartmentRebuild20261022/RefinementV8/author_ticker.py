"""Original typography atlas; no borrowed advertising artwork."""
from PIL import Image,ImageDraw,ImageFont
from pathlib import Path
R=Path(__file__).resolve().parent;P=R.parents[2]
font=ImageFont.truetype(str(P/'Content/UI/GunsmithWorkbench/Fonts/JetBrainsMono-Medium.ttf'),66)
im=Image.new('RGB',(2048,512),(3,5,9));d=ImageDraw.Draw(im)
rows=['NEXUS  //  UPGRADE YOUR TOMORROW  //  ','ION  //  RECHARGE THE NIGHT  //  ','TIDELINE  //  BEYOND THE SHORE  //  ','AFTERHOURS  //  02:00  //  LIVE  //  ']
for i,(s,c) in enumerate(zip(rows,[(110,225,255),(255,179,75),(174,155,255),(255,110,221)])):
 d.text((42,i*128+27),s,font=font,fill=c)
 d.rectangle((20,i*128+18,28,i*128+110),fill=c)
im.save(R/'Textures/T_AP8_Ticker_BC.png')
(R/'campaigns.txt').write_text('\n'.join(rows),encoding='utf8')
