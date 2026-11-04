"""User-reference-led vector concept. Only a design draft; no runtime/model publication."""
from pathlib import Path
import ast,json,shutil,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.path import Path as MPath
from matplotlib.patches import PathPatch,Rectangle,FancyBboxPatch,Circle,Ellipse
from matplotlib.transforms import Affine2D
from matplotlib.font_manager import FontProperties

P=Path(__file__).resolve().parent;P.mkdir(parents=True,exist_ok=True)
source=Path('C:/Users/allan/AppData/Local/Temp/codex-clipboard-72fea02d-e969-4ea3-8324-ccfd89acd503.png')
reference=P/'UserReference.png'
if not reference.exists():shutil.copy2(source,reference)
matplotlib.rcParams['svg.fonttype']='path'
regular=FontProperties(fname='C:/Windows/Fonts/msyh.ttc')
bold=FontProperties(fname='C:/Windows/Fonts/msyhbd.ttc')
paper='#f7f7f2';ink='#25343a';muted='#63747a';accent='#467b79';hair='#ccd4d2';fill='#849092'
fig=plt.figure(figsize=(20,14),dpi=140,facecolor=paper)
ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,2000);ax.set_ylim(1400,0);ax.axis('off')
# Reuse vector layout primitives, not the rejected draft's shape.
helper=P.parent/'CrescentDesignDraft01/draw_design.py'
tree=ast.parse(helper.read_text('utf-8'))
defs=ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'text','line','path','patch','dot_label'}],type_ignores=[])
exec(compile(defs,str(helper),'exec'),globals())

# The left member of the supplied pair provides the silhouette reference.
# Its decoration, spear tip, long shaft, text and mirrored second axe are not part of this component.
outline=[('M',114,46),
    ('C',84,43,52,78,49,118),('C',46,161,69,200,109,218),
    ('C',95,204,94,191,100,177),('C',109,160,131,155,148,157),
    ('C',151,158,150,174,150,187),('L',150,240),('L',181,240),('L',181,182),
    ('C',181,167,180,161,187,160),('C',202,160,216,167,228,172),
    ('C',225,155,218,138,205,130),('C',192,121,178,117,164,115),
    ('C',138,113,117,105,112,88),('C',108,74,110,59,114,46),('Z',)]
shape=path(outline)
bevel=path([('M',114,46),('C',84,43,52,78,49,118),('C',46,161,69,200,109,218),
    ('C',88,198,75,174,77,137),('C',77,100,94,70,114,46),('Z',)])
# Gentle inner-edge highlight ties the two concave transitions into the central shoulder.
upper=path([('M',110,74),('C',111,105,132,118,162,120),('C',191,121,211,137,222,157)])
lower=path([('M',98,205),('C',87,180,101,157,131,152),('C',143,150,156,155,162,159)])
root_left=path([('M',143,116),('C',146,128,146,144,145,154),('C',144,165,155,172,155,187),('L',155,229)])
root_right=path([('M',181,119),('C',180,132,180,146,180,157),('C',179,169,176,179,176,192),('L',176,229)])
# A restrained flat machined cheek on the thick central shoulder.
cheek=path([('M',152,123),('C',158,123,169,124,174,126),('L',174,149),
            ('C',167,148,159,148,153,149),('C',151,141,151,132,152,123),('Z',)])

text(65,48,'钩月斧刃',35,weight=True)
text(315,60,'参考形态修订 · 草案 02',22,muted)
text(1930,60,'REFERENCE STUDY  /  02',14,muted,ha='right')
text(68,112,'宽月牙刃面  /  上下双凹过渡  /  短后钩  /  直轴接颈',17,muted)
line([(65,166),(1935,166)],ink,1.2)
line([(1035,210),(1035,1232)],hair,.9);line([(1448,210),(1448,920)],hair,.9)
text(68,203,'01  正面 · 轮廓与材质分区',19,weight=True)
text(1090,203,'02  侧视厚度',19,weight=True)
text(1492,203,'03  刃根与接颈',19,weight=True)

main=Affine2D().scale(3.5).translate(-75,170)
patch(shape,main,fill,width=1.7)
patch(bevel,main,'#edf1ef','#4e5e63',.95,z=4)
for p in [upper,lower]:patch(p,main,edge='#c3cecc',width=1.,z=5)
for p in [root_left,root_right]:patch(p,main,edge='#b8c5c3',width=.85,z=5)
patch(cheek,main,'#768385','#536669',.8,z=5)
# The existing stock's connector will control final dimensions during modeling.
line([main.transform((143,229)),main.transform((188,229))],accent,.9,(0,(5,4)))
ghost=path([('M',150,240),('L',150,264),('M',181,240),('L',181,264)])
patch(ghost,main,edge=hair,width=1,z=2)

dot_label(1,main.transform((77,69)),(683,301),(750,301),'宽月牙轮廓','外刃饱满，上下端收尖')
dot_label(2,main.transform((215,147)),(714,655),(750,655),'短后钩与厚肩','刃根直接汇入接颈')
dot_label(3,main.transform((176,226)),(710,1000),(750,1000),'竖直接颈','下端按原装接口适配')
text(155,1155,'上下内凹线共同收束刃根',15,accent,weight=True)
text(155,1194,'参考原图的整体比例，表面采用现代碳钢分区。',13.5,muted)

# Same-height side projection: thin blade flares into a thick central cheek, then stock neck.
side_local=path([('M',0,46),('C',-2,62,-4,81,-4,103),('C',-4,112,-8,113,-8,123),
    ('L',-8,157),('C',-8,168,-6,175,-6,183),('L',-6,240),('L',6,240),('L',6,183),
    ('C',6,175,8,168,8,157),('L',8,123),('C',8,113,4,112,4,103),('C',4,81,2,62,0,46),('Z',)])
side_x=1245;side_t=Affine2D().scale(3.5).translate(side_x,170)
patch(side_local,side_t,'#bfc9c8',width=1.3)
line([(side_x,311),(side_x,1040)],'#9fadaa',.7,(0,(9,4,2,4)))
line([(side_x-36,971.5),(side_x+36,971.5)],accent,.9,(0,(5,4)))
line([(side_x+16,454),(1320,454)],accent,.8);text(1294,411,'薄刃面',13,muted)
line([(side_x+28,665),(1320,665)],accent,.8);text(1294,622,'中央厚肩',13,muted)
text(1090,1128,'薄刃 → 厚肩 → 接颈',14,accent,weight=True)
text(1090,1163,'侧视表达体积关系\n尺寸以后续原模接口为准',13,muted)

# A genuine crop of the same shape, showing both concave roots and the straight connector.
clip=Rectangle((1490,282),435,580,facecolor='none',edgecolor='none',transform=ax.transData);ax.add_patch(clip)
zoom=Affine2D().scale(3.3).translate(1492-98*3.3,290-82*3.3)
patch(shape,zoom,fill,width=1.5,clip=clip)
for p in [upper,lower]:patch(p,zoom,edge='#c3cecc',width=1.,clip=clip,z=5)
for p in [root_left,root_right]:patch(p,zoom,edge='#b8c5c3',width=.9,clip=clip,z=5)
patch(cheek,zoom,'#768385','#536669',.8,clip=clip,z=5)
for x,y,label in [(115,113,'A'),(163,139,'B'),(164,219,'C')]:
    xp,yp=zoom.transform((x,y))
    ax.add_patch(Circle((xp,yp),12,facecolor=paper,edgecolor=accent,lw=.9,zorder=8))
    ax.text(xp,yp,label,ha='center',va='center',color=accent,fontsize=10,fontproperties=bold,zorder=9)
text(1494,884,'A 双凹刃根    B 一体厚肩    C 直轴接颈',12,muted)

line([(1490,934),(1935,934)],hair,.9);text(1492,963,'截面关系',16,weight=True)
for x,label,w,h in [(1575,'A  刃根',105,17),(1735,'B  厚肩',105,42),(1875,'C  接颈',64,32)]:
    box=FancyBboxPatch((x-w/2,1040-h/2),w,h,boxstyle=f'round,pad=0,rounding_size={min(h/2-1,10)}',
                      facecolor='#c5cfce',edgecolor=ink,lw=1.2)
    ax.add_patch(box);text(x,1081,label,12.5,muted,ha='center')
text(1492,1144,'刃根加厚，内圆角连续过渡；',13,muted)
text(1492,1177,'接颈与握柄保持同一竖直轴。',13,muted)

line([(65,1265),(1935,1265)],ink,1.)
ax.add_patch(Rectangle((68,1305),25,25,facecolor='#454e50',edgecolor=ink,lw=.7));text(108,1302,'石墨灰碳钢',14)
ax.add_patch(Rectangle((300,1305),25,25,facecolor='#edf0ef',edgecolor=muted,lw=.7));text(340,1302,'银色磨刃',14)
text(1930,1302,'用户图片形态参考 · 当前为二维草案',14,muted,ha='right')

name='Crescent_ReferenceShape_Draft02'
fig.savefig(P/(name+'.png'),dpi=140,facecolor=paper)
fig.savefig(P/(name+'.svg'),facecolor=paper);plt.close(fig)
(P/'design.json').write_text(json.dumps({'status':'draft_awaiting_shape_review','revision':'reference_shape_02_20261104',
    'source':'draw_design.py','reference':'UserReference.png','reference_sha256':hashlib.sha256(reference.read_bytes()).hexdigest(),
    'reference_role':'left axe head silhouette; paired object and its text are not instructions',
    'retained_shape_features':['broad crescent outer blade','concave upper and lower root transition','short down-curved rear poll','straight neck axis'],
    'finish':'modern graphite carbon steel face and satin silver ground edge',
    'outline':outline,'coordinate_system':'concept coordinates, not final dimensions','runtime_assets_modified':False,
    'next_stage':'user shape acceptance, then model with the original mounting interface'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('REFERENCE_DRAFT_SAVED '+str(P/(name+'.png')))
