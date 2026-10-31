"""Author a planning dataset from existing city recipes; no UE assets are changed."""
from pathlib import Path
from datetime import datetime
import ast, json, math

R = Path(__file__).resolve().parent
P = R.parents[1]
OLD = P / 'SourceAssets/CyberpunkApartmentRebuild20261022'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def world(p):
    return [round((-p[0] + 10) * 1.25, 2), round((p[1] - 615) * 1.25, 2)]

tree = ast.parse((OLD/'RefinementV15/design.py').read_text(encoding='utf-8-sig'))
shore = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SHORE' for t in n.targets))
assembly = read(P/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json')
layout = read(P/'SourceAssets/CyberpunkExteriorUpgrade20261025/layout.json')
installed = read(P/'SourceAssets/CyberpunkExteriorUpgrade20261025/installed.json')
new = {r['index']:r for r in layout['placements']}
buildings = []
for i, b in enumerate(assembly['buildings']):
    if i in new:
        lo,hi = new[i]['world_bounds']['min'],new[i]['world_bounds']['max']
        rect = [lo[0]/100,lo[1]/100,(hi[0]-lo[0])/100,(hi[1]-lo[1])/100]
    else:
        x,y = world([b['x'],b['y']]);w,d=b['width']*1.25,b['depth']*1.25
        rect = [x-w/2,y-d/2,w,d]
    buildings.append(dict(id=f'BAY-B{i:04}',group=b['group'],replaced=i in new,rect=[round(v,2) for v in rect]))

land=[]
for i,(a,b) in enumerate(zip(shore,shore[1:])):
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy);nx,ny=-dy/length,dx/length
    land.append(dict(id=f'QUAY-{i}',points=[world(q) for q in [a,b,[b[0]+nx*600,b[1]+ny*600],[a[0]+nx*600,a[1]+ny*600]]]))
farlands=[[-7500,2880,1320,9000],[3650,4350,8000,10000]]
for i,(x1,y1,x2,y2) in enumerate(farlands):
    land.append(dict(id=f'FAR-LAND-{i}',points=[world(q) for q in [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]]))

raw=shore[2:6];points=[]
for i in range(len(raw)-1):
    a,b,c,d=raw[max(i-1,0)],raw[i],raw[i+1],raw[min(i+2,len(raw)-1)]
    for j in range(48):
        t=j/48
        points.append([.5*(2*b[k]+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t*t+(-a[k]+3*b[k]-3*c[k]+d[k])*t*t*t) for k in (0,1)])
points.append(raw[-1])
def station(i,offset=26):
    a,b=points[max(i-1,0)],points[min(i+1,len(points)-1)]
    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
    return world([points[i][0]-dy/length*offset,points[i][1]+dx/length*offset])

zones=[
 dict(id='P1',name='中央市民公园',area='滨水陆地',priority='第一批',center=[-560,1500],polygon=[[-630,1400],[-530,1420],[-440,1530],[-470,1680],[-650,1640],[-670,1510]],
      purpose='把中央楼间空地组织成有入口、林荫环路和喷泉核心的公共空间。',
      elements=['24–30 m 浅池与 2.5–4 m 主喷流','4–6 m 林荫主环路，2.5–3 m 支路','0.6–1.2 m 台地与配套缓坡','树冠成团，中央保留可辨认的铺装与水面'],
      density='绿地约 55%、铺装约 35%、水面约 10%；树冠投影目标 35–45%。',
      anchor='从 V16 第 71 站过街点接入，沿 B0046–B0048 之间的空间连接公园；避开两座中央地标基座。'),
 dict(id='P2',name='西段林荫社区园',area='滨水陆地',priority='第二批',center=[-1640,1550],polygon=[[-1780,1450],[-1580,1440],[-1550,1640],[-1730,1680]],
      purpose='形成较安静的乔木林、休息台地和小型活动场地，补齐左段楼间空白。',
      elements=['5–9 株一组的主树群','18–25 m 活动铺装与林下座椅','低矮灌木围合、地被分片','一处 8–12 m 静水池，按视距决定是否保留'],
      density='绿地约 70%、铺装约 25%、水面最多 5%；外围密、路径与入口疏。',
      anchor='连接第 18 站过街点及 B0029、B0033 门厅；避开西侧地标和已有楼体。'),
 dict(id='P3',name='东段台地花园',area='滨水陆地',priority='第二批',center=[480,1850],polygon=[[380,1770],[530,1730],[610,1820],[510,1980],[360,1920]],
      purpose='利用弯岸和楼群转折形成阶梯花园，给侧窗提供明确的近低远高层次。',
      elements=['2–3 级景观台地，总高差 1.2–2.4 m','各台地配置短楼梯与连续缓坡','局部 6–10 m 叠水墙，落差 0.6–1.2 m','低矮植物框住视线，较高树群退到后缘'],
      density='绿地约 60%、铺装约 35%、水面约 5%；避免连续高树墙。',
      anchor='由第 124 站过街点、B0061 与 B0064 入口引出支路；绕开地标基座与转弯道路。'),
 dict(id='P4',name='滨水步行带与街角',area='滨水陆地',priority='第一批',center=[-430,1200],polygon=[],
      purpose='把已有门厅、观景点、码头连接成连续街景，让公园有清晰入口。',
      elements=['替换既有 94 株简化道路树的可见树体','保留 11 处门厅、6 处观景点、3 处码头与 36 辆车流','4–6 个轻量街角组合：座椅、种植池、亭棚、导视','清晰区分车行、树池家具、人行和岸边停留带'],
      density='节点密、连接段疏；出入口与过街点保持连续视线。',
      anchor='复用 V16 道路样条与第 18/71/124 站过街点，先调整道路树和家具，不覆盖车流车道。'),
 dict(id='P5',name='远岸城市森林公园',area='远岸陆地',priority='第一批先做轮廓',center=[-700,2960],polygon=[[-2400,2890],[800,2890],[800,3030],[-2400,3030]],
      purpose='处理真正远端的大片空地，以连续但有缺口的林带和三处广场建立城市前景。',
      elements=['三处林荫广场，参考 X=-1700/-700/350 作者坐标','每段树群有乔木、次层灌木与成片地被','最远处使用实体树群或多角度代理，避免薄片树墙','远端水池只保留盆体、水面和可读轮廓'],
      density='先做 40–60 个树群单元，保留 20–30% 视觉开口；不逐平方米铺草。',
      anchor='仅在既有 FAR-LAND-0 陆地上，候选带为作者 Y=2890–3030；扣除远楼基座和通道。'),
 dict(id='P6',name='岬角生态观景园',area='远岸陆地',priority='第三批',center=[4350,4500],polygon=[[3850,4380],[5000,4380],[5000,4630],[3850,4630]],
      purpose='柔化远岬角楼群的硬边，维持开放河口与城市深度。',
      elements=['弧形林带与疏密变化的树群','一处低矮观景平台和折线步道','必要挡墙及坡脚植物','保留楼体之间可见的地面与岸线'],
      density='以 20–30 个树群单元起步；避免整面同高林墙和重复喷泉。',
      anchor='仅在 FAR-LAND-1 上；不跨越河口补地，不新建跨水道路。')
]
for z in zones:
    z['author_center']=z['center'];z['center']=world(z['center']);z['polygon']=[world(q) for q in z['polygon']]
    z['status']='proposed_not_installed'

asset_groups=[]
specs=[
 ('Soul 乔木与灌木','SoulCity/Environment/Meshes/Foliage',['SM_Aspen_Tree_01','SM_LV_Soul_Tree01_B','SM_S_Soul_Tree2','SM_S_Soul_bush']),
 ('Soul 最远树群候选','SoulCity/Environment/Meshes/Foliage',['SM_LV_Soul_TreeCluster','SM_S_Soul_TreeCards_01','SM_S_Soul_TreeCards_02']),
 ('PN 地被','PN_FoliageCollection/Meshes/groundPlantMesh',['ground_01_01','ground_02_01','ground_03_01']),
 ('PN 花草','PN_FoliageCollection/Meshes/flowerMesh',['flower_01_01','flower_02_01','flower_03_01']),
 ('PN 草丛','PN_GrassLibrary/Meshes/grassMesh',['grass_01_01_mesh','grass_02_01_mesh']),
 ('PN 热带植物备选','PN_tropicalGroundPlants/Meshes',['tropicalPlant_01_01','tropicalPlant_02_01']),
 ('黑杨作者资源，静态适配待定','Megaplant_Library/Tree_Black_Poplar/Tree_Black_Poplar_01',['Tree_Black_Poplar_01_A','Tree_Black_Poplar_01_B']),
 ('已有喷泉水面实现参考','Props/RomanFountain20260917',['SM_RomanFountain_WaterWaves','SM_RomanFountain_WaterFX']),
]
for name,folder,names in specs:
    paths=['/Game/'+folder+'/'+n for n in names if (P/'Content'/folder/(n+'.uasset')).is_file()]
    asset_groups.append(dict(name=name,paths=paths,evidence='package_file_exists_only; mesh class, scale, UV, materials and LOD to be read during production'))
counts={folder:len(list((P/'Content'/folder).glob('*.uasset'))) for folder in ['PN_FoliageCollection/Meshes/groundPlantMesh','PN_FoliageCollection/Meshes/flowerMesh','PN_GrassLibrary/Meshes/grassMesh','PN_tropicalGroundPlants/Meshes']}
data=dict(stage='design_only',created_at=datetime.now().astimezone().isoformat(),target_map='/Game/GameMaps/L_CyberpunkApartment',
          existing_exterior_saved_at=installed['saved_at'],existing_exterior_reflection=installed['reflection'],
          coordinate_contract='UE world metres: X=(-authorX+10)*1.25; Y=(authorY-615)*1.25; Z=(authorZ-90)*1.25. Proposed dimensions are final world metres.',
          evidence_boundary='Source recipes and previous save receipts, no fresh UE scene read or screenshot. Proposed polygons are design envelopes, not cleared placement areas; apply land, full building bases, entrances, roads, pier and sightline exclusions during production.',
          shore=[world(p) for p in shore],land=land,buildings=buildings,road=[station(i) for i in range(len(points))],
          crossings=[dict(station=i,point=station(i)) for i in [18,71,124]],lookouts=[station(i,4) for i in [12,33,57,78,108,132]],
          piers=[world(p) for p in [[-760,1080],[-270,1160],[200,1280]]],zones=zones,asset_groups=asset_groups,candidate_package_counts=counts,
          counts=dict(existing_road_trees=94,existing_lobbies=11,existing_lookouts=6,existing_piers=3,existing_cars=36,new_buildings=44,existing_landmarks=5),
          proposed_connections=[dict(zone='P1',from_station=71),dict(zone='P2',from_station=18),dict(zone='P3',from_station=124)],
          map_modified=False,engine_started=False,tests_run=False)
(R/'design.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('Urban landscape design dataset saved; no engine assets changed.')

# The planning canvas embeds this source snapshot; it never loads the game or network.
canvas = Path('C:/Users/allan/.cursor/projects/d-FPS3D/canvases/cyberpunk-urban-landscape-20261025.canvas.tsx')
header = "import { useState, useHostTheme, Stack, Row, Grid, H1, H2, H3, Text, Button, Card, CardBody, Divider, Table, Pill } from 'cursor/canvas';\n"
body = r'''
const phases = [
  ['1', '场地与通路', '依据既有陆地和占地确定施工范围，完成中央公园环路、广场、台阶与喷泉主体。'],
  ['2', '第一批完整观感', 'P1 中央公园 + P4 中央街景 + P5 远岸林带同步制作，先解决主焦点、连续性与远端空旷。'],
  ['3', '两翼与街角', '完成 P2、P3，替换剩余道路树，补齐 4–6 个街角组合、入口、亭棚和种植边缘。'],
  ['4', '岬角与正式接入', '完成 P6、统一夜景与湿润、更新静态反射，保存唯一正式公寓并续接重建流程。'],
];
const facilities = [
  ['主步道 / 支路', '4–6 m / 2.5–3 m', '树池、路灯和座椅设独立家具带，节点与入口局部扩宽。'],
  ['常规通行台阶', '高约 0.15 m，深 0.32–0.40 m', '每段先按 4–8 级设计，完整平台、侧壁和地面收口。'],
  ['中央公园浅池', '直径 24–30 m，主喷流高 2.5–4 m', '池底、池壁、池沿、水面和落点分别制作，周边有完整环路。'],
  ['东段台地', '总高差 1.2–2.4 m，分 2–3 级', '楼梯与连续缓坡共同连接，前缘低植被，后缘高树群。'],
  ['叠水墙', '长 6–10 m，落差 0.6–1.2 m', '池体和落点连续，远端退掉飞沫但保留水面。'],
  ['乔木初始间距', '约 7–12 m，按冠幅调整', '树群有高低与前后变化，入口和地标视线保留开口。'],
];
const documentPath = 'D:/FPS3D/FPSGAME/Docs/Art/CyberpunkUrbanLandscape-Masterplan-20261025.md';
const dataPath = 'D:/FPS3D/FPSGAME/SourceAssets/CyberpunkUrbanLandscapePlan20261025/design.json';

export default function UrbanLandscapePlan() {
  const theme = useHostTheme();
  const [selected, setSelected] = useState('P1');
  const [view, setView] = useState<'core' | 'far' | 'all'>('core');
  const [tab, setTab] = useState('布局');
  const [showBuildings, setShowBuildings] = useState(true);
  const [showZones, setShowZones] = useState(true);
  const zone = DATA.zones.find(z => z.id === selected) || DATA.zones[0];
  const extents = {core: [-1700, -100, 3500, 2300], far: [-6700, 2400, 3500, 6400], all: [-9000, -150, 10000, 8500]};
  const [xmin, ymin, xmax, ymax] = extents[view];
  const W = 1040, H = 570;
  const scale = Math.min((W - 80) / (xmax - xmin), (H - 80) / (ymax - ymin));
  const ox = (W - (xmax - xmin) * scale) / 2;
  const oy = (H - (ymax - ymin) * scale) / 2;
  const project = (p: number[]) => [ox + (p[0] - xmin) * scale, H - oy - (p[1] - ymin) * scale];
  const poly = (p: number[][]) => p.map(v => project(v).join(',')).join(' ');
  const choose = (id: string) => { setSelected(id); setView(['P5', 'P6'].includes(id) ? 'far' : 'core'); };
  const visible = (p: number[]) => p[0] >= xmin && p[0] <= xmax && p[1] >= ymin && p[1] <= ymax;
  const ruler = view === 'core' ? 500 : 2000;

  return <Stack gap={22} style={{maxWidth: 1200, margin: '0 auto', padding: 24, color: theme.text.primary, background: theme.bg.editor}}>
    <Stack gap={8}>
      <Row justify="space-between" wrap gap={12}><Text size="small" tone="secondary">FPSGAME · 城市公共空间 · 2026-10-25</Text><Pill>设计方案 / 尚未接入关卡</Pill></Row>
      <H1>让空地成为公园，让街景连续起来</H1>
      <Text>一条滨水步行带，三座公园，两片远岸绿地。通过路径、林缘、台地和水景组织城市，而不是均匀散布道具。</Text>
      <Text size="small" tone="secondary">沿用 44 栋新楼、5 座地标、现有海湾与城市动态系统；唯一目标地图为 L_CyberpunkApartment。</Text>
    </Stack>
    <Row gap={8} wrap>{['布局','构件与素材','实施顺序'].map(t => <Button key={t} variant={tab === t ? 'primary' : 'secondary'} onClick={() => setTab(t)}>{t}</Button>)}</Row>

    {tab === '布局' && <Stack gap={16}>
      <Row gap={8} wrap>
        {([['core','滨水街区'],['far','远岸与岬角'],['all','全域关系']] as const).map(([k,label]) => <Button key={k} variant={view === k ? 'primary' : 'secondary'} onClick={() => setView(k)}>{label}</Button>)}
        <Button variant="secondary" onClick={() => setShowBuildings(!showBuildings)}>{showBuildings ? '隐藏现有楼群' : '显示现有楼群'}</Button>
        <Button variant="secondary" onClick={() => setShowZones(!showZones)}>{showZones ? '隐藏候选分区' : '显示候选分区'}</Button>
      </Row>
      <Text size="small" tone="secondary">俯视布局 · UE 世界坐标（米）。分区名称用于设计，不表示已建立地理方位。</Text>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="现有岸线与楼群上的城市公园候选布局" style={{width:'100%', border:`1px solid ${theme.stroke.secondary}`, background:theme.bg.editor}}>
        <defs><pattern id="urban-plan-hatch" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M0,8 L8,0" stroke={theme.accent.primary} strokeWidth="0.7" opacity="0.5" /></pattern><clipPath id="urban-plan-map-clip"><rect x="1" y="1" width={W-2} height={H-2}/></clipPath></defs>
        <g clipPath="url(#urban-plan-map-clip)">
          {DATA.land.map(l => <polygon key={l.id} points={poly(l.points)} fill={theme.fill.quaternary} stroke={theme.stroke.secondary} strokeWidth="1" />)}
          {showZones && DATA.zones.filter(z => z.polygon.length > 0).map(z => <polygon key={z.id} points={poly(z.polygon)} fill="url(#urban-plan-hatch)" stroke={theme.accent.primary} strokeWidth={z.id === selected ? 2.4 : 1.2} opacity={z.id === selected ? 1 : 0.55} onClick={() => choose(z.id)} style={{cursor:'pointer'}}><title>{z.id} {z.name}：设计包络，需扣除占地</title></polygon>)}
          <polyline points={poly(DATA.shore)} fill="none" stroke={theme.text.secondary} strokeWidth="1.5" />
          <polyline points={poly(DATA.road)} fill="none" stroke={theme.stroke.primary} strokeWidth={Math.max(1.5, 30 * scale)} />
          {showZones && selected === 'P4' && <polyline points={poly(DATA.road)} fill="none" stroke={theme.accent.primary} strokeWidth="3.5" strokeDasharray="8 5" />}
          {showBuildings && DATA.buildings.map(b => {
            const [x,y,w,h] = b.rect; const p = project([x,y+h]);
            return <rect key={b.id} x={p[0]} y={p[1]} width={w*scale} height={h*scale} fill={b.group === 'Landmarks' ? theme.text.secondary : theme.fill.secondary} stroke={b.replaced ? theme.accent.primary : theme.stroke.primary} strokeWidth={b.replaced ? 0.8 : 0.5}><title>{b.id} · {b.replaced ? '本次已替换建筑范围' : '原作者建筑占地参考'}</title></rect>;
          })}
          {showZones && DATA.proposed_connections.map(c => {
            const a = DATA.crossings.find(p => p.station === c.from_station)!.point;
            const b = DATA.zones.find(z => z.id === c.zone)!.center;
            return <line key={c.zone} x1={project(a)[0]} y1={project(a)[1]} x2={project(b)[0]} y2={project(b)[1]} stroke={theme.accent.primary} strokeWidth="1.6" strokeDasharray="5 5" opacity="0.8"><title>拟步行联系，具体路线需绕开现有占地</title></line>;
          })}
          {DATA.lookouts.map((p,i) => <circle key={`l${i}`} cx={project(p)[0]} cy={project(p)[1]} r="2.7" fill={theme.text.secondary}><title>现有观景点 {i+1}</title></circle>)}
          {DATA.piers.map((p,i) => <rect key={`p${i}`} x={project(p)[0]-3} y={project(p)[1]-3} width="6" height="6" fill={theme.text.secondary}><title>现有码头 {i+1}</title></rect>)}
          {DATA.crossings.filter(c => visible(c.point)).map(c => <circle key={c.station} cx={project(c.point)[0]} cy={project(c.point)[1]} r="4" fill={theme.bg.editor} stroke={theme.text.primary} strokeWidth="1.5"><title>V16 第 {c.station} 站过街点</title></circle>)}
          {showZones && DATA.zones.filter(z => visible(z.center)).map(z => {const p=project(z.center);return <g key={z.id} onClick={() => choose(z.id)} style={{cursor:'pointer'}}>
            <circle cx={p[0]} cy={p[1]} r={z.id === selected ? 17 : 14} fill={z.id === selected ? theme.accent.primary : theme.bg.editor} stroke={theme.accent.primary} strokeWidth="1.5" />
            <text x={p[0]} y={p[1]+4} textAnchor="middle" fontSize="11" fontWeight="600" fill={z.id === selected ? theme.text.onAccent : theme.accent.primary}>{z.id}</text>
            <title>{z.name}</title>
          </g>})}
          {visible([0,0]) && <g><circle cx={project([0,0])[0]} cy={project([0,0])[1]} r="5" fill={theme.text.primary}/><text x={project([0,0])[0]+9} y={project([0,0])[1]+4} fontSize="12" fill={theme.text.primary}>公寓观景原点附近</text></g>}
        </g>
        <rect x="16" y="16" width="264" height="46" fill={theme.bg.editor} />
        <text x="26" y="34" fontSize="12" fill={theme.text.primary}>实线 / 灰色：现有场地与建筑参考</text>
        <text x="26" y="53" fontSize="12" fill={theme.accent.primary}>斜线：设计包络　虚线：拟步行联系</text>
        <path d={`M30 ${H-35} v6 h${ruler*scale} v-6`} fill="none" stroke={theme.text.primary} strokeWidth="1.5" />
        <text x="30" y={H-44} fontSize="12" fill={theme.text.primary}>{ruler.toLocaleString()} m</text>
        <text x={W-24} y={H-16} textAnchor="end" fontSize="11" fill={theme.text.secondary}>横轴 UE X（m） · 纵轴 UE Y（m，向上）</text>
      </svg>
      <Text size="small" tone="secondary">来源：岸线与道路制作源码、楼群作者记录、44 栋替换包围盒和 21:49 保存回执。未读取实时关卡；候选范围含需避让的占地，斜线区域不代表全部可直接铺设。这里是设计图，不是游戏截图。</Text>
      <Row gap={8} wrap>{DATA.zones.map(z => <Button key={z.id} variant={selected === z.id ? 'primary' : 'secondary'} onClick={() => choose(z.id)}>{z.id} {z.name}</Button>)}</Row>
      <Grid columns="repeat(auto-fit, minmax(300px, 1fr))" gap={24}>
        <Stack gap={10}><Row gap={8} wrap><Pill>{zone.priority}</Pill><Text size="small" tone="secondary">{zone.area}</Text></Row><H2>{zone.name}</H2><Text>{zone.purpose}</Text><Text tone="secondary">{zone.anchor}</Text><Text size="small" tone="tertiary">核心候选 UE XY：{zone.center.map(v => v.toFixed(1)).join(' / ')} m。地表标高在制作阶段适配。</Text></Stack>
        <Card><CardBody><Stack gap={10}><H3>空间组成</H3><ul style={{margin:0,paddingLeft:20,lineHeight:1.9}}>{zone.elements.map(e => <li key={e}>{e}</li>)}</ul><Divider/><Text size="small">{zone.density}</Text></Stack></CardBody></Card>
      </Grid>
    </Stack>}

    {tab === '构件与素材' && <Stack gap={20}>
      <H2>大形体清楚，细节随观看距离分配</H2>
      <Table headers={['构件','初始设计尺寸','制作要求']} rows={facilities}/>
      <Text size="small" tone="secondary">尺寸为本项目美术起点，单位为最终世界米，不是建设法规；后续按实际承载面、冠幅与道路净空适配。</Text>
      <Divider/><H2>直接使用已有库，控制素材家族</H2>
      <Table headers={['素材分工','已找到的候选包']} rows={DATA.asset_groups.map(g => [g.name,g.paths.map(p => p.split('/').pop()).join('、')])}/>
      <Text size="small" tone="secondary">以上为文件存在的候选清单，尚未在 UE 读取其类型、尺寸、材质与 LOD。PN 地被 72、花草 96、草丛 110、热带植物 20 个目录包并非全量使用。</Text>
      <Grid columns="repeat(auto-fit, minmax(300px, 1fr))" gap={24}>
        <Stack gap={9}><H3>表面与水景</H3><Text>石材、金属、树干和叶片保留相应法线与粗糙度。喷泉分开池底、池沿、水面、流束和落点；远端保留大形体，退掉细小飞沫。</Text></Stack>
        <Stack gap={9}><H3>植物组织</H3><Text>主树群、林缘灌木、成片地被形成层次。远处采用实例与适当代理，黑杨作者资源先明确静态输出；不给远景每株树挂骨骼更新。</Text></Stack>
      </Grid>
    </Stack>}

    {tab === '实施顺序' && <Stack gap={20}>
      <H2>先形成完整的一段城市公共空间</H2>
      {phases.map(([n,title,body]) => <Row key={n} gap={16} align="start"><Pill>{n}</Pill><Stack gap={6}><H3>{title}</H3><Text>{body}</Text></Stack></Row>)}
      <Divider/>
      <Grid columns="repeat(auto-fit, minmax(300px, 1fr))" gap={24}>
        <Stack gap={9}><H3>首批制作配额</H3><Text>中景乔木约 220–320 株，包含替换现有 94 株；远岸先做 40–60 个树群单元。数量服从冠幅和地块，不按空地面积机械铺满。</Text><Text size="small" tone="secondary">这些是设计配额，没有测试帧率、显存或实际视线覆盖。</Text></Stack>
        <Stack gap={9}><H3>接入既有公寓</H3><Text>按部件移除旧树体与旧灌木，保留道路、门厅、树池及车流语义。新景观挂在现有外景续接之后，统一更新静态倒影，不另建测试地图。</Text></Stack>
      </Grid>
      <Text>河口、水域、车流路径、门厅入口、码头登船口、地标基座和广告投射空间均参与放置排除。当前为方案交付，尚未修改正式场景。</Text>
    </Stack>}

    <Divider/>
    <Row justify="space-between" wrap gap={12}><a href={documentPath} style={{color:theme.text.link}}>完整城市设计方案</a><a href={dataPath} style={{color:theme.text.link}}>分区与素材数据</a><Text size="small" tone="secondary">未启动 UE · 未改地图 · 未运行测试</Text></Row>
  </Stack>;
}
'''
canvas.write_text(header+'const DATA = '+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n'+body,encoding='utf-8')
print('Planning canvas saved:',canvas)
production=P/'SourceAssets/CyberpunkUrbanLandscape20261025'
if (production/'installed.json').exists():
 import runpy
 runpy.run_path(str(production/'sync_delivery.py'),run_name='__main__')
