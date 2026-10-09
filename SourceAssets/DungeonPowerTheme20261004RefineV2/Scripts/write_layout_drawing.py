"""Dimension drawing from source configuration; not a render or runtime check."""
import json,html,math
from pathlib import Path
R=Path(__file__).resolve().parents[1];c=json.loads((R/'Config/scene.json').read_text());D=R/'Docs'
S=16;X=lambda x:100+(x+9)*S;Y=lambda y:585-y*S
q=['<svg xmlns="http://www.w3.org/2000/svg" width="1840" height="1120" viewBox="0 0 1840 1120">','<rect width="1840" height="1120" fill="#ecebe2"/>','<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",sans-serif;fill:#263d35}.small{font-size:17px}.label{font-size:23px;font-weight:600}.note{font-size:20px}</style>','<text x="95" y="58" font-size="36" font-weight="700">失效供能中心 · 圆形总控扩建</text>','<text x="95" y="96" class="note">作者尺寸图 · 参照车站最终主厅面积 · 非引擎截图、非导航或运行验收</text>']
def rect(x,y,w,h,fill,stroke='#485b50',sw=2):q.append(f'<rect x="{X(x):.2f}" y="{Y(y+h):.2f}" width="{w*S:.2f}" height="{h*S:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def poly(ps,fill):q.append('<polygon points="'+' '.join(f'{X(x):.2f},{Y(y):.2f}' for x,y in ps)+'" fill="'+fill+'" stroke="#485b50" stroke-width="2"/>')
def circ(x,y,r,fill,stroke='#485b50',sw=2):q.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{r*S}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
def text(x,y,t,cls='small'):q.append(f'<text x="{X(x):.2f}" y="{Y(y):.2f}" class="{cls}">{html.escape(t)}</text>')
rect(-9,-8,18,16,'#d8d9cb');rect(-3,8,6,3,'#d8d9cb');rect(9,-1.56,6,3.12,'#bfc4b3');rect(15,-11,26,22,'#d8d9cb');rect(41,-1.56,6,3.12,'#bfc4b3');rect(15.35,7.55,25.3,3.15,'#a9b4a0')
r=c['rooms'][2];cx=r['origin_m'][0];radius=r['radius_m'];ri,ro=r['upper_annulus_m'];z=r['upper_deck_m']
circ(cx,0,radius,'#d8d9cb');circ(cx,0,ro,'#a9b4a0');circ(cx,0,ri,'#d8d9cb');circ(cx,0,4.1,'#aaa893');circ(cx,0,3.7,'#647f6a');circ(cx,0,4.75,'none','#b08b47',2)
for y in (-4.25,4.25):rect(23.35,y-1.95,9.3,3.9,'#aaa893');rect(24.075,y-1.50,7.85,3.0,'#647f6a')
for x in (16.45,37.75):
 rect(x,2.15,1.8,5.4,'#c3c9b8')
 for i in range(15):q.append(f'<line x1="{X(x)}" y1="{Y(2.15+i*.36)}" x2="{X(x+1.8)}" y2="{Y(2.15+i*.36)}" stroke="#697768"/>')
for a in map(math.radians,(225,315)):
 n=(math.cos(a),math.sin(a));t=(-n[1],n[0]);start=ri-8.64
 ps=[(cx+n[0]*rr+t[0]*ss,n[1]*rr+t[1]*ss) for rr,ss in [(start,-1),(ri,-1),(ri,1),(start,1)]];poly(ps,'#c3c9b8')
 for i in range(25):
  rr=start+i*.36;p=(cx+n[0]*rr-t[0],n[1]*rr-t[1]);e=(cx+n[0]*rr+t[0],n[1]*rr+t[1]);q.append(f'<line x1="{X(p[0])}" y1="{Y(p[1])}" x2="{X(e[0])}" y2="{Y(e[1])}" stroke="#697768"/>')
cr=r['control_room'];x0,x1=cr['x_bounds_m'];y0,y1=cr['y_bounds_m'];rect(cx+x0,y0,x1-x0,y1-y0,'#919f91');text(cx-4.8,y0+2.1,'封闭主控制室')
for room in c['rooms']:
 ox,oy,_=room['origin_m']
 for p in room['reused_parts']:
  x,y,z=p['position_m'];x+=ox;y+=oy;name=p['source_asset_id']
  if name=='SM_Facility_PowerCabinet':rect(x-.6,y-.3,1.2,.6,'#385749',sw=1)
  elif name=='SM_Staff_Chair':circ(x,y,.27,'#967e55',sw=1)
 for p in room['authored_parts']:
  if 'ControlConsole' in p['mesh']:x,y,z=p['position_m'];rect(ox+x-1.38,oy+y-.52,2.76,1.04,'#567566')
text(-8,15.2,'01 配电检修廊','label');text(-8,13.4,'18×16米；净高4.8米')
text(16,15.2,'02 双机发电大厅','label');text(16,13.4,'26×22米；净高9米')
text(cx-15,25.3,'03 圆形蓄能总控大厅','label');text(cx-15,23.5,'直径45米；净高11.7米；完整二层3.84米')
text(cx-3.8,-6.2,'精细蓄能核心');text(cx-4.7,-7.8,'直径7.4米 / 机身7.815米')
text(10,-3.0,'6米');text(42,-3.0,'6米');text(19,9.2,'检修高台')
q+=['<text x="95" y="1005" class="note">车站参照：最终主厅48×33米，等面积圆直径44.91米；此版取45米，不把隧道计入主厅尺度。</text>','<text x="95" y="1042" class="note">主门净空300×280厘米；圆厅楼梯踏步16 / 踏面36 / 宽200厘米；护栏108厘米。</text>','<text x="95" y="1080" class="small">深绿：设备与控制台；浅绿：环形二层；棕色：桌椅。所有位置来自作者配置，不代表运行验证。2026-10-04</text>','</svg>']
(D/'PowerCenter_DimensionalPlan.svg').write_text('\n'.join(q),encoding='utf8');print('POWER_DIMENSIONAL_DRAWING_WRITTEN')
