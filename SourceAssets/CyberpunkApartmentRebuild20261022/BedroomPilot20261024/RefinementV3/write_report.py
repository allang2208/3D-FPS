from pathlib import Path
import json,csv
R=Path(__file__).resolve().parent;PROJECT=R.parents[3]
def read(p):return json.loads(p.read_text('utf8'))
saved=read(R/'installed.json');assets=read(R/'assets_saved.json');checks=read(R/'Audit/after/intersections.json');clear=read(R/'Audit/after/clearances.json');readback=read(R/'saved-assets-readback.json');geometry=read(R/'source-geometry.json')
before=read(R.parent/'RefinementV2/assembly.json');previous={r['key']:r for r in before['meshes']}
if checks['pairs'] or any(s['contacts'] for s in clear['sweeps']):raise RuntimeError('Unresolved placement contact')
if any(r['degenerate_uv_triangles'] for r in geometry):raise RuntimeError('Collapsed UV remains')
if any(r['boundary_edges'] or r['nonmanifold_edges'] for r in geometry if r['key'] in {'BedRefined','ReadingFixture'}):raise RuntimeError('Lamp shell remains open')
changes={
 'Headwall':'提高圆角与支座曲面密度，校正软包织纹、木纹和金属表面尺度',
 'ServiceSpine':'圆形端口与旋钮加密，修正文字符号焊接及涂装/金属材质',
 'ReadingFixture':'连续封闭空腔灯罩、内缩扩散片；不透明单面材质，保留原灯光调度',
 'BedsideTray':'托盘圆角、腕表环、螺钉与设备面板细化，校正贴图尺度',
 'BedsideBooks':'重建分层页块、书皮、圆书脊、包角、头带与浮雕印字；杯口及把手加密',
 'BedRefined':'移除原低段数弯臂灯，重建连续弯管/安装座/有厚度灯罩/内缩透光片，平顺被褥转角',
 'FootThrow':'跟随被褥新曲面，保留厚度与流苏；按纱线尺度修订法线和粗糙度',
 'BedRug':'修订绒面纹理物理尺度，保留贴地和包边净距',
 'WindowBench':'软包圆角与框架细化，补固定螺钉和布料/木材表面',
 'BenchFoldedLinen':'保留三层闭合折叠体与承托关系，提升织物法线和表面尺度',
 'LaundryBasket':'篮沿、编织杆与提手圆面加密，修复布料封边退化 UV，保留布料净距',
 'WallShelf':'重建七册立书与两册平放书，陶盆内外壁/卷口/土层及 36 片有厚度曲面叶片，增加叶脉和纸页 PBR',
 'DeskLife':'桌面书籍、杯具、笔筒和印字细化，保持键鼠与电源面板净空',
 'Headphones':'加密头梁、耳罩、支架与线缆，补细孔/螺钉，升级软垫和涂装表面',
 'DeskCableTray':'提升走线弯曲和圆截面精度，保留抽屉/桌腿避让',
 'DeskRail':'横栏曲面、连接件与字面细化，修正印字 UV',
 'Slippers':'优化圆角与实体鞋面法线，修订橡胶和织物表面尺度',
}
with (R/'upgrade-matrix.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['component','V2_LOD0_triangles','V3_LOD0_triangles','change'])
    for key,row in assets['meshes'].items():w.writerow([key,previous[key]['triangles'],row['triangles'],changes[key]])
summary=dict(stage='saved_and_scoped_checks_complete',map=saved['map'],saved_at=saved['saved_at'],meshes=len(assets['meshes']),materials=len(assets['materials']),new_texture_maps=len(assets['textures']),unique_source_triangles=sum(r['triangles'] for r in assets['meshes'].values()),previous_unique_source_triangles=sum(r['triangles'] for r in previous.values()),source_uv_degenerate_triangles=0,closed_lamp_meshes=True,inventory_components=checks['components'],unintended_layout_contacts=len(checks['pairs']),retained_installation_contacts=len(checks['installation_contacts']),door_samples=sum(s['samples'] for s in clear['sweeps']),normal_readback_materials=len(readback['materials']),game_run=False,preview='Blender source mesh with real material source textures; not UE gameplay')
(R/'completed.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
table='\n'.join(f"| {k} | {previous[k]['triangles']:,} | {v['triangles']:,} | {changes[k]} |" for k,v in assets['meshes'].items())
text=f'''# 卧室试点 V3：灯具、近景结构与材质修订

已保存地图 `{saved['map']}`，时间 {saved['saved_at']}。
本轮按用户两张截图及原精细建模标准修订，原公寓与其他房间的共享模型、材质未替换。

## 本轮定位

- 截图中的弯臂灯属于床网格；原版保留了低段数管段与封口式灯头。本轮移除该局部并重建有厚度、法线向外的灯罩与内缩扩散片；新增方形壁灯同时改为连续空腔壳体。
- 架上原叶片为重复四边形，立书缺真实页块和装订结构；已按近景观察重建。
- 读取原资产发现 14 类试点材质已有 Normal 连接，但纸张/陶瓷等依赖弱通用噪声，部分封边 UV 退化，织物平铺过密。此次分别修订结构、UV 和表面，不以是否存在贴图引用代替观感判断。

## 组件清单

下表面数为作者 LOD0 三角形，按独立网格统计，非 Nanite 回退网格，也不代表同屏帧率。

| 组合件 | V2 | V3 | 修改 |
| --- | ---: | ---: | --- |
{table}

## 材质与保存证据

- {summary['materials']} 类本试点独立材质，已编译并从保存资产读回 Normal 连接、贴图采样类型和材质槽。
- 新增 {summary['new_texture_maps']} 张 2048 贴图：纸纤维、纸页边、陶瓷釉面、土壤、叶脉的 BaseColor / DirectX Normal / ORM。为原创解析材质，不宣称实拍扫描。
- 木纹、金属、橡胶、布料继续复用项目内 2K–4K 材质库，并按真实尺度修订法线强度与粗糙度。复用源保持原样。
- 精细书架、薄片和两类灯具保留完整传统 LOD0，其他适合的组合件沿用 Nanite；没有修改全局画质或纹理池。
- `assets_saved.json`、`installed.json`、`saved-assets-readback.json` 分别记录已保存资产、地图和实际读回结果；`production-final.json` 为最终后台批次退出回执。

## 用户要求范围内的检查

- 两类灯具所在网格无开放边、非流形边；全部 17 个导出网格的有效表面未发现退化 UV 三角形。
- 已保存房间 75 个相关组件的范围内，未处理的外部布局穿插为 0；4 组植株入土及机箱固定接触单列保留。
- 7 个储物格共 460 个开合位置采样未发现与周边陈设相交；床品、篮布和承托关系仍按上一轮范围复查。
- 字面浮雕有两处极小轮廓连接的非流形记录，局限于印字网格，不在灯壳或家具结构；详见 `source-geometry.json`。
- 已查看真实模型和贴图的 Blender 近景图；没有启动 UE 编辑器、游戏或 PIE，实际游戏光照、使用体验与最终观感由用户确认。

## 近景制作图

以下是 Blender 源模型配实际材质纹理的检查图，不是游戏截图。

![书架近景](../SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/RefinementV3/Review/shelf.png)
![弯臂灯](../SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/RefinementV3/Review/bed-lamp.png)
![连续壳体壁灯](../SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/RefinementV3/Review/wall-lamp.png)

```text
open /Game/GameMaps/L_CyberpunkApartment
```
'''
text=text.replace('../SourceAssets/CyberpunkApartmentRebuild20261022/BedroomPilot20261024/RefinementV3/',R.as_posix()+'/')
(PROJECT/'Docs/CyberpunkBedroom-PilotV3-20261024.md').write_text(text,encoding='utf8')
(R/'README.md').write_text(text,encoding='utf8')
print(json.dumps(summary,ensure_ascii=False))
