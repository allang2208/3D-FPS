"""Original vector UI layouts rasterized as engine textures, no preview render."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import math,json
R=Path(__file__).resolve().parent;O=R/'Textures';O.mkdir(exist_ok=True)
FONT='C:/Windows/Fonts/segoeui.ttf';BOLD='C:/Windows/Fonts/seguisb.ttf'
bg=(7,12,18);line=(35,54,65);white=(204,220,225);muted=(104,131,146);cyan=(76,190,204);amber=(218,162,94)
def font(n,b=False):return ImageFont.truetype(BOLD if b else FONT,n)
def text(d,p,s,n=26,c=white,b=False):d.text(p,s,font=font(n,b),fill=c)
def panel(d,rect):d.rounded_rectangle(rect,radius=12,fill=(12,23,31),outline=line,width=2)
def save(im,name):im.save(O/('T_AP13_'+name+'.png'))

atlas=Image.new('RGB',(2048,4096),bg)
for page in range(3):
 im=Image.new('RGB',(2048,1310),bg);d=ImageDraw.Draw(im)
 d.rectangle((0,0,2048,7),fill=cyan);text(d,(72,42),'BAYNET',58,white,True)
 text(d,(76,115),'NIGHTFALL / RESIDENTIAL CHANNEL',23,muted)
 text(d,(1580,60),'STUDIO 09',34,cyan,True);text(d,(1582,109),'CITY SERVICES NETWORK',19,muted)
 d.line((72,167,1976,167),fill=line,width=2)
 titles=['THE ESTUARY AFTER DARK','A CITY IN MOTION','BEYOND THE WATERLINE']
 subs=['Harbor connections / infrastructure briefing','Transit atlas / waterfront district','Architecture / the residential skyline']
 text(d,(72,200),titles[page],56,white,True);text(d,(76,280),subs[page],27,muted)
 panel(d,(72,348,1392,1090));panel(d,(1424,348,1976,1090))
 for k in range(7):d.line((110,408+k*90,1350,408+k*90),fill=(22,40,51),width=1)
 for k in range(10):d.line((120+k*133,380,120+k*133,1054),fill=(22,40,51),width=1)
 if page in (0,2):
  d.polygon([(110,927),(1350,870),(1350,1054),(110,1054)],fill=(12,39,51))
  for i in range(24):
   x=124+i*50;w=32+(i*17)%22;h=82+(i*113)%370;y=880-h
   d.rectangle((x,y,x+w,884),fill=(28+(i%3)*4,46+(i%4)*5,59+(i%4)*6),outline=(59,89,103),width=2)
   for xx in range(x+7,x+w-3,10):
    for yy in range(y+15,871,22):
     if (xx+yy+i*3)%7<4:d.rectangle((xx,yy,xx+3,yy+5),fill=amber if i%5 else cyan)
   if i in (4,12,19):d.rectangle((x-2,y+25,x+w+2,y+80),outline=cyan,width=3)
  for j in range(19):
   yy=916+j*6;x=142+(j*97)%1080;d.line((x,yy,x+35+(j%4)*12,yy),fill=(40,93,108),width=2)
  text(d,(128,382),'SOUTH BANK  /  CITY PROFILE',23,cyan)
  text(d,(128,1005),'WIDE WATER / CONNECTED SHORES',22,muted)
 else:
  routes=[[(140,930),(380,770),(620,770),(900,580),(1300,460)],[(140,510),(350,630),(710,630),(960,875),(1300,875)],[(300,1000),(490,860),(490,520),(730,410),(1180,410)]]
  for n,points in enumerate(routes):
   col=[cyan,amber,(143,153,208)][n];d.line(points,fill=col,width=7)
   for x,y in points:d.ellipse((x-11,y-11,x+11,y+11),fill=bg,outline=col,width=4)
  for p,label in [((155,950),'SOUTH QUAY'),((650,790),'ESTUARY'),((930,600),'NEXUS'),((1040,910),'PORT LOOP')]:text(d,p,label,24,white)
  text(d,(128,382),'DISTRICT CONNECTIONS',23,cyan)
 for i,(title,desc) in enumerate([('01 / WATERFRONT','A connected bay community'),('02 / RESIDENTIAL','Private space / shared skyline'),('03 / TRANSIT','Rail links across the estuary')]):
  yy=396+i*210;text(d,(1460,yy),title,25,cyan,True);text(d,(1460,yy+57),desc,22,white)
  d.line((1460,yy+140,1935,yy+140),fill=line,width=2)
 text(d,(1460,1030),'BAYNET  /  LOCAL EDITION',19,muted)
 d.rectangle((72,1136,1976,1140),fill=cyan)
 text(d,(76,1169),'NIGHTFALL RESIDENCES',30,white,True)
 text(d,(76,1222),'HARBOR LIFE    /    CITY SYSTEMS    /    ARCHITECTURE',22,muted)
 text(d,(1660,1194),f'PROGRAM 0{page+1}',24,cyan)
 atlas.paste(im,(0,page*1310))
save(atlas,'BaynetAtlas')

im=Image.new('RGB',(1536,908),bg);d=ImageDraw.Draw(im)
text(d,(54,34),'NEXUS / RESIDENT WORKSPACE',38,white,True)
text(d,(55,91),'FILES  /  PROJECTS  /  LOCAL SERVICES',20,muted);d.line((48,132,1488,132),fill=cyan,width=3)
for rect in [(48,164,1022,690),(1050,164,1488,690)]:panel(d,rect)
text(d,(80,194),'ARCHIVE / PROJECT DIRECTORY',27,cyan,True)
for i,(name,kind) in enumerate([('Estuary district notes','DOCUMENT'),('South bank route atlas','MAP'),('Nightfall interior systems','DESIGN'),('Harbor observation log','JOURNAL'),('Residential service index','LOCAL')]):
 yy=259+i*77;d.rounded_rectangle((80,yy,975,yy+59),radius=5,fill=(18,33,43));text(d,(100,yy+13),name,25);text(d,(790,yy+17),kind,18,muted)
text(d,(1083,200),'DEVICE CONTROL',24,cyan,True)
for i,s in enumerate(['Physical power switch','Local workspace','Automatic standby','Private terminal']):text(d,(1082,275+i*72),s,23,white)
text(d,(1083,628),'NODE / STUDIO-09',21,muted)
text(d,(60,727),'POWER',18,muted);text(d,(900,781),'RESIDENTIAL SYSTEM / NEXUS',21,muted)
save(im,'Office')

for name,w,h in [('Treadmill',1040,320),('Rower',640,416)]:
 im=Image.new('RGB',(w,h),bg);d=ImageDraw.Draw(im)
 text(d,(int(w*.06),int(h*.05)),'PULSE / RUN' if name=='Treadmill' else 'PULSE / ROW',int(h*.09),white,True)
 d.line((int(w*.06),int(h*.21),int(w*.94),int(h*.21)),fill=cyan,width=2)
 text(d,(int(w*.06),int(h*.26)),'ACTIVE SESSION',int(h*.055),muted)
 text(d,(int(w*.67),int(h*.50)),'MIN : SEC',int(h*.062),cyan)
 text(d,(int(w*.54),int(h*.86)),'LOCAL CONTROL',int(h*.05),muted)
 save(im,name)

im=Image.new('RGB',(512,212),bg);d=ImageDraw.Draw(im)
d.ellipse((24,29,170,175),outline=cyan,width=9);d.rectangle((80,10,113,93),fill=bg);d.line((97,28,97,96),fill=white,width=9)
text(d,(205,40),'POWER',54,white,True);text(d,(209,123),'PRESS  /  E',24,muted);save(im,'Control')
im=Image.new('RGB',(1024,256),bg);d=ImageDraw.Draw(im)
for i,(s,col) in enumerate([('POWER OFF',muted),('RUNNING',cyan),('STANDBY',amber),('PAUSED',amber)]):text(d,(20,i*64+7),s,41,col,True)
save(im,'States')
(R/'screen-source.json').write_text(json.dumps(dict(files=[p.name for p in O.glob('*.png')],original_vector_layouts=True,game_run=False,rendered=False),indent=2))
print('AP13_SCREEN_LAYOUTS_AUTHORED')
