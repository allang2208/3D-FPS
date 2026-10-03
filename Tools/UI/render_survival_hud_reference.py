"""Requested offline UI references. Exact project fonts/tokens; no UE launch or runtime QA."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math
import sys

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/SurvivalHUD20261003'
OUT.mkdir(parents=True,exist_ok=True)
FONTS=ROOT/'Content/UI/GunsmithWorkbench/Fonts'
PALETTE=dict(bg='#111111',glass='#1A1A1A',content='#121212',border='#444444',text='#E8E8E8',secondary='#B7B7B7',tertiary='#919191',gold='#C7AA70',health='#BD626D',healthdeep='#763B43',mana='#7194AC',manadeep='#36566E',hunger='#BEA06E',hungerdeep='#75613F',water='#8AAFA8',waterdeep='#466660',san='#AD9BBE',sandeep='#655773',warning='#F0BE71',danger='#FF8193')

def font(px,numeric=False,medium=False):
    name=('JetBrainsMono-' + ('Medium' if medium else 'Regular') + '.ttf') if numeric else ('NotoSansSC-'+('Medium' if medium else 'Regular')+'.otf')
    return ImageFont.truetype(str(FONTS/name),px)

def text(draw,pos,label,px=14,color='text',numeric=False,medium=False,right=False):
    f=font(px,numeric,medium)
    if right: pos=(pos[0]-draw.textlength(label,font=f),pos[1])
    draw.text(pos,label,font=f,fill=PALETTE.get(color,color),anchor='lt')

def track(image,x,y,width,height,ratio,kind):
    draw=ImageDraw.Draw(image)
    ratio=max(0,min(1,ratio))
    draw.rounded_rectangle((x,y,x+width,y+height),radius=3,fill=PALETTE['content'],outline=PALETTE['danger'] if ratio<=.25 and kind!='mana' else PALETTE['border'])
    if ratio<=0: return
    w=max(1,round((width-2)*ratio));h=max(1,height-2)
    light=PALETTE['warning'] if ratio<=.25 and kind in ('hunger','water','san') else PALETTE[kind]
    a=tuple(int(PALETTE[kind+'deep'][i:i+2],16) for i in (1,3,5));b=tuple(int(light[i:i+2],16) for i in (1,3,5))
    strip=Image.new('RGB',(w,h));sd=ImageDraw.Draw(strip)
    for i in range(w):
        t=i/max(1,w-1);sd.line((i,0,i,h),fill=tuple(round(p+(q-p)*t) for p,q in zip(a,b)))
    mask=Image.new('L',(w,h),0);ImageDraw.Draw(mask).rounded_rectangle((0,0,w-1,h-1),radius=2,fill=255)
    image.paste(strip,(x+1,y+1),mask)

def corner_accents(image,radius=10):
    # Same quarter-arc / 6px tangent recipe as ColdSteelHUDNavigation.
    scale=4;overlay=Image.new('RGBA',(image.width*scale,image.height*scale),(0,0,0,0));draw=ImageDraw.Draw(overlay)
    inset=.75;arc_radius=radius-inset
    for flipx in (False,True):
        for flipy in (False,True):
            points=[(radius+6,inset)]
            points += [(radius+arc_radius*math.cos(-math.pi*.5-i*math.pi*.5/8),radius+arc_radius*math.sin(-math.pi*.5-i*math.pi*.5/8)) for i in range(9)]
            points.append((inset,radius+6))
            points=[((image.width-1-x if flipx else x)*scale,(image.height-1-y if flipy else y)*scale) for x,y in points]
            draw.line(points,fill=PALETTE['gold'],width=5,joint='curve')
    overlay=overlay.resize(image.size,Image.Resampling.LANCZOS)
    image.paste(overlay,(0,0),overlay)

def hud(variant,values=(76,62,83,68,92),maximum=(200,250,100,100,100),refined=False):
    # Both candidates use the same 440px footprint and the same runtime information.
    width,height=440,(184 if refined else 208) if variant=='A' else 292
    image=Image.new('RGB',(width,height),PALETTE['glass']);draw=ImageDraw.Draw(image)
    draw.rounded_rectangle((0,0,width-1,height-1),radius=10,outline=PALETTE['border'])
    low=values[2]==0 or values[3]==0
    warning='饥饿 · 脱水  |  每秒损失 10% 最大生命' if values[2]==values[3]==0 else '饥饿  |  每秒损失 10% 最大生命' if values[2]==0 else '脱水  |  每秒损失 10% 最大生命' if values[3]==0 else '精神状态低下' if values[4]<=25 else '补充食物与水分' if min(values[2:4])<=25 else ''
    caption=['生命','魔法','饥饿度','缺水度','SAN'];kinds=['health','mana','hunger','water','san']
    top,bottom=10,height-10
    warningheight=24 if warning else 0
    if variant=='A':
        resourceheight=(height-20-(38 if refined else 44)-(12 if refined else 10)-warningheight)/2
        levelbottom=top+resourceheight*2
    else:
        resourceheight=(height-20-warningheight)/5
        levelbottom=top+resourceheight*5
    mid=(top+levelbottom)/2
    badge_top,badge_bottom=(mid-28,mid+28) if refined else (top,levelbottom)
    draw.rounded_rectangle((12,badge_top,76,badge_bottom),radius=8,fill=PALETTE['content'],outline=PALETTE['gold'])
    text(draw,(44,mid-21),'等级',12,'gold',right=False)
    label='12';text(draw,(44-draw.textlength(label,font=font(20,True,True))/2,mid+1),label,20,numeric=True,medium=True)
    # Centre the identity label in its 64px column.
    label_width=draw.textlength('等级',font=font(12));draw.rectangle((13,mid-22,75,mid-5),fill=PALETTE['content']);text(draw,(44-label_width/2,mid-21),'等级',12,'gold')
    for i in range(2):
        y=top+i*resourceheight+7
        text(draw,(94,y),caption[i],14,'secondary')
        text(draw,(422,y),f'{values[i]:.0f} / {maximum[i]:.0f}',16,numeric=True,right=True)
        track(image,94,round(y+24),328,10,values[i]/maximum[i],kinds[i])
    if variant=='A':
        if refined:draw.line((12,levelbottom+6,428,levelbottom+6),fill=PALETTE['border'],width=1)
        y=round(levelbottom+14)
        for j in range(3):
            x=12+j*142
            text(draw,(x,y),caption[j+2],12,'secondary')
            val=values[j+2];color='danger' if val==0 else 'warning' if val<=25 else 'text'
            text(draw,(x+132,y),str(val),14,color,numeric=True,right=True)
            track(image,x,y+24,132,6,val/100,kinds[j+2])
    else:
        for j in range(3):
            y=round(top+(j+2)*resourceheight+7)
            text(draw,(94,y),caption[j+2],12,'secondary')
            val=values[j+2];color='danger' if val==0 else 'warning' if val<=25 else 'text'
            text(draw,(422,y),f'{val} / 100',14,color,numeric=True,right=True)
            track(image,94,y+24,328,10,val/100,kinds[j+2])
    if warning:text(draw,(12,height-26),warning,12,'danger' if low else 'warning')
    if refined:corner_accents(image)
    return image

def backdrop(width=716,height=424):
    im=Image.new('RGB',(width,height));d=ImageDraw.Draw(im)
    for y in range(height):
        g=round(27+(1-abs(y-height*.38)/height)*9);d.line((0,y,width,y),fill=(g,g,g))
    # Abstract dungeon blockout only; it is deliberately not a fabricated game screenshot.
    van=(width*.6,height*.42)
    d.polygon([(0,0),(width*.29,height*.08),(width*.29,height*.65),(0,height)],fill='#282828')
    d.polygon([(width,0),(width*.8,height*.08),(width*.8,height*.65),(width,height)],fill='#252525')
    d.rectangle((width*.29,height*.08,width*.8,height*.65),fill='#313131')
    d.rectangle((width*.49,height*.24,width*.64,height*.65),fill='#171717',outline='#444444',width=2)
    for i in range(8):
        xx=i*width/7;d.line((van[0],van[1],xx,height),fill='#393939')
    for y in (height*.72,height*.86):d.line((0,y,width,y),fill='#3B3B3B')
    d.line((width*.38,0,width*.38,height*.6),fill='#505050',width=3)
    d.line((width*.72,0,width*.72,height*.62),fill='#484848',width=3)
    d.rectangle((width*.42,height*.12,width*.67,height*.135),fill='#68675F')
    text(d,(16,16),'布局参考 · 非实机截图',11,'tertiary')
    return im

def make_board():
    board=Image.new('RGB',(1600,1130),PALETTE['bg']);d=ImageDraw.Draw(board)
    text(d,(48,30),'COLD STEEL / SURVIVAL',12,'gold',numeric=True)
    text(d,(48,64),'生存状态 · 两版布局',24,medium=True)
    text(d,(48,107),'同一套生存数据，两种信息密度。保留生命、魔法、等级与现有快捷栏避让。',14,'secondary')
    d.line((48,144,1552,144),fill=PALETTE['border'])
    for variant,x,title,description in [('A',48,'紧凑横排','生命与魔法保持主位，食物、水分与 SAN 集中在底部。'),('B',836,'纵向记录','五项资源逐行呈现，当前值与上限更容易同时阅读。')]:
        text(d,(x,172),variant,24,'gold',numeric=True,medium=True)
        text(d,(x+44,172),title,20,medium=True)
        text(d,(x,209),description,12,'secondary')
        scene=backdrop();card=hud(variant,(152,155,83,68,92))
        scene.paste(card,(16,424-card.height-20));board.paste(scene,(x,240))
        text(d,(x,684),'A · 440 × 208 px  /  默认布局' if variant=='A' else 'B · 440 × 292 px  /  可切换布局',12,'tertiary',numeric=False)
        text(d,(x,725),'耗尽状态',16,medium=True)
        alert=hud(variant,(90,155,0,0,72));board.paste(alert,(x,758))
        right_x=x+462
        text(d,(right_x,774),'任一归零',14,'danger',medium=True)
        text(d,(right_x,804),'每秒 −10% 最大生命',12,'secondary')
        text(d,(right_x,838),'同时归零不叠加',12,'tertiary')
        text(d,(right_x,878),'SAN ≤25',14,'warning',numeric=True)
        text(d,(right_x,910),'显示「精神状态低下」',12,'secondary')
        text(d,(right_x,940),'暂不追加失控惩罚',12,'tertiary')
    d.line((48,1073,1552,1073),fill=PALETTE['border'])
    text(d,(48,1091),'工程字体：Noto Sans SC / JetBrains Mono  ·  中性黑灰玻璃 / 银灰细线 / 淡金等级身份',12,'tertiary')
    text(d,(1552,1091),'示例数据 · 2026.10.03',12,'tertiary',right=True)
    board.save(OUT/'survival-ui-A-B.png')
    for variant in ('A','B'):
        hud(variant,(152,155,83,68,92)).save(OUT/f'survival-ui-{variant}.png')
        hud(variant,(90,155,0,0,72)).save(OUT/f'survival-ui-{variant}-depleted.png')

def make_selected_a():
    normal=hud('A',(152,155,83,68,92),refined=True)
    depleted=hud('A',(90,155,0,0,72),refined=True)
    normal.save(OUT/'survival-ui-A-selected.png');depleted.save(OUT/'survival-ui-A-selected-depleted.png')
    board=Image.new('RGB',(1100,1020),PALETTE['bg']);draw=ImageDraw.Draw(board)
    text(draw,(40,28),'COLD STEEL / SURVIVAL',12,'gold',numeric=True)
    text(draw,(40,66),'A · 紧凑横排 / 已选版优化',24,medium=True)
    text(draw,(40,108),'沿用时钟、事件栏与弹药栏的圆弧金角线，让生存状态融入当前 HUD。',14,'secondary')
    draw.line((40,138,1060,138),fill=PALETTE['border'])
    for x,label,card in [(40,'正常状态',normal),(560,'耗尽状态',depleted)]:
        text(draw,(x,158),label,16,medium=True)
        scene=backdrop(500,260);scene.paste(card,(16,260-card.height-16));board.paste(scene,(x,190))
    text(draw,(40,477),'圆弧细节 · 2× 放大参考',16,medium=True)
    board.paste(normal.resize((880,368),Image.Resampling.LANCZOS),(110,520))
    for x,title,note in [(110,'四角金线','真实圆角 + 短切线'),(434,'等级更紧凑','64 × 56 px / 独立列宽'),(758,'占屏更紧凑','440 × 184 px')]:
        text(draw,(x,914),title,14,'gold',medium=True);text(draw,(x,942),note,12,'secondary')
    draw.line((40,978,1060,978),fill=PALETTE['border'])
    text(draw,(40,994),'离线设计参考 · 示例数据 · 非实机截图',11,'tertiary')
    board.save(OUT/'survival-ui-A-refined-reference.png')

if __name__=='__main__':
    if '--selected-a' in sys.argv:
        make_selected_a();print(OUT/'survival-ui-A-refined-reference.png')
    else:
        make_board();print(OUT/'survival-ui-A-B.png')
