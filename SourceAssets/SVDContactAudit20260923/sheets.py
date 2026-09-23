from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
O=Path(__file__).parent;F=O/'frames'
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',19)
groups={
 '01_base_contacts':[(f'base_idle_0_{v}.png',t) for v,t in [('left','原厂待机 · 左侧'),('right','原厂待机 · 右侧'),('under','原厂待机 · 下方')]]+[(f'base_reload_{f}_mag.png',f'普通换弹 · {f}/120 秒') for f in [128,180,240]],
 '02_magazine_release':[(f'base_reload_{f}_mag.png',f'普通换弹 · 帧 {f} / {f/120:.3f} 秒') for f in [52,220,240,252,264,280]],
 '03_charge':[(f'base_equip_{f}_handle.png',f'装备拉栓 · 帧 {f} / {f/120:.3f} 秒') for f in [64,80,94,100,116]]+[('base_reload_empty_310_handle.png','空仓拉栓 · 帧 310 / 2.583 秒')],
 '04_grips':[(f'{family}_idle_0_{v}.png',f'{family} 待机 · {v}') for family in ['vertical','canted','prism','angled'] for v in ['left','right']],
 '05_palm_details':[(f'palm_{clip}_{f}_{sign}.png',f'{label} · 帧 {f} · 掌面轴 {sign:+}') for clip,f,label in [('reload',180,'持匣'),('reload',240,'压实'),('equip',94,'拉栓到后止点')] for sign in [-1,1]],
}
for name,entries in groups.items():
 if not all((F/f).exists() for f,t in entries):continue
 cols=3 if len(entries)==6 else 2;cw=480;ch=450;im=Image.new('RGB',(cw*cols,ch*((len(entries)+cols-1)//cols)+38),(235,237,238));d=ImageDraw.Draw(im)
 d.text((12,8),'动作接触检查 · 左手蓝 / 右手橙 / 拉机柄红 · 诊断配色，非游戏材质',font=font,fill=(25,35,45))
 for i,(f,title) in enumerate(entries):
  x=(i%cols)*cw;y=(i//cols)*ch+38;p=Image.open(F/f).convert('RGB');p.thumbnail((cw,414));im.paste(p,(x,y+30));d.text((x+10,y+3),title,font=font,fill=(25,35,45))
 im.save(O/(name+'.jpg'),quality=87,optimize=True)
 print(name,(O/(name+'.jpg')).stat().st_size)
