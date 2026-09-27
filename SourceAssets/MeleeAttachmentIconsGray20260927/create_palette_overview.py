from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent;content=P.parents[1]/'Content/ColdSteelData/AttachmentIcons20260913'
entries=[
 ('弓 · 原装缠带',content/'bow_dark_grip_false.png'),
 ('弓 · 木制瞄具',content/'bow_dark_sight_false.png'),
 ('高地剑 · 原装护手',P/'Icons/ue_highland_claymore_guard_false.png'),
 ('高地剑 · 棘冠配重球',P/'Icons/ue_highland_claymore_pommel_highland_thorn_crown.png'),
 ('符文长剑 · 符文配重',P/'Icons/ue_rune_sword_pommel_pommel_runic.png'),
 ('寒晶剑 · 吸震缠柄',P/'Icons/ue_frost_crystal_sword_grip_shock_wrap.png'),
 ('高地剑 · 魔力球配重',P/'Icons/ue_highland_claymore_pommel_pommel_mana_orb.png'),
 ('伐木斧 · 主部件',P/'Icons/tool_axe_head_false.png')]
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
title=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',28)
sheet=Image.new('RGB',(1120,650),(31,34,38));d=ImageDraw.Draw(sheet)
d.text((24,14),'改造栏 · 统一灰白色',font=title,fill=(238,238,238))
for i,(label,file) in enumerate(entries):
 x=i%4*280;y=62+i//4*286
 d.rectangle((x+5,y+3,x+274,y+281),fill=(39,42,46))
 im=Image.open(file).convert('RGBA').resize((230,230),Image.Resampling.LANCZOS)
 sheet.paste(im,(x+25,y+5),im)
 d.text((x+14,y+246),label,font=font,fill=(228,228,228))
sheet.save(P/'palette-overview.jpg',quality=96)
