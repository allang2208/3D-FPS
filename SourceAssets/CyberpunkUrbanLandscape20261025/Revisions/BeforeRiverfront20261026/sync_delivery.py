"""Update the existing planning document / canvas from the saved production receipts."""
from pathlib import Path
import json,collections,re
R=Path(__file__).resolve().parent;P=R.parents[1]
layout=json.loads((R/'layout.json').read_text(encoding='utf8'));saved=json.loads((R/'installed.json').read_text(encoding='utf8'));assets=json.loads((R/'assets_saved.json').read_text(encoding='utf8'))
if saved['counts']!=layout['counts'] or saved['reflection']!='native_cube_saved':raise RuntimeError('Wait for final publication before writing delivery status')
counts=layout['counts'];fixture_counts=dict(collections.Counter(r['kind'] for r in layout['fixtures']))
delivery=dict(saved_at=saved['saved_at'],map=saved['map'],counts=counts,fixtures=fixture_counts,geometry_assets=len(assets['meshes']),plant_blueprints=len(assets['blueprints']),actors=len(saved['actors']),reflection=saved['reflection_texture'],tests_run=False)
(R/'delivery.json').write_text(json.dumps(delivery,ensure_ascii=False,indent=2),encoding='utf8')
details={
 'P1':['26 m 中央喷泉、9 道弧形水束','70 株乔木、180 组灌木地被','环路、过街连接与池边长椅'],
 'P2':['10.4 m 浅池与林下座椅','70 株乔木、160 组灌木地被','林荫环路与街道连接'],
 'P3':['0.6 / 1.2 m 两级台地，15 cm 踏步','约 1:20 连续缓坡与栏杆开口','9 m 台上浅池、60 株乔木、160 组林下植物'],
 'P4':['替换 94 株旧道路树，保留原种植池','替换门厅与观景点的 102 组粗糙灌木','6 个街角：亭棚、座椅、双花池、导视、垃圾箱'],
 'P5':['60 个树群单元、508 株乔木','三处浅池节点与连续园路','220 组林缘植物、成片草地材质'],
 'P6':['30 个树群单元、205 株乔木','0.6 m 观景平台、台阶和缓坡','折线园路与 100 组林缘植物']}
doc=P/'Docs/Art/CyberpunkUrbanLandscape-Masterplan-20261025.md'
text=doc.read_text(encoding='utf8')
text=re.sub(r'\n<!-- URBAN_DELIVERY_BEGIN -->[\s\S]*?<!-- URBAN_DELIVERY_END -->\n','\n',text)
text=text.replace('2026-10-25。状态：方案与选址数据已保存，尚未制作或接入本轮景观资产。唯一目标地图为','2026-10-25。状态：六分区景观资产与静态反射已接入并保存。唯一目标地图为')
intro='\n<!-- URBAN_DELIVERY_BEGIN -->\n## 本轮落盘记录\n\n'
intro+=f"保存时间：{saved['saved_at']}。正式地图：`{saved['map']}`。制作入口：`SourceAssets/CyberpunkUrbanLandscape20261025/`，派生资产根：`/Game/Props/CyberpunkUrbanLandscape20261025/`。\n\n"
intro+=f"已保存 {len(assets['meshes'])} 个网格资产、6 个分区植物蓝图、{counts['plants']:,} 个植物实例和 {counts['fixtures']} 组公共设施。植物含 1,007 株乔木、278 组灌木和 656 组地被/花草；其中道路树为替换原有 94 株。6 个街角组合采用避开现有树冠和入口的候选位置。\n\n"
intro+='| 分区 | 本轮已制作并接入 |\n| --- | --- |\n'
for zid,items in details.items():intro+='| '+zid+' | '+'；'.join(items)+' |\n'
intro+='\n新增公共设施按装配组计数：'+ '、'.join(f'{k} {v}' for k,v in fixture_counts.items())+'。34 张独立长椅之外，亭棚、台地和观景平台内也包含固定座椅。\n\n'
intro+='草地、土壤与缺失的白杨树皮法线已制作 7 张 1024 贴图。白杨叶片改用独立的受光、双面裁切材质并接入库内匹配法线，其余所选植物保留原贴图与透明裁切。派生植物材质去除风位移，按约 200 m 空间格分组 HISM；小型地被与灌木设置距离剔除。刚性构件有实体厚度、倒角、UV 与对应表面材质。\n\n'
intro+='仅替换 `AP16_Trees` 中旧树干/树冠，以及 3 组 `AP18_Frontage`、2 组 `AP18_Lookouts` 的旧叶片角色。保留合并网格内的树池、门厅和平台。新景观接在既有外景 `apply_upgrade` 之后，后续重建按同一标签更新，避免叠放旧树。\n\n'
intro+='已制造并绑定含新绿化的 6 面 × 2048 HDR 静态城市反射；水面与喷流从静态捕获清单中分开。没有新增实时捕获、动态灯或逐树 Tick。公园沿用外围静态布景的碰撞策略，本轮不包含导航和可交互公园玩法。\n\n'
intro+='本轮读取过实际资产尺寸、材质和正式地图对象，布局生成使用陆地、楼体与地标基座、道路、门厅通路等排除范围；这属于制作过程，不是穿模验收。未运行游戏、视觉或性能测试，也未为验收截图。由用户在游戏中测试。\n\n'
intro+='以下保留原总体设计与初始配额；实际接入内容以上述记录、`delivery.json` 和 `installed.json` 为准。初始候选中的售卖点、单独自行车架、额外店铺立面与叠水墙未作为本批新构件制作，现有建筑首层继续保留。\n<!-- URBAN_DELIVERY_END -->\n'
pos=text.index('\n## 1.');text=text[:pos]+intro+text[pos:]
text=text.replace('没有打开 UE、读取实时关卡、截图或开展验收；以下位置是依据作者资料的设计包络','最初方案阶段没有打开 UE、读取实时关卡、截图或开展验收；以下原始位置是依据作者资料的设计包络')
text=text.replace('这两个名称是计划中的制作入口，本轮未创建 UE 资产。','这两个名称现已用于正式制作与接入，落盘结果见顶部记录。')
text=text.replace('本轮交付是总体设计文档、带现有几何基底的交互规划图和机器可读选址数据。没有改动正式地图，没有新建测试场景，没有进行游戏、穿模、视觉或性能验收。','原方案交付是总体设计文档、交互规划图和选址数据。本次实施已保存正式地图与景观资产，没有新建测试场景，没有进行游戏、穿模、视觉或性能验收。')
doc.write_text(text,encoding='utf8')

canvas=Path(r'C:\Users\allan\.cursor\projects\d-FPS3D\canvases\cyberpunk-urban-landscape-20261025.canvas.tsx')
text=canvas.read_text(encoding='utf8');a=text.index('const DATA = ')+len('const DATA = ');b=text.index(';\n',a);data=json.loads(text[a:b])
data.update(stage='formal_map_saved',saved_at=saved['saved_at'],evidence_boundary='Authored coordinates and production save receipts; no gameplay or visual acceptance.')
for z in data['zones']:
    actual=next((r for r in layout['zones'] if r['id']==z['id']),None)
    if actual:z['center']=actual['center'];z['polygon']=actual['boundary'];z['area']=f"实际生成区域 {actual['area_m2']:,.0f} m²"
    z['priority']='已接入';z['elements']=details[z['id']];z['density']=f"已保存 {counts['by_zone'][z['id']]} 个植物实例";z['anchor']='位置由实际承载面、建筑及通路排除范围生成。'
text=text[:a]+json.dumps(data,ensure_ascii=False,separators=(',',':'))+text[b:]
text=re.sub(r'^const BUILT = .*?;\n','',text,flags=re.M)
built=dict(zones=[dict(id=z['id'],paving=z['paving_triangles']) for z in layout['zones']],trees=[[p['p'][0],p['p'][1],p['height']*.3,p['zone']] for p in layout['plants'] if p['mesh'].startswith('Tree')],fixtures=[[p['p'][0],p['p'][1],p['kind']] for p in layout['fixtures']],counts=counts,saved_at=saved['saved_at'])
pos=text.index('\n',text.index('const DATA = '))+1;text=text[:pos]+'const BUILT = '+json.dumps(built,separators=(',',':'))+';\n'+text[pos:]
start=text.find('          {showZones && DATA.proposed_connections.map')
if start>=0:
    end=text.index('          {DATA.lookouts.map',start)
    text=text[:start]+'''          {showZones && BUILT.zones.map(z => <path key={`built-${z.id}`} d={z.paving.map(t => 'M'+t.map(p => project(p).join(',')).join('L')+'Z').join(' ')} fill={theme.accent.primary} opacity="0.3" />)}
          {showZones && BUILT.trees.filter(p => visible(p as number[])).map((p,i) => <circle key={`tree-${i}`} cx={project(p as number[])[0]} cy={project(p as number[])[1]} r={Math.max(.8,Number(p[2])*scale)} fill={theme.accent.primary} opacity="0.7"><title>{String(p[3])} 已布置乔木</title></circle>)}
          {showZones && BUILT.fixtures.filter(p => visible(p as number[])).map((p,i) => <rect key={`fixture-${i}`} x={project(p as number[])[0]-2} y={project(p as number[])[1]-2} width="4" height="4" fill={theme.text.primary}><title>{String(p[2])}</title></rect>)}
'''+text[end:]
replacements={
 '设计方案 / 尚未接入关卡':'六分区已接入正式地图',
 '隐藏候选分区':'隐藏景观分区','显示候选分区':'显示景观分区','公园候选布局':'公园实施布局',
 '：设计包络，需扣除占地':'：已生成景观边界',
 '斜线：设计包络　虚线：拟步行联系':'色块：已生成步道　圆点：已布置乔木',
 '来源：岸线与道路制作源码、楼群作者记录、44 栋替换包围盒和 21:49 保存回执。未读取实时关卡；候选范围含需避让的占地，斜线区域不代表全部可直接铺设。这里是设计图，不是游戏截图。':'来源：实际场地读取、制作坐标和正式地图保存回执。显示生成的步道、乔木和设施位置；未进行游戏、视觉或性能验收。',
 '核心候选 UE XY：':'已落盘核心 UE XY：','地表标高在制作阶段适配。':'已按承载面标高接入。',
 '以上为文件存在的候选清单，尚未在 UE 读取其类型、尺寸、材质与 LOD。PN 地被 72、花草 96、草丛 110、热带植物 20 个目录包并非全量使用。':'本批使用 7 个植物网格家族；已读取选中资产的实际尺寸与材质，保留已有 LOD。库目录计数不代表本批使用量。',
 '首批制作配额':'本批保存数量',
 '中景乔木约 220–320 株，包含替换现有 94 株；远岸先做 40–60 个树群单元。数量服从冠幅和地块，不按空地面积机械铺满。':'1,941 个植物实例：近处 294 株乔木（含 94 株道路树替换），两片远岸 713 株乔木，另有 934 组灌木与地被。远岸组织为 60 + 30 个树群单元。',
 '这些是设计配额，没有测试帧率、显存或实际视线覆盖。':'数量来自制作和保存回执；帧率、显存、视线效果由用户测试。',
 '当前为方案交付，尚未修改正式场景。':'P1–P6 已保存到同一正式地图，重建续接已更新。',
 '未启动 UE · 未改地图 · 未运行测试':'后台导入与地图保存完成 · 未运行测试',
 '完整城市设计方案':'城市设计与落盘记录',
 '4–6 个街角组合':'6 个街角组合',
 '先形成完整的一段城市公共空间':'六分区制作与接入记录',
 '先完成':'已完成'
}
for old,new in replacements.items():text=text.replace(old,new)
text=text.replace("['中央公园浅池', '直径 24–30 m，主喷流高 2.5–4 m'","['中央公园浅池', '直径 26 m，喷流最高约 4 m'")
text=text.replace("['东段台地', '总高差 1.2–2.4 m，分 2–3 级'","['东段台地', '0.6 / 1.2 m 两级台地'")
text=text.replace("['叠水墙', '长 6–10 m，落差 0.6–1.2 m', '池体和落点连续，远端退掉飞沫但保留水面。']","['台上浅池', '直径 9 m，位于上层平台', '独立池体和水面，与台阶和缓坡留出联系。']")
text=text.replace("const dataPath = 'D:/FPS3D/FPSGAME/SourceAssets/CyberpunkUrbanLandscapePlan20261025/design.json';","const dataPath = 'D:/FPS3D/FPSGAME/SourceAssets/CyberpunkUrbanLandscape20261025/delivery.json';")
canvas.write_text(text,encoding='utf8')
print('URBAN_DELIVERY_UPDATED',saved['saved_at'],counts['plants'],counts['fixtures'],flush=True)
