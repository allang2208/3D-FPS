"""Author new, editable room-planning diagrams; does not edit concept images or UE assets."""
from pathlib import Path
from html import escape
import json
from PIL import Image, ImageDraw, ImageFont

OUT = Path('D:/FPS3D/FPSGAME/Docs/Gameplay/Previews/DungeonRoomConcepts_20260921')
OUT.mkdir(parents=True, exist_ok=True)
W, H = 1440, 1040
BG, INK, MUTED = '#f4f1e9', '#283631', '#68746c'
WALL, ROUTE, BRASS, EARTH = '#69736c', '#d4e5dc', '#c4a674', '#b69b7e'
FONT = 'C:/Windows/Fonts/msyh.ttc'

class Board:
    def __init__(self, title, subtitle, origin, scale):
        self.im = Image.new('RGB', (W, H), BG)
        self.d = ImageDraw.Draw(self.im)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', f'<rect width="{W}" height="{H}" fill="{BG}"/>']
        self.origin, self.scale = origin, scale
        self.text((64, 38), 'FPSGAME  /  地下设施与遗迹', 18, MUTED)
        self.text((64, 74), title, 35)
        self.text((64, 125), subtitle, 19, MUTED)
        self.line([(64, 169), (1376, 169)], '#c5cdc4', 2)
        self.line([(836, 207), (836, 936)], '#c5cdc4', 2)
        self.text((64, 984), '美术候选布局 · 房间外轮廓沿用现有尺寸 · 道具占地为建议值 · 未写入 UE', 18, MUTED)

    def text(self, p, value, size=20, color=INK, center=False):
        font = ImageFont.truetype(FONT, size)
        anchor = 'mt' if center else 'lt'
        self.d.text(p, value, font=font, fill=color, anchor=anchor)
        align = 'middle' if center else 'start'
        self.svg.append(f'<text x="{p[0]:.2f}" y="{p[1]+size*.86:.2f}" font-family="Microsoft YaHei, sans-serif" font-size="{size}" text-anchor="{align}" fill="{color}">{escape(value)}</text>')

    def line(self, pts, color=INK, width=2):
        self.d.line(pts, fill=color, width=width, joint='curve')
        coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)
        self.svg.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')

    def polygon(self, pts, fill, outline=None, width=2):
        self.d.polygon(pts, fill=fill)
        coords = ' '.join(f'{x:.2f},{y:.2f}' for x,y in pts)
        self.svg.append(f'<polygon points="{coords}" fill="{fill}"/>')
        if outline:
            self.line(pts+[pts[0]], outline, width)

    def circle(self, p, radius, fill, outline=None):
        x,y=p
        self.d.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill,outline=outline,width=2)
        self.svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{fill}" stroke="{outline or fill}" stroke-width="2"/>')

    def xy(self, x,y):
        return self.origin[0]+x*self.scale, self.origin[1]-y*self.scale

    def rect(self, x,y,w,h,fill,outline=None):
        self.polygon([self.xy(x,y),self.xy(x+w,y),self.xy(x+w,y+h),self.xy(x,y+h)],fill,outline)

    def poly(self, points, fill, outline=None):
        self.polygon([self.xy(*p) for p in points],fill,outline)

    def ml(self, points,color=INK,width=2):
        self.line([self.xy(*p) for p in points],color,width)

    def label(self, x,y,value,size=18,color=INK):
        px,py=self.xy(x,y)
        self.text((px,py-size*.45),value,size,color,True)

    def pin(self, x,y,n):
        p=self.xy(x,y)
        self.circle(p,16,INK)
        self.text((p[0],p[1]-12),str(n),19,BG,True)

    def legend(self,n,title,lines,top):
        self.circle((892,top+13),16,INK)
        self.text((892,top+1),str(n),19,BG,True)
        self.text((924,top),title,23)
        for j,line in enumerate(lines):
            self.text((888,top+40+j*29),line,19,MUTED)

    def room(self,w,h,opening):
        self.rect(0,-.64,w,.64,'#e0e4df')
        self.rect(0,0,w,h,'#e9e4d9')
        for x in range(1,int(w)+1): self.ml([(x,0),(x,h)],'#d9d5ca',1)
        for y in range(1,int(h)+1): self.ml([(0,y),(w,y)],'#d9d5ca',1)
        self.ml([(0,0),(0,h),(w,h),(w,0)],WALL,13)
        self.ml([(0,0),(opening[0],0)],WALL,13)
        self.ml([(opening[1],0),(w,0)],WALL,13)
        left,top=self.xy(0,h)
        right,_=self.xy(w,h)
        self.line([(left,top-34),(right,top-34)],MUTED,2)
        self.line([(left,top-42),(left,top-26)],MUTED,2)
        self.line([(right,top-42),(right,top-26)],MUTED,2)
        self.text(((left+right)/2,top-66),f'{w:g} m',22,INK,True)
        self.text((right+24,(top+self.origin[1])/2),f'{h:g} m',21,MUTED)
        self.label(w/2,-.34,'既有主走廊',18,MUTED)

    def camera(self,x,y,target):
        p=self.xy(x,y); q=self.xy(*target)
        self.line([p,q],'#6b91a0',3)
        self.circle(p,10,'#6b91a0')
        self.text((p[0]+18,p[1]-12),'概念图视点',17,'#507885')

    def finish(self,name):
        self.svg.append('</svg>')
        self.im.save(OUT/f'{name}.png')
        (OUT/f'{name}.svg').write_text('\n'.join(self.svg),encoding='utf-8')
        print(str(OUT/f'{name}.png'))


b=Board('01  维修间｜被中断的检修', '6.0 × 4.2 m，顶高 3.3 m；入口 5.2 m。以工作台为主要视觉中心。', (94,790),110)
b.room(6,4.2,(.4,5.6))
# Working circulation is reserved before placing furniture.
b.poly([(2.35,0),(3.55,0),(3.55,2.65),(4.05,2.65),(4.05,3.35),(1.45,3.35),(1.45,2.65),(2.35,2.65)],ROUTE)
b.rect(.10,1.72,.78,2.30,BRASS,INK)
b.rect(.10,3.42,2.62,.68,BRASS,INK)
b.rect(.10,.70,.68,.87,'#ad8070',INK)
b.rect(5.30,.43,.60,1.90,'#9fa995',INK)
b.rect(4.10,3.51,1.72,.59,'#baa169',INK)
b.rect(2.90,3.30,.83,.80,'#9c8b76',INK)
b.ml([(3.3,3.95),(3.3,4.12),(5.75,4.12),(5.75,3.83)],'#765c48',8)
b.ml([(.28,.12),(.28,3.98),(5.72,3.98),(5.72,.28)],'#869998',5)
b.pin(.47,2.88,1); b.pin(.45,1.12,2); b.pin(4.96,3.80,3)
b.pin(3.32,3.67,4); b.pin(5.60,1.39,5)
b.label(2.95,1.52,'通行留白',21,'#426755')
b.label(2.95,1.13,'目标净宽 ≥ 1.2 m',17,'#426755')
b.label(2.97,-.88,'开口与通道保持现有关系',18,MUTED)
b.camera(1.22,-.45,(2.90,2.56))
b.legend(1,'L 形工作台 + 工具板',['拆开的电机是焦点，工具围绕它摆放。','台面厚度、支腿、插座和电源线需完整。'],225)
b.legend(2,'工具推车',['停在工作台旁，保留搬运通道。','使用痕迹集中在轮迹、抽屉和台面。'],363)
b.legend(3,'复用旧电柜',['背墙右侧，保留开门与检修空间。','旧电柜形态保留，补连续线管。'],501)
b.legend(4,'阀门与服务管线',['接入墙体和顶部，避免独立摆放。','局部渗漏与下方痕迹相互对应。'],639)
b.legend(5,'备件架',['右侧前段浅进深收纳。','箱盒成组摆放，留空格与积灰差异。'],777)
b.finish('03_workshop_layout')

r=Board('02  遗迹侧穴｜地下工程揭开的旧层', '6.5 × 7.5 m，最高 4.6 m；保留既有破口、雕像及石拱身份。', (112,900),82)
r.room(6.5,7.5,(1.2,5.2))
r.rect(0,0,6.5,1.35,'#d7d9d0')
r.poly([(0,1.35),(.85,1.43),(1.65,1.25),(2.50,1.65),(3.15,1.49),(3.88,1.82),(4.68,1.35),(5.5,1.61),(6.5,1.46),(6.5,7.5),(0,7.5)],'#c9c0ae')
r.poly([(0,1.58),(.64,1.92),(1.14,2.66),(1.35,3.7),(1.85,4.66),(2.25,5.62),(1.65,6.37),(1.12,7.5),(0,7.5)],EARTH, '#8f7761')
r.poly([(5.45,1.67),(6.5,1.46),(6.5,7.5),(5.35,7.5),(5.95,6.28),(5.53,5.20),(5.87,3.68)],EARTH,'#8f7761')
r.poly([(2.52,0),(3.92,0),(4.28,1.60),(4.67,3.00),(4.72,4.40),(4.43,5.05),(3.14,5.05),(3.50,4.2),(3.42,3.08),(3.05,1.72)],ROUTE)
# Old masonry and the arch remain inside the established room envelope.
r.rect(.14,7.04,6.2,.33,'#8b8371',INK)
r.rect(.14,2.68,.34,4.34,'#8b8371',INK)
r.rect(6.02,2.00,.34,5.05,'#8b8371',INK)
r.rect(2.75,6.78,2.75,.40,'#8b8371',INK)
r.rect(2.75,5.64,.41,1.45,'#8b8371',INK)
r.rect(5.09,5.64,.41,1.45,'#8b8371',INK)
r.rect(3.38,5.52,1.50,1.06,BRASS,INK)
r.circle(r.xy(4.12,6.08),16,'#e8dfc9',INK)
r.rect(.62,.10,.23,.23,WALL,INK)
r.rect(.62,1.08,.23,.23,WALL,INK)
r.ml([(.73,-.06),(.73,1.44)],WALL,9)
r.circle(r.xy(1.25,.96),11,'#d5ad61',INK)
r.ml([(1.25,.96),(1.07,.64),(.93,.23),(.93,-.39)],'#5b665a',3)
r.ml([(0,1.35),(.85,1.43),(1.65,1.25),(2.50,1.65),(3.15,1.49),(3.88,1.82),(4.68,1.35),(5.5,1.61),(6.5,1.46)],'#8f7761',4)
r.pin(.74,.58,1);r.pin(1.17,4.15,2);r.pin(5.10,1.48,3);r.pin(4.13,6.04,4)
r.label(4.04,3.55,'清理出的接近路线',16,'#426755')
r.label(4.04,3.20,'目标净宽 ≥ 1.2 m',16,'#426755')
r.camera(3.02,-.40,(4.04,5.02))
r.legend(1,'破口断面 + 临时支撑',['瓷砖、钢筋混凝土、土层分层显露。','施工灯和电缆留在入口现代区域。'],225)
r.legend(2,'沿侧墙堆积的土与瓦砾',['左侧更密，向路线逐渐降低。','碎块材质对应缺损，避免均匀撒点。'],383)
r.legend(3,'现代板面向旧石板过渡',['局部露出下层旧地面，约低 15–25 cm。','用土坡缓接；无深坑，不阻断接近。'],541)
r.legend(4,'石拱与雕像',['靠后略偏右，嵌入旧砌体。','保留雕像身份；不按生成图重做面貌。'],699)
r.text((888,863),'灯光：入口冷光 + 侧向施工暖光',19,INK)
r.text((888,896),'异常：只在雕像附近保留克制暗示',19,MUTED)
r.finish('04_ruin_layout')

layout={
    'status':'concept_proposal_not_runtime_data',
    'units':'metres',
    'coordinates':'Room-local: u right when looking inward, v increases away from entry. Diagrams are proposals, not surveyed mesh transforms.',
    'workshop':{'width':6.0,'depth':4.2,'height':3.3,'opening_width':5.2,'target_clear_route_width':1.2,'groups':['rear_left_L_workbench','left_front_tool_cart','rear_right_existing_cabinet','rear_service_corner','right_front_parts_shelf']},
    'ruin':{'width':6.5,'depth':7.5,'max_height':4.6,'target_clear_route_width':1.2,'proposed_old_floor_offset':[-.25,-.15],'groups':['entry_shoring_and_worklight','left_dense_soil_rubble','local_floor_transition','rear_right_arch_existing_statue','peripheral_old_masonry']},
    'randomization_rules':{'fixed':['room_shell','entry','route_clearance','service_connections','statue_identity'],'group_variants':['workbench_repair_state','shelf_fill','rubble_bank_silhouette','leak_event'],'dependent_details':['leak_to_stain','missing_wall_to_fragments','repair_object_to_tools','traffic_to_floor_wear']}
}
(OUT/'layout-proposal.json').write_text(json.dumps(layout,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
