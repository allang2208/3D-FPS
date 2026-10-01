"""Original PBR materials and industrial markings, authored without rendering."""
import json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored/Textures';OUT.mkdir(parents=True,exist_ok=True)
N=1024;W=4096;H=2048;rng=np.random.default_rng(930184)
y,x=np.mgrid[0:N,0:N].astype(np.float32)/N
base=np.zeros((H,W,3),np.uint8);normal=np.full_like(base,(128,128,255));orm=np.full_like(base,(255,160,0));rects={}
def noise(n):
    im=Image.fromarray((rng.random((n,n))*255).astype(np.uint8))
    return np.array(im.resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)/255
def srgb(a):return np.where(a<=.0031308,a*12.92,1.055*np.maximum(a,0)**(1/2.4)-.055)
scan_path=ROOT.parents[1]/'BlastFurnace20260923/Authored/Textures/BlastFurnace_WroughtIron_Height.png'
with Image.open(scan_path) as im:scan=np.array(im.convert('L'),dtype=np.float32)/255
# Copy decoded pixels before closing PIL; integer box downsample avoids the old
# file-backed resize issue documented in the furnace production notes.
sy,sx=scan.shape;scan=scan[:sy//N*N,:sx//N*N].reshape(N,sy//N,N,sx//N).mean(axis=(1,3))
def tile(index,name,color,height,rough,metal,ao=1,scale=10):
    X=(index%4)*N;Y=(index//4)*N
    base[Y:Y+N,X:X+N]=np.clip(srgb(np.asarray(color))*255,0,255).astype(np.uint8)
    dy,dx=np.gradient(np.asarray(height,dtype=np.float32))
    v=np.stack((-dx*scale,dy*scale,np.ones_like(dx)),axis=-1);v/=np.linalg.norm(v,axis=-1,keepdims=True)
    normal[Y:Y+N,X:X+N]=np.clip((v*.5+.5)*255,0,255).astype(np.uint8)
    for c,data in enumerate((ao,rough,metal)):orm[Y:Y+N,X:X+N,c]=np.clip(np.asarray(data)*255,0,255).astype(np.uint8)
    rects[name]=[X+8,Y+8,X+N-8,Y+N-8]

# Painted surfaces: paint remains dielectric. Chips expose steel; oxidised recesses
# stay non-metallic. Wear is biased toward the perimeter and the lower drainage edge.
for i,name,rgb in [(0,'graphite',(.047,.054,.052)),(1,'teal',(.055,.110,.105)),(2,'ochre',(.28,.175,.043))]:
    macro=noise(15);grain=noise(640);mid=noise(120)
    edge=np.minimum.reduce([x,1-x,y,1-y]);mask=np.clip((.012+(mid-.5)*.029+(macro-.5)*.025-edge)*160,0,1)
    canvas=Image.new('L',(N,N));d=ImageDraw.Draw(canvas)
    for j in range(120):
        px=int(rng.integers(14,N-14));py=int(rng.integers(14,N-14))
        if min(px,py,N-px,N-py)>90 and rng.random()<.93:continue
        d.line((px,py,px+int(rng.integers(-18,35)),py+int(rng.integers(-8,28))),fill=int(rng.integers(60,230)),width=1 if j%5 else 2)
    mask=np.maximum(mask,np.array(canvas,np.float32)/255)
    ox=np.clip((macro*.55+scan*.45-.40)*2.9,0,.96)*mask
    c=np.asarray(rgb)[None,None,:]*(.88+macro[:,:,None]*.23+grain[:,:,None]*.055)
    c=c*(1-mask[:,:,None])+np.array((.43,.46,.45))*mask[:,:,None]
    c=c*(1-ox[:,:,None])+np.stack((.12+mid*.07,.041+mid*.025,.012+mid*.009),-1)*ox[:,:,None]
    dirt=np.clip((y-.68)*.9,0,.2)*(.3+macro*.7)
    c*=1-dirt[:,:,None]
    tile(i,name,c,grain*.011+mid*.005-mask*.045+ox*(.008+scan*.04),.44+grain*.09+ox*.28+dirt,mask*(1-ox),1-ox*.06)

fine=noise(880);cloud=noise(60)
brushed=np.array(Image.fromarray((rng.random((32,N))*255).astype(np.uint8)).resize((N,N),Image.Resampling.BILINEAR),np.float32)/255
steel=(.40+.075*brushed+.012*fine+.025*cloud)[:,:,None]*np.array((.96,1,1.01))
tile(3,'steel',steel,fine*.003+brushed*.018,.28+.14*brushed+.028*cloud,.96)
tile(4,'chrome',(.53+.035*fine+.015*cloud)[:,:,None]*np.array((.97,.99,1.02)),fine*.0008,.14+.045*cloud,.99)
rubber=(.012+.003*cloud+.001*fine)[:,:,None]*np.array((.97,1,1))
tile(5,'rubber',rubber,fine*.022,.69+cloud*.14,0)
tile(6,'soot',(.017+.011*cloud)[:,:,None]*np.array((1.04,.98,.92)),fine*.027+cloud*.016,.85+fine*.08,0,1-cloud*.05)
tile(7,'labels',np.ones((N,N,3))*.64,np.zeros((N,N)),.53,0)

art=Image.fromarray(base);draw=ImageDraw.Draw(art)
def font(size,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('consolab.ttf' if bold else 'consola.ttf'),size)
def panel(name,rect,background=(186,184,166)):
    rects[name]=[3072+rect[0],1024+rect[1],3072+rect[2],1024+rect[3]]
    r=rects[name];draw.rectangle(r,fill=background);draw.rectangle([r[0]+3,r[1]+3,r[2]-3,r[3]-3],outline=(38,41,37),width=3);return r
def words(r,lines,sizes):
    for i,(line,size) in enumerate(zip(lines,sizes)):
        draw.text(((r[0]+r[2])/2,r[1]+(i+.5)*(r[3]-r[1])/len(lines)),line,font=font(size,i==0),anchor='mm',fill=(29,34,32))
r=panel('door_plate',(20,20,1004,215));words(r,['THERMAL TREATMENT / CHAMBER','SERVICE ISOLATION  |  COLD STANDBY','F-3   /   LOCK BEFORE START'],[48,33,35])
r=panel('trolley_plate',(20,236,1004,390));words(r,['CHARGING TRANSFER TROLLEY','TC-02    |    BRAKE BEFORE LOADING'],[47,32])
r=panel('waste_plate',(20,414,1004,600),(184,143,48));words(r,['MEDICAL WASTE','KEEP LID CLOSED  /  ISOLATED'],[64,38])
r=panel('hazard',(20,620,1004,716),(185,144,43))
for px in range(r[0]-90,r[2],120):draw.polygon([(px,r[1]),(px+52,r[1]),(px+146,r[3]),(px+94,r[3])],fill=(29,33,31))
r=panel('service',(20,738,580,1002));words(r,['HYDRAULIC DRIVE','MANUAL ISOLATION','RELEASE PRESSURE','BEFORE SERVICE'],[33,31,28,28])
r=panel('gauge',(605,742,855,992));cx=(r[0]+r[2])/2;cy=(r[1]+r[3])/2
draw.ellipse((cx-120,cy-120,cx+120,cy+120),fill=(192,191,174),outline=(46,44,38),width=3)
for j in range(31):
    a=math.radians(135+j*9);R=102;L=15 if j%5==0 else 8
    draw.line((cx+math.cos(a)*(R-L),cy+math.sin(a)*(R-L),cx+math.cos(a)*R,cy+math.sin(a)*R),fill=(28,30,29),width=3 if j%5==0 else 2)
draw.text((cx,cy+42),'bar',font=font(22),anchor='mm',fill=(25,29,27))
draw.text((cx-76,cy+66),'0',font=font(20),anchor='mm',fill=(25,29,27))
r=panel('bio',(878,746,1000,996),(184,143,48))
draw.text(((r[0]+r[2])/2,r[1]+110),'!',font=font(102,True),anchor='mm',fill=(22,28,25))
draw.text(((r[0]+r[2])/2,r[3]-35),'BIO',font=font(32,True),anchor='mm',fill=(22,28,25))
# Artwork is matte printed metal; the paint chips on other tiles remain independent.
base=np.array(art)
for suffix,array in [('BaseColor',base),('NormalGL',normal),('ORM',orm)]:Image.fromarray(array).save(OUT/('T_IncineratorEquipment_'+suffix+'.png'))
(ROOT/'Authored/atlas.json').write_text(json.dumps({'size':[W,H],'rects':rects,'seed':930184,'color_workflow':'Linear albedo encoded to sRGB once; labels drawn in display sRGB','provenance':'Original procedural PBR/signage; corrosion microheight reuses local WroughtIron derivative from owned Sharur Normandy Village T_MetalRust_00A. Project use only; source licence retained with original asset.', 'scan_source':str(scan_path)},indent=2),encoding='utf-8')
print('EQUIPMENT_TEXTURES_AUTHORED',W,H,flush=True)
