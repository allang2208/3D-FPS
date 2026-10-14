"""Original decorative engineering drawings; atlas proportions match the paper meshes."""
from pathlib import Path
import math
import numpy as np
from PIL import Image,ImageDraw,ImageFont

MAIN_RECT=(0.,1.-1454/2048.,1.,1.)
DETAIL_RECT=(0.,1.-2040/2048.,720/2048.,1.-1536/2048.)

def generate_atlas(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20261004)
    grain=rng.normal(0,.65,(2048,2048,1))
    base=np.array([236,231,213],dtype=float)[None,None,:]
    img=Image.fromarray(np.clip(base+grain,0,255).astype('uint8'),'RGB')
    ink=(49,53,51);muted=(112,115,105);accent=(130,76,52)
    fontfile='C:/Windows/Fonts/consola.ttf'
    def sheet(x,y,w,h,detail=False):
        # Design in a 2048x1454 physical sheet frame, scale uniformly.
        scale=w/2048;lay=Image.new('RGBA',(2048,1454),(0,0,0,0));d=ImageDraw.Draw(lay)
        def font(n):return ImageFont.truetype(fontfile,n)
        def label(pos,text,size=24,color=ink,anchor=None):d.text(pos,text,font=font(size),fill=color,anchor=anchor)
        def line(points,width=3,color=ink):d.line(points,fill=color,width=width,joint='curve')
        def poly(points,width=5):line(points+[points[0]],width)
        def dashed(a,b,dash=16,gap=9):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            for start in np.arange(0,length,dash+gap):
                end=min(start+dash,length);line([(a[0]+dx*start/length,a[1]+dy*start/length),(a[0]+dx*end/length,a[1]+dy*end/length)],2,muted)
        def dim(a,b,text,offset=30):
            line([a,b],2,muted);dx,dy=b[0]-a[0],b[1]-a[1];n=math.hypot(dx,dy);ux,uy=dx/n,dy/n
            for p,s in [(a,1),(b,-1)]:
                tip=(p[0]+s*14*ux,p[1]+s*14*uy)
                d.polygon([p,(tip[0]-5*uy,tip[1]+5*ux),(tip[0]+5*uy,tip[1]-5*ux)],fill=ink)
            mid=((a[0]+b[0])/2-offset*uy,(a[1]+b[1])/2+offset*ux)
            label(mid,text,26,ink,'mm')
        def hatch_ellipse(box):
            mask=Image.new('L',lay.size);md=ImageDraw.Draw(mask);md.ellipse(box,fill=255)
            pat=Image.new('RGBA',lay.size);pd=ImageDraw.Draw(pat)
            for z in range(int(box[0]-200),int(box[2]+300),15):pd.line([(z,box[1]),(z-200,box[3])],fill=muted,width=2)
            lay.paste(pat,(0,0),mask);d.ellipse(box,outline=ink,width=5)
        d.rectangle((28,28,2020,1426),outline=ink,width=3)
        line([(28,118),(2020,118)],3)
        label((62,48),'FIELD WORKSHOP  /  TOOL ENGINEERING',40)
        label((1970,65),'DWG 024-B' if not detail else 'DWG 024-C',28,ink,'rm')
        if not detail:
            label((125,160),'01  AXE - FRONT',28);label((742,160),'SIDE',28)
            # Curved axe handle and wedge-mounted head.
            poly([(414,410),(459,414),(451,570),(467,735),(499,960),(452,970),(422,752),(411,563)])
            line([(436,443),(432,603),(447,756),(475,943)],2,muted)
            poly([(174,278),(254,283),(328,326),(417,345),(486,335),(499,403),(468,435),(379,425),(298,450),(190,505),(163,455)])
            line([(196,292),(189,430),(206,488)],3,muted)
            d.ellipse((421,339,477,421),outline=ink,width=4)
            poly([(434,355),(461,355),(462,405),(436,405)],2)
            dashed((441,225),(441,990));dashed((125,379),(533,379))
            dim((118,278),(118,970),'560',-42);line([(129,278),(174,278)],2,muted);line([(129,970),(453,970)],2,muted)
            dim((165,225),(499,225),'180',-28)
            # Narrow side elevation clearly separate from front view.
            poly([(771,285),(807,285),(821,442),(810,471),(791,451),(782,338)])
            poly([(786,447),(809,447),(816,682),(839,954),(812,962),(790,689)])
            dashed((800,248),(800,995));dim((857,285),(857,962),'560',-50)
            label((650,1030),'A-A  /  HANDLE EYE',26)
            hatch_ellipse((648,1100,872,1212));d.ellipse((701,1128,817,1184),fill=(236,231,213),outline=ink,width=4)
            line([(752,1128),(760,1184)],7,accent);label((640,1250),'ASH HANDLE + STEEL WEDGE',20)
            # Pickaxe frontal arc, central socket and gently tapering handle.
            label((1120,160),'02  PICKAXE - FRONT',28)
            poly([(1110,420),(1210,341),(1370,311),(1482,319),(1531,300),(1584,323),(1710,317),(1855,365),(1934,420),(1815,381),(1690,365),(1590,371),(1569,433),(1484,432),(1466,374),(1330,368),(1218,383)])
            poly([(1502,427),(1552,427),(1560,650),(1555,956),(1514,967),(1505,665)])
            line([(1529,448),(1535,687),(1537,947)],2,muted)
            dashed((1530,230),(1530,1000));dashed((1100,348),(1940,348))
            dim((1120,250),(1930,250),'420',-28);dim((1970,330),(1970,967),'620',38)
            d.ellipse((1465,323,1596,380),outline=ink,width=3)
            line([(1585,400),(1740,520),(1880,520)],2,muted);label((1690,540),'TAPERED EYE',24)
            line([(486,380),(567,488),(639,488)],2,muted);label((518,511),'WEDGE',24)
            label((82,1050),'B-B  /  AXE SECTION',25)
            hatch_ellipse((91,1110,338,1216));d.ellipse((156,1134,272,1193),fill=(236,231,213),outline=ink,width=4)
            dim((90,1290),(338,1290),'52',25)
            label((993,1050),'03  FITTING DETAIL',25)
            poly([(1022,1120),(1110,1120),(1091,1255),(1043,1255)],4)
            for yy in range(1140,1240,18):line([(1042,yy),(1088,yy-8)],2,muted)
            label((962,1310),'DRIVE WEDGE',22)
            # Revision / assembly title block, actual readable labels.
            d.rectangle((1260,1100,2020,1426),outline=ink,width=3)
            for yy in (1180,1260,1340):line([(1260,yy),(2020,yy)],2)
            label((1284,1118),'AXE & PICKAXE / ASSEMBLY STUDY',27)
            label((1284,1202),'MATERIAL: FORGED STEEL / ASH',23)
            label((1284,1282),'SCALE NTS   UNITS mm   REV B',23)
            label((1284,1360),'FIELD TOOLS     SHEET 01 / 02',23)
        else:
            label((125,165),'HANDLE JOINT  /  EXPLODED DETAIL',38)
            poly([(850,300),(1010,300),(978,650),(880,650)],7)
            label((1070,418),'01  STEEL WEDGE',32)
            dashed((930,245),(930,1230))
            hatch_ellipse((550,720,1280,970));d.ellipse((776,774,1060,913),fill=(236,231,213),outline=ink,width=6)
            label((1390,812),'02  FORGED HEAD',32)
            poly([(853,1070),(1003,1070),(1025,1250),(870,1250)],6)
            label((1160,1160),'03  TIMBER TENON',32)
            dim((500,720),(500,970),'52',-46);dim((550,1014),(1280,1014),'90',36)
            line([(60,1332),(2020,1332)],3)
            label((76,1366),'JOINT STUDY   /   SECTION A-A    /    REV B',31)
        # A lower resolution detail sheet has the same physical aspect ratio.
        if w!=2048:lay=lay.resize((w,h),Image.Resampling.LANCZOS)
        img.paste(lay,(x,y),lay)
    sheet(0,0,2048,1454)
    sheet(0,1536,720,504,True)
    ImageDraw.Draw(img).rectangle((0,0,18,18),fill=(236,231,213))
    img.save(out/'T_WBKC_Blueprint_BaseColor.png')
    return img

if __name__=='__main__':generate_atlas(Path(__file__).resolve().parents[1]/'Authored/Textures')

