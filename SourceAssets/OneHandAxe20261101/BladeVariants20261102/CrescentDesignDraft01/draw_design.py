"""Editable vector design drawing; no game mesh or runtime assets are changed."""
from pathlib import Path
import math,json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Rectangle,FancyBboxPatch,Circle,Ellipse
from matplotlib.transforms import Affine2D
from matplotlib.font_manager import FontProperties

P=Path(__file__).resolve().parent;P.mkdir(parents=True,exist_ok=True)
matplotlib.rcParams['svg.fonttype']='path'
regular=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
bold=FontProperties(fname='C:/Windows/Fonts/msyhbd.ttc')
paper='#f7f7f2';ink='#25343a';muted='#63747a';accent='#467b79';hair='#ccd4d2';fill='#dce2e1'
fig=plt.figure(figsize=(20,14),dpi=140,facecolor=paper)
ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,2000);ax.set_ylim(1400,0);ax.axis('off')

def text(x,y,label,size=17,color=ink,weight=False,ha='left'):
    return ax.text(x,y,label,fontproperties=bold if weight else regular,fontsize=size,color=color,
                   ha=ha,va='top',linespacing=1.6)
def line(points,color=hair,width=1.,style='-'):
    points=np.asarray(points);ax.plot(points[:,0],points[:,1],color=color,lw=width,ls=style,solid_capstyle='round')
def path(commands):
    verts=[];codes=[]
    for command in commands:
        op,*values=command
        if op in ('M','L'):
            verts.append(tuple(values));codes.append(MPath.MOVETO if op=='M' else MPath.LINETO)
        elif op=='C':
            verts.extend(zip(values[::2],values[1::2]));codes.extend([MPath.CURVE4]*3)
        elif op=='Z':verts.append((0,0));codes.append(MPath.CLOSEPOLY)
    return MPath(verts,codes)
def arc(cx,cy,r,start,end):
    n=math.ceil(abs(end-start)/(math.pi/2));commands=[]
    for i in range(n):
        a=start+(end-start)*i/n;b=start+(end-start)*(i+1)/n
        k=4/3*math.tan((b-a)/4)
        x0,y0=cx+r*math.cos(a),cy+r*math.sin(a)
        x1,y1=cx+r*math.cos(b),cy+r*math.sin(b)
        commands.append(('C',x0-k*r*math.sin(a),y0+k*r*math.cos(a),
                          x1+k*r*math.sin(b),y1-k*r*math.cos(b),x1,y1))
    return commands
def patch(p,transform=None,face='none',edge=ink,width=1.7,clip=None,z=3):
    item=PathPatch(p,facecolor=face,edgecolor=edge,lw=width,joinstyle='round',capstyle='round',zorder=z)
    item.set_transform((transform or Affine2D())+ax.transData)
    ax.add_patch(item)
    if clip is not None:item.set_clip_path(clip)
    return item
def dot_label(number,anchor,elbow,end,label,sub):
    line([anchor,elbow,end],accent,1.1)
    ax.add_patch(Circle(anchor,3.2,facecolor=accent,edgecolor='none',zorder=8))
    x,y=end;ax.add_patch(Circle((x+13,y+31),13,facecolor=accent,edgecolor='none'))
    ax.text(x+13,y+31,str(number),ha='center',va='center',color='white',fontsize=11,fontproperties=bold)
    text(x+37,y+14,label,16,weight=True);text(x+37,y+49,sub,12.5,muted)

# Full silhouette is a single editable cubic outline. The shoulder is part of that outline.
cx,cy,r=430.,340.,225.
tipx=(225**2-217**2+516**2-430**2)/(2*(516-430))
angle=math.acos((tipx-cx)/r);top=(tipx,cy-r*math.sin(angle));bottom=(tipx,cy+r*math.sin(angle))
outline=[('M',*top)]+arc(cx,cy,r,-angle,-2*math.pi+angle)+[
    ('C',416,548,350,503,322,438),
    ('C',308,411,306,392,330,396),
    ('C',404,409,479,464,525,530),
    ('C',555,574,568,619,568,662),
    ('L',568,750),('L',632,750),('L',632,525),
    ('C',632,445,603,395,548,352),
    ('C',494,310,424,279,354,266),
    ('C',333,262,323,253,337,230),
    ('C',370,174,429,135,*top),('Z',)]
shape=path(outline)
# The ground edge tapers to zero width at both horns so it preserves their points.
end_angle=-2*math.pi+angle
bevel=[('M',*top)]+arc(cx,cy,r,-angle,end_angle)
for t in np.linspace(1,0,181):
    a=-angle+(end_angle+angle)*t;rr=r-14*math.sin(math.pi*t)
    bevel.append(('L',cx+rr*math.cos(a),cy+rr*math.sin(a)))
bevel.append(('Z',))
bevel=path(bevel)

# Overall sheet layout.
text(65,48,'钩月斧刃',35,weight=True)
text(315,60,'一体弧肩 · 形态草案 01',22,muted)
text(1930,60,'DESIGN STUDY  /  01',14,muted,ha='right')
text(68,112,'先确认月牙轮廓、肩部走向与厚度关系，再以原装接口约束建模。',17,muted)
line([(65,166),(1935,166)],ink,1.2)
line([(1035,210),(1035,1232)],hair,.9)
line([(1448,210),(1448,920)],hair,.9)
text(68,203,'01  正面轮廓',19,weight=True)
text(1090,203,'02  侧视厚度',19,weight=True)
text(1492,203,'03  弧肩局部',19,weight=True)

main=Affine2D().scale(1.2).translate(-120,140)
patch(shape,main,fill)
patch(bevel,main,'#fdfdf9',muted,.85,z=4)
# One restrained groove follows the crescent and ends before the shoulder.
grooveangle=math.radians(116)
groove=path([('M',cx+190*math.cos(-grooveangle),cy+190*math.sin(-grooveangle))]
            +arc(cx,cy,190,-grooveangle,-2*math.pi+grooveangle))
patch(groove,main,edge='#95a5a6',width=1.2,z=5)
# Surface guide lines show the turn of the shoulder into the neck; they are not seams.
flow1=path([('M',348,288),('C',430,304,504,343,550,392),('C',594,439,611,494,610,558),('L',610,710)])
flow2=path([('M',345,375),('C',426,398,489,444,535,501),('C',574,550,588,606,588,664),('L',588,710)])
patch(flow1,main,edge='#a4b2b1',width=.9,z=5);patch(flow2,main,edge='#a4b2b1',width=.9,z=5)
# Dashed final interface and a ghosted continuation identify the retained stock mating region.
line([main.transform((550,714)),main.transform((650,714))],accent,1.,(0,(5,4)))
ghost=path([('M',568,750),('L',568,800),('M',632,750),('L',632,800)])
patch(ghost,main,edge=hair,width=1.,z=2)
dot_label(1,main.transform((317.5,145.14)),(710,300),(750,300),'月牙大圆弧','上、下两端沿弧线收尖')
dot_label(2,main.transform((501,418)),(714,640),(750,640),'斜向展开的弧肩','宽面逐渐汇入接颈')
dot_label(3,main.transform((625,713)),(713,1000),(750,1000),'原装接颈','下端轮廓留给原模约束')
text(175,1162,'连续外轮廓',14,accent,weight=True)
text(175,1197,'月牙、肩部与斧颈作为同一个形体设计',13,muted)

# Side elevation: blade is thin; the shoulder grows in volume toward the retained neck.
sx=1245;top_y=float(main.transform(top)[1]);end_y=float(main.transform((0,750))[1])
side=path([('M',sx,top_y),('C',sx-8,390,sx-9,450,sx-9,520),
           ('C',sx-10,603,sx-17,673,sx-19,744),('C',sx-20,826,sx-18,924,sx-18,end_y),
           ('L',sx+18,end_y),('C',sx+18,924,sx+20,826,sx+19,744),
           ('C',sx+17,673,sx+10,603,sx+9,520),('C',sx+9,450,sx+8,390,sx,top_y),('Z',)])
patch(side,face='#dce2e1',width=1.3)
line([(sx,top_y-20),(sx,end_y+26)],'#9fadaa',.7,(0,(9,4,2,4)))
line([(sx-40,996),(sx+40,996)],accent,.9,(0,(5,4)))
line([(sx+12,439),(1320,439)],accent,.8);text(1294,399,'薄刃身',13,muted)
line([(sx+20,732),(1320,732)],accent,.8);text(1294,688,'饱满弧肩',13,muted)
text(1090,1128,'厚度连续过渡',14,accent,weight=True)
text(1090,1163,'此视图表达体积关系\n不作为尺寸定稿',13,muted)

# Enlarged shoulder cutout from exactly the same front-view paths.
clip=Rectangle((1490,280),435,595,facecolor='none',edgecolor='none',transform=ax.transData)
ax.add_patch(clip)
zoom=Affine2D().scale(1.28).translate(1485-305*1.28,294-230*1.28)
patch(shape,zoom,'#e2e7e5',clip=clip,width=1.5)
patch(flow1,zoom,edge='#98aaa7',width=1.0,clip=clip,z=5)
patch(flow2,zoom,edge='#98aaa7',width=1.0,clip=clip,z=5)
# Three section positions and generous inside-radius direction.
for a,b,label in [((367,279),(348,398),'A'),((524,339),(478,472),'B'),((568,686),(632,686),'C')]:
    a,b=zoom.transform(a),zoom.transform(b);line([a,b],accent,.85,(0,(4,4)))
    text(a[0]+8,a[1]-25,label,12,accent,True)
text(1500,887,'浅线为曲面走向，不是拼接缝',12.5,muted)

# The section study is kept separate from the material key.
line([(1490,934),(1935,934)],hair,.9)
text(1492,963,'截面关系',16,weight=True)
for x,label,w,h in [(1575,'A  刃根',105,17),(1735,'B  弧肩',105,40),(1875,'C  接颈',64,32)]:
    box=FancyBboxPatch((x-w/2,1040-h/2),w,h,boxstyle=f'round,pad=0,rounding_size={min(h/2-1,12)}',
                       facecolor='#dce2e1',edgecolor=ink,lw=1.2)
    ax.add_patch(box);text(x,1081,label,12.5,muted,ha='center')
text(1492,1144,'由薄面过渡为圆润肩部，',13.5,muted)
text(1492,1177,'再收束到原装接颈。',13.5,muted)
line([(65,1265),(1935,1265)],ink,1.)
ax.add_patch(Rectangle((68,1305),25,25,facecolor='#454e50',edgecolor=ink,lw=.7))
text(108,1302,'石墨灰碳钢',14)
ax.add_patch(Rectangle((300,1305),25,25,facecolor='#edf0ef',edgecolor=muted,lw=.7))
text(340,1302,'银色磨刃',14)
text(1930,1302,'仅外形草案 · 尚未建模 / 接入',14,muted,ha='right')

fig.savefig(P/'Crescent_IntegratedShoulder_Draft01.png',dpi=140,facecolor=paper)
fig.savefig(P/'Crescent_IntegratedShoulder_Draft01.svg',facecolor=paper)
plt.close(fig)
(P/'design.json').write_text(json.dumps({'status':'draft_awaiting_shape_review','scope':'2D crescent silhouette and integrated shoulder only',
    'source':'draw_design.py','outline':outline,'coordinate_system':'drawing coordinates, not final manufacturing dimensions',
    'mount_constraint':'retain accepted original hatchet mating interface at local Z=11.5 cm during subsequent modeling',
    'runtime_assets_modified':False,'next_stage':'model only after the user accepts this silhouette'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('DESIGN_DRAFT_SAVED '+str(P/'Crescent_IntegratedShoulder_Draft01.png'))
