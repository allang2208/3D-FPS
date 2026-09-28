from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/GodSpaceLayout20260927/Preview')
parts=['''<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="1200" viewBox="0 0 1400 1200"><defs><pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse"><path d="M20 0H0V20" fill="none" stroke="#213345" stroke-width=".5"/></pattern><marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10" fill="#83c5d2"/></marker></defs><rect width="1400" height="1200" fill="#0e1a28"/><g font-family="Microsoft YaHei, Noto Sans SC, sans-serif"><text x="65" y="65" fill="#eff3ed" font-size="32" font-weight="bold">主神空间 / 浮空布局 V1</text><text x="65" y="100" fill="#92aabd" font-size="17">独立方案预览 · 80 × 96 m · 现有组件重排 · 尚未替换 UE 正式关卡</text><rect x="70" y="150" width="850" height="975" fill="url(#grid)"/>''']
# plan local meters x +-40,y +-48 -> image x 150..790, y240..1008
ox,oy,k=470,630,8
P=lambda x,y:(ox+k*x,oy-k*y)
def poly(pts,fill,stroke='#d0c2a2',sw=2):
 parts.append('<polygon points="'+' '.join('%s,%s'%P(x,y) for x,y in pts)+'" fill="'+fill+'" stroke="'+stroke+'" stroke-width="'+str(sw)+'"/>')
def rect(x,y,w,h,c):
 a,b=P(x-w/2,y+h/2);parts.append(f'<rect x="{a}" y="{b}" width="{w*k}" height="{h*k}" fill="{c}"/>')
def line(x,y,xx,yy,c='#83c5d2',sw=2,arrow=False):
 a,b=P(x,y);d,e=P(xx,yy);parts.append(f'<line x1="{a}" y1="{b}" x2="{d}" y2="{e}" stroke="{c}" stroke-width="{sw}"'+(' marker-end="url(#arrow)"' if arrow else '')+'/>')
def circle(x,y,r,c,stroke='none'):
 a,b=P(x,y);parts.append(f'<circle cx="{a}" cy="{b}" r="{r*k}" fill="{c}" stroke="{stroke}" stroke-width="2"/>')
def label(x,y,t,sz=18,c='#eff3ed'):
 a,b=P(x,y);parts.append(f'<text x="{a}" y="{b}" text-anchor="middle" fill="{c}" font-size="{sz}">{t}</text>')
poly([(-30,-48),(30,-48),(40,-38),(40,38),(30,48),(-30,48),(-40,38),(-40,-38)],'#e2e7e4')
rect(0,0,9.4,88,'#557681');rect(0,8,73,5.2,'#557681')
circle(0,-6,10,'#c9d2cf','#b4985a');circle(0,-6,4.8,'#7b9da7');label(0,-7,'02',23)
rect(0,27,18,20,'#b8c2c1');rect(0,27,12,12,'#526e7b');circle(0,28.6,2.3,'#cef6ff','#ac884b');rect(0,24.5,2.2,2,'#d5c5a0');label(0,40,'01 主神祭坛',18,'#233947')
circle(-24,13,6.5,'#c5d1d1','#a38e62');circle(-24,13,4.8,'#7a8a92');label(-24,13,'03',23);label(-24,2,'星座凉亭',16,'#233947')
rect(24,13,17,21,'#78929a');label(24,13,'04',23);label(24,2,'生产 / 仓储',16,'#233947')
for x,y in [(-22,-29),(22,-29),(-22,-19)]:
 rect(x,y,6,6,'#698c99');rect(x,y,1.5,4.4,'#c8eef3')
rect(22,-19,6,6,'#9fafb2');label(-22,-38,'05 传送区',16,'#233947');label(22,-14,'预留',13,'#233947')
for x in [-35,35]:
 for y1,y2 in [(-32,-12),(22,38)]:
  line(x,y1,x,y2,'#8f9a98',6)
  num=round((y2-y1)/4)
  for i in range(num+1):circle(x,y1+(y2-y1)*i/num,.45,'#faf6eb','#bcaa8b')
for xx in [-20,20]:
 line(xx-8,39,xx+8,39,'#8f9a98',6)
 for dx in [-8,-4,0,4,8]:circle(xx+dx,39,.45,'#faf6eb','#bcaa8b')
circle(13,-38,1.1,'#52aebe');label(13,-43,'到达区',16,'#233947')
line(13,-36,10,-15,arrow=True);line(10,-15,12,5,arrow=True);line(12,8,17,8,arrow=True);line(-8,8,-16,8,arrow=True);line(8,11,8,16,arrow=True)
line(-39,-52,39,-52,'#8394a0',1);label(0,-56,'平台宽 80 m',16,'#9badb9')
line(43,-47,43,47,'#8394a0',1);label(46,0,'96 m',15,'#9badb9')
parts.append('''<g transform="translate(970 210)"><text y="0" fill="#d8c99f" font-size="22">功能区与新增组件</text>''')
rows=[('01 / 主神祭坛','现有小祭坛 + 新阶台','光球与轨道为概念占位'),('02 / 中央喷泉','复用 V9，保持 9.6 m 外径','左右绕行，不再挤在小中庭'),('03 / 星座凉亭','复用已有穹顶与柱组','侧向开景，面向云海'),('04 / 生产与仓储','高炉、铸造台、仓库箱','后续需矮墙 / 屋盖 / 标识'),('05 / 传送到达区','现有 3 座场景门','固定锚点接入留待确认后')]
for i,(a,b,c) in enumerate(rows):
 y=55+i*123;parts.append(f'<text y="{y}" fill="#eef2ef" font-size="19">{a}</text><text y="{y+31}" fill="#9db3c2" font-size="16">{b}</text><text y="{y+58}" fill="#9db3c2" font-size="16">{c}</text>')
parts.append('''<text y="720" fill="#d8c99f" font-size="20">远景垂直层次</text><text y="755" fill="#aac4d0" font-size="16">高度均相对平台，非 UE 海拔</text><text y="785" fill="#aac4d0" font-size="16">云峰：下方 150–350 m</text><text y="815" fill="#aac4d0" font-size="16">云海：下方 280–600 m</text><text y="845" fill="#aac4d0" font-size="16">大地：下方约 1.5 km</text></g><text x="65" y="1170" fill="#8198a8" font-size="15">方案图。云形仅占位，正式复用游戏现有云；地表可参考外部方案，新模块仍为概念表达。</text></g></svg>''')
(R/'layout_annotated.svg').write_text(''.join(parts),encoding='utf8')
