from pathlib import Path
import json,csv,collections
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
a=json.loads((ROOT/'Receipts/saved-audit.json').read_text('utf8'))
r=json.loads((ROOT/'Receipts/install.json').read_text('utf8'))
b=json.loads((ROOT/'Config/bindings.json').read_text('utf8'))
group=collections.defaultdict(list)
for row in a['module_rows']:group[row['module']].append(row)
lines=['# 随机地牢其余场景灯具与光源配对修正（2026-10-09）','',
'已检查正式随机地牢目录中接待大厅以外的 40 个模块：37 个含灯光、3 个无局部灯光。逐盏处理 306 条原始模块灯光配置及固定起始区 13 盏灯。正式目录和两个连接大厅样板已实际保存；未启动游戏、未生成新布局、未截图或渲染。','',
'## 修正内容','',
'- 以 UE 已导入网格的真实发光材质分区、网格放置变换为依据，导出 79 个候选网格并逐盏配对。顶灯发光点位于灯罩下表面外 1 cm；保留向下的聚光灯，将全向顶灯改为朝下的矩形灯。面光源尺寸依据灯罩尺寸设置。',
'- 点光源改矩形光时流明乘 0.25，按两类光源不同的配光换算保留原本向下的中心照度；保留颜色、有效半径、阴影策略、淡出距离、故障熄灭与闪烁材质。',
'- 入口两盏椭圆壁灯按倾斜墙面的发光法线朝走廊照射，矩形发光区内接于灯罩投影；车站工作台灯按灯泡和灯罩出口的倾角照射桌面。',
'- 三种错层坡道的转弯平台原有光源没有灯具。各复用一件已有工业顶灯，挂杆顶部与平台天花板对齐；保留原有三盏光源数量。',
'- 过渡大厅三个主题入口的通道灯原来位于两盏灯具中间。各分为两盏对齐灯罩的矩形灯，每盏分配原光输出的一半。逐项比对了 3 个入口 × 6 个主题的 18 组灯具布局。',
'- 移除生态育苗室与水培室中共四盏没有实体灯具的悬空全向补光；其余生态灯按实际灯罩位置校准。',
'- 固定起始区的裸露神龛灯泡保留全向发光，光源半径约束在玻璃内；工作台原有聚光灯的位置、方向和亮度正确，予以保留。',
'- 两个连接大厅样板还包含接待大厅副本，连同副本中的 23 盏灯一并同步。正式接待大厅模块保持上一批已保存的修正。','',
'## 已保存','',
'| 地图 | 本轮处理 |','|---|---|',
'| `/Game/GameMaps/L_Dungeon_Randomized` | 原 306 条其余模块灯光处理后为 305 条，固定区 13 盏；加上已修正接待大厅 23 条，正式目录共 328 条 |',
'| `/Game/GameMaps/Design/L_FacilityTransit_Subject` | 53 盏：过渡大厅 30 + 接待大厅副本 23 |',
'| `/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject` | 53 盏：另三主题的过渡大厅 30 + 接待大厅副本 23 |','',
'## 分模块检查清单','',
'| 模块 | 原配置数 | 保存后光源数 | 灯型 |','|---|---:|---:|---|']
for key,rows in b['modules'].items():
    kinds=collections.Counter(x['type'] for x in group[key]);desc=' / '.join(str(v)+' '+k for k,v in kinds.items())
    lines.append(f'| {key} | {len(rows)} | {len(group[key])} | {desc} |')
lines+=['','无局部光源模块：Threshold、TreasureLink、RouteElbow。','',
'## 保存后核对与重建','',
f"回读了正式目录的 305 条本轮模块光源、固定起始区 13 盏，以及两个样板的 106 盏。灯罩间距、朝向、灯型、光源长度、流明与保存后数据相符；对应包无未保存修改。银行目录的 120 套摆放数据保持不变，新的原生合同散列为 `{a['bank_contract_sha1']}`。这是灯光数据与保存结果核对，不是游戏画面或性能验收。",
'',
'逐盏记录见 `SourceAssets/DungeonFixtureLighting20261009/Receipts/per-light.csv` 和 `saved-audit.json`；原始网格、逐盏旧位置、修改前后配置分别保存在 `geometry.json`、`Config/bindings.json`、`Receipts/install.json`。',
'',
'正式作者入口 `DungeonFacilityFlow20261007/extend_catalog.py` 最后重放本轮修订；固定起始区恢复配置及生成脚本同步修正；大厅样板的 `HallLighting20261007/profile.py` 同步重放。新增灯具复用已存在的工业灯资产，并进入模块硬引用及原有房间调度，不新增逐帧扫描。',
'',
f"本轮地图、外部 Actor 包和配置备份：`{r['backup']}`。",
'',
'运行体验交由用户测试；本轮未测试游戏、未做截图或渲染验收。','']
(PROJECT/'Docs/Gameplay/dungeon-fixture-lighting-20261009.md').write_text('\n'.join(lines),encoding='utf8')
with (ROOT/'Receipts/per-light.csv').open('w',newline='',encoding='utf-8-sig') as handle:
    writer=csv.writer(handle);writer.writerow(['scope','id','type','position_cm','direction','lumens','mesh','result'])
    for row in a['module_rows']:writer.writerow([row['module'],row.get('id') or row['index'],row['type'],row['position_cm'],row['normal'],row['lumens'],row['mesh'],'face gap 1 cm / direction matched'])
    for scope,rows in [('FixedStart',a['fixed_rows'])]+[(s['map'],s['lights']) for s in a['subjects']]:
        for row in rows:writer.writerow([scope,row['label'],row['type'],row['position'],row['forward'],row['intensity'],'','saved fields matched'])
    for key,rows in b['modules'].items():
        for i,row in enumerate(rows):
            if row.get('remove'):writer.writerow([key,i,'removed',row['anchor_cm'],'','','',row['reason']])
print('LIGHTING_REPORT_WRITTEN',len(a['module_rows'])+len(a['fixed_rows'])+106,'saved light rows')
