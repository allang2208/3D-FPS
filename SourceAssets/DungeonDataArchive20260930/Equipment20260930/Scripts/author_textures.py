"""Original 4K shared PBR atlas, with edge-biased wear and readable instrument printing."""
from pathlib import Path
import json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
N=1024;W=H=4096;rng=np.random.default_rng(930441)
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
base=np.zeros((H,W,3),np.uint8);normal=np.full_like(base,(128,128,255));orm=np.full_like(base,(255,170,0));rects={}
def noise(n):return np.array(Image.fromarray((rng.random((n,n))*255).astype(np.uint8)).resize((N,N),Image.Resampling.BICUBIC),np.float32)/255
def srgb(a):return np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
def tile(i,name,c,h,rough,metal,ao=1,scale=8):
 X=(i%4)*N;Y=(i//4)*N
 base[Y:Y+N,X:X+N]=np.clip(srgb(np.asarray(c))*255,0,255).astype(np.uint8)
 dy,dx=np.gradient(np.asarray(h,np.float32));v=np.stack((-dx*scale,dy*scale,np.ones_like(dx)),axis=-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
 normal[Y:Y+N,X:X+N]=np.clip((v*.5+.5)*255,0,255).astype(np.uint8)
 for channel,value in enumerate((ao,rough,metal)):orm[Y:Y+N,X:X+N,channel]=np.clip(np.asarray(value)*255,0,255).astype(np.uint8)
 rects[name]=[X+8,Y+8,X+N-8,Y+N-8]
for i,name,rgb in [(0,'green',(.075,.096,.082)),(1,'pale',(.24,.265,.225)),(2,'ivory',(.42,.405,.34)),(4,'graphite',(.023,.028,.025))]:
 macro=noise(13);mid=noise(97);fine=noise(720);edge=np.minimum.reduce([x,1-x,y,1-y])
 chips=np.clip((.0125+(mid-.5)*.007+(macro-.5)*.006-edge)*360,0,1)*np.clip((fine-.25)*2.3,0,1)
 canvas=Image.new('L',(N,N));d=ImageDraw.Draw(canvas)
 for j in range(115):
  px,py=rng.integers(12,N-12,2)
  if min(px,py,N-px,N-py)>60 and rng.random()<.94:continue
  d.line((int(px),int(py),int(px+rng.integers(-16,21)),int(py+rng.integers(-5,30))),fill=int(rng.integers(50,190)),width=1)
 chips=np.maximum(chips,np.array(canvas,np.float32)/255);oxid=np.clip((macro*.55+mid*.45-.42)*3.5,0,.97)*chips
 dirt=(np.clip(y-.75,0,.25)*.6+np.clip(.12-macro,0,.12))
 c=np.array(rgb)[None,None,:]*(.92+macro[:,:,None]*.055+mid[:,:,None]*.065+fine[:,:,None]*.04)
 c=c*(1-chips[:,:,None])+np.array((.37,.38,.35))*chips[:,:,None]
 c=c*(1-oxid[:,:,None])+np.stack((.12+mid*.045,.045+mid*.017,.012+mid*.008),-1)*oxid[:,:,None]
 c*=1-dirt[:,:,None]
 tile(i,name,c,fine*.010+mid*.002-chips*.025+oxid*.027,.54+fine*.10+oxid*.18+dirt,chips*(1-oxid),1-dirt*.10)
fine=noise(850);cloud=noise(40)
brushed=np.array(Image.fromarray((rng.random((24,N))*255).astype(np.uint8)).resize((N,N),Image.Resampling.BILINEAR),np.float32)/255
tile(3,'steel',(.39+.08*brushed+.015*cloud)[:,:,None]*np.array((.98,1.,1.)),fine*.002+brushed*.012,.34+brushed*.19,.96)
tile(5,'rubber',(.009+cloud*.003)[:,:,None]*np.array((1,1.05,1.04)),fine*.014,.70+cloud*.12,0)
tile(6,'paper',(.39+cloud*.065)[:,:,None]*np.array((1.16,.9,.57)),fine*.022+cloud*.01,.81+fine*.08,0)
tile(7,'plastic',(.024+cloud*.005)[:,:,None]*np.array((1,1.1,1.04)),fine*.003,.38+cloud*.14,0)
for i,name,c in [(8,'red',(.40,.016,.009)),(9,'amber',(.65,.31,.035)),(10,'jade',(.018,.29,.11))]:
 tile(i,name,np.array(c)[None,None,:]*(.94+cloud[:,:,None]*.06),fine*.002,.24+cloud*.045,0)
tile(11,'screen',(.014+cloud*.0005)[:,:,None]*np.array((.76,1.2,1.)),fine*.0001,.22+cloud*.012,0)
for i,name in [(12,'labels'),(13,'meters'),(14,'tape_art'),(15,'keys')]:tile(i,name,np.ones((N,N,3))*.48,np.zeros((N,N)),.64,0)
art=Image.fromarray(base);d=ImageDraw.Draw(art)
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('consolab.ttf' if bold else 'consola.ttf'),n)
def panel(tile_i,name,r,bg=(201,195,168),border=True):
 X=(tile_i%4)*N;Y=(tile_i//4)*N;r=[X+r[0],Y+r[1],X+r[2],Y+r[3]];rects[name]=r
 d.rectangle(r,fill=bg)
 if border:d.rectangle((r[0]+3,r[1]+3,r[2]-3,r[3]-3),outline=(61,62,53),width=2)
 return r
def text(r,lines,sizes):
 for i,(line,size) in enumerate(zip(lines,sizes)):d.text(((r[0]+r[2])/2,r[1]+(i+.5)*(r[3]-r[1])/len(lines)),line,font=font(size,i==0),fill=(32,36,31),anchor='mm')
for i in range(10):
 r=panel(12,'index_'+str(i),(16+(i%2)*502,16+(i//2)*106,492+(i%2)*502,106+(i//2)*106));text(r,[f'RECORDS  {1981+i} / {21+i:03d}',f'ARCHIVE {chr(65+i//5)}-{i%5+1:02d}'],[28,23])
for name,r,lines,sizes in [
 ('server_plate',(16,566,1008,674),['DATA SYSTEMS / RACK 04','ISOLATE MAINS BEFORE SERVICE'],[46,29]),
 ('tape_plate',(16,696,1008,802),['MAGNETIC ARCHIVE'],[55]),
 ('console_plate',(16,824,1008,906),['CENTRAL DISPATCH / ARCHIVE CONTROL'],[34]),
 ('warning',(16,928,490,1008),['CAUTION / 220 V'],[31]),
 ('meter_label',(512,928,1008,1008),['LINE CURRENT'],[31])]:text(panel(12,name,r),lines,sizes)
for j,name in enumerate(['volts','amps']):
 r=panel(13,'dial_'+name,(14+j*504,15,498+j*504,499),border=False);cx=(r[0]+r[2])/2;cy=r[1]+280
 d.ellipse((cx-222,cy-242,cx+222,cy+202),outline=(80,78,64),width=2)
 for k in range(41):
  a=math.radians(205-k*5.75);rr=192;ll=21 if k%5==0 else 10
  d.line((cx+math.cos(a)*(rr-ll),cy-math.sin(a)*(rr-ll),cx+math.cos(a)*rr,cy-math.sin(a)*rr),fill=(27,30,28),width=3 if k%5==0 else 2)
  if k%10==0:d.text((cx+math.cos(a)*146,cy-math.sin(a)*146),str(k*10 if j==0 else k),font=font(23),anchor='mm',fill=(24,26,23))
 d.text((cx,cy+50),'V' if j==0 else 'A',font=font(56),anchor='mm',fill=(28,32,28))
 d.text((cx,cy+116),'VOLTAGE' if j==0 else 'LINE CURRENT',font=font(24),anchor='mm',fill=(29,32,27))
for j,name in enumerate(['system','channel','monitor','tape_feed','volume','emergency','switches','status']):
 c=j%4;row=j//4;r=panel(13,name,(14+c*252,524+row*240,246+c*252,750+row*240),border=False)
 text(r,[name.upper().replace('_',' '),'1   2   3' if j<5 else 'CONTROL'],[23,21])
for i in range(12):
 col=i%6;row=i//6;r=panel(14,'tape_'+str(i),(10+col*168,10+row*498,160+col*168,495+row*498),(200-i%3*6,191-i%4*4,160-i%2*8))
 d.rectangle((r[0]+6,r[1]+6,r[2]-6,r[1]+55),fill=(78,71,51) if i%3 else (99,43,30))
 d.text(((r[0]+r[2])/2,r[1]+31),f'MT-{i+1:02d}',font=font(25,True),anchor='mm',fill=(220,212,180))
 for k,line in enumerate(['DATA','ARCHIVE',f'{1983+i}',f'VOL {i*7+1:03d}','BACKUP']):d.text(((r[0]+r[2])/2,r[1]+87+k*53),line,font=font(23 if k!=1 else 21),anchor='mm',fill=(38,40,34))
 for k in range(32):
  xx=r[0]+12+k*3.6;d.line((xx,r[3]-70,xx,r[3]-20),fill=(37,39,31),width=1+(k%3==0))
chars='1234567890QWERTYUIOPASDFGHJKLZXCVBNM+-./: ENTER SHIFT CTRL SPACE'.split(' ')
keys=list('1234567890QWERTYUIOPASDFGHJKLZXCVBNM+-./:')+['ENTER','SHIFT','CTRL','SPACE','ESC','TAB']
for i,k in enumerate(keys):
 xx=(i%8)*128;yy=(i//8)*128;r=panel(15,'key_'+k,(xx+7,yy+7,xx+121,yy+121),(192,184,153),False)
 d.text(((r[0]+r[2])/2,(r[1]+r[3])/2),k,font=font(51 if len(k)==1 else 25,True),anchor='mm',fill=(38,42,35))
for i in range(16):
 xx=(i%8)*128;yy=768+(i//8)*128;r=panel(15,'button_'+str(i+1),(xx+7,yy+7,xx+121,yy+121),(200,180,125),False)
 d.text(((r[0]+r[2])/2,(r[1]+r[3])/2),str(i+1),font=font(53),anchor='mm',fill=(33,34,29))
base=np.array(art)
for suffix,data in [('BaseColor',base),('NormalGL',normal),('ORM',orm)]:Image.fromarray(data).save(OUT/('T_ArchiveEquipment_'+suffix+'.png'))
normal_dx=normal.copy();normal_dx[:,:,1]=255-normal_dx[:,:,1];Image.fromarray(normal_dx).save(OUT/'T_ArchiveEquipment_NormalDX.png')
(ROOT/'Authored/atlas.json').write_text(json.dumps(dict(size=[W,H],rects=rects,seed=930441,provenance='Original authored PBR surfaces and instrument/index artwork. Generated reference images are design guidance, not projected textures.',normal_convention='Blender OpenGL; separate DirectX normal for Unreal'),indent=2),encoding='utf-8')
print('ARCHIVE_TEXTURES_AUTHORED 4096 x 4096, BaseColor / NormalGL / NormalDX / ORM',flush=True)
