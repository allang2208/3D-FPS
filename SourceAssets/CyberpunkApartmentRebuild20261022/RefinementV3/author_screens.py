"""Manufactured device UI textures with readable labels, panels and graphs."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
root=Path(__file__).resolve().parent;out=root/'Textures';out.mkdir(exist_ok=True)
font='C:/Windows/Fonts/consola.ttf'
def f(size):return ImageFont.truetype(font,size)
for name in ('OfficeUI','WorkoutUI'):
 im=Image.new('RGB',(1536,864),(8,13,20));d=ImageDraw.Draw(im)
 cyan=(57,171,193);muted=(92,116,135);white=(184,204,213);line=(30,49,66)
 d.rounded_rectangle((24,24,1512,840),radius=14,outline=line,width=2)
 d.text((54,44),'NEXUS / LOCAL WORKSPACE' if name=='OfficeUI' else 'PULSE / TRAINING SYSTEM',font=f(32),fill=white)
 d.text((1230,50),'CONNECTED',font=f(23),fill=cyan)
 d.line((46,100,1490,100),fill=line,width=2)
 if name=='OfficeUI':
  for i,s in enumerate(('OVERVIEW','PROJECTS','TERMINAL','NETWORK','ARCHIVE')):
   y=140+i*77
   if i==0:d.rounded_rectangle((48,y-10,260,y+40),radius=6,fill=(22,45,58))
   d.text((65,y),s,font=f(23),fill=cyan if i==0 else muted)
  for box in ((292,128,1055,500),(1080,128,1480,500),(292,526,1480,778)):d.rounded_rectangle(box,radius=10,outline=line,width=2)
  d.text((320,153),'NEURAL LINK / THROUGHPUT',font=f(24),fill=white)
  for y in range(225,480,50):d.line((320,y,1020,y),fill=line)
  pts=[(320+i*7,370-(((i*17)%53)+((i*7)%41))) for i in range(101)]
  d.line(pts,fill=cyan,width=3)
  d.text((1102,158),'SYSTEM STATUS',font=f(23),fill=white)
  for i,s in enumerate(('CPU  24%','MEM  38%','GPU  16%','LINK  SECURE')):
   y=220+i*63;d.text((1102,y),s,font=f(25),fill=muted)
   d.rectangle((1105,y+34,1427,y+41),fill=line);d.rectangle((1105,y+34,1150+i*32,y+41),fill=cyan)
  for i,s in enumerate(('> connect harbor.local --secure','  identity verified / studio-09','> mount archive / shared / projects','  sync complete: 128 objects','> _')):
   d.text((320,551+i*40),s,font=f(24),fill=cyan if i in (0,4) else muted)
 else:
  for i,(value,label) in enumerate((('06.0','KM/H'),('124','HEART RATE'),('18:42','SESSION'),('2.10','DISTANCE KM'))):
   x=65+i*365;d.text((x,155),value,font=f(70),fill=white);d.text((x+3,250),label,font=f(24),fill=cyan)
  d.text((65,341),'STEADY STATE / ZONE 02',font=f(28),fill=white)
  for y in range(420,685,55):d.line((65,y,1470,y),fill=line)
  pts=[(65+i*10,570-((i*31)%37)-35*((i//12)%2)) for i in range(141)]
  d.line(pts,fill=cyan,width=4)
  for x,s in [(65,'WARM UP'),(475,'INTERVALS'),(885,'COOL DOWN')]:
   d.rounded_rectangle((x,720,x+350,786),radius=8,fill=(22,45,58));d.text((x+35,740),s,font=f(25),fill=white)
 im.save(out/('T_AP_'+name+'.png'))
print('DEVICE_UI_TEXTURES_AUTHORED')
