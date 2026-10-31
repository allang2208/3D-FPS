# 赛博朋克卧室试点

> **已正式接入现有公寓，独立试点已退役。** 当前入口为 `open /Game/GameMaps/L_CyberpunkApartment`；下文保留当时的制作记录。正式接入记录见 `Docs/CyberpunkBedroom-Integration-20261024.md`。

当前迭代为 **V3 灯具、近景结构与材质修订**，制作源、逐项处理记录和检查证据见
[RefinementV3/README.md](RefinementV3/README.md)。下文保留 V1 制作记录；V3 已安装时，
`publish.py` 和 `install_level.py` 自动转入 V3，避免重新安装旧版覆盖修复。

## V1 制作记录

目标：把视频中的精确结构、生活陈设、材质和分层照明用于现有公寓 Bed2。

原地图 `/Game/GameMaps/L_CyberpunkApartment` 作为只读来源。试点保存为
`/Game/GameMaps/Design/L_CyberpunkBedroom_Pilot20261024`，玩家出生点设在卧室内。
最终是否已保存以本目录 `installed.json` 的 `stage: map_saved` 为准。

2026-10-24 12:20（UTC+8）已完成材质编译、16 个模型导入、17 组陈设装配、2 盏房间调度阅读灯及独立地图保存。
`assets-02.json`、`map-02.json` 均记录进程退出码 0，`completed.json` 为 `production_saved`。
原公寓地图未由本任务修改，游戏与视觉效果仍由用户测试。

## 制作范围

- 灰黑吸音床头饰面、烟熏木侧条、铜色细收边、真实通风格栅和床边供电脊。
- 两盏有灯罩和出光面的暖色阅读灯，绑定原 `ApartmentAtmosphere` 的 Bed2 房间调度和 `FixtureLevel`。
- 原床本体只设置独立材质覆盖；保留模型、位置、缩放、碰撞与休息动作接触。新增床尾搭毯、低绒地毯和拖鞋。
- 床头托盘、移动设备、腕表、装订书本和带内壁的杯子。
- 窗边软包凳、折叠织物、带底面/内壁/提手的编织收纳篮。
- 有承托支架的壁架、书本和陶盆；书桌增加耳机架、笔筒、便笺、杯子、走线托盘，以及固定到桌面的信息横栏。
- 新增内容按组合件导出，16 种网格；凳和收纳篮具有独立简单碰撞。支持 Nanite 的组在导入时完成构建。
- 新建 14 类本试点独占材质，复用项目现有法线、粗糙度与木纹来源；新模型 UV 使用米制物理尺度。床品保留既有 UV 比例校准。

## 作者链

1. `read_source.py` 读取当前保存公寓的床、桌、容器、灯具与活动区域作为制作资料。
2. `design.py` 保存风格、边界、材质规格。
3. Blender 后台运行 `author.py`，产出 `BedroomPilot_Source.blend`、`Meshes/*.fbx`、`assembly.json`。
4. `run_background.ps1 -Script build_assets.py -Run <新批次名> -CompileMaterials` 导入新资产并完成材质编译。
5. `run_background.ps1 -Script install_level.py -Run <新批次名>` 创建独立地图、组装卧室并保存。

只保存本试点资产及新地图，不向原公寓 V20 的正式重建链注册；用户认可后再按 Bed2 范围接入。
复制来源时保留最新已保存的其他房间、海湾、阳台、设备和储物功能。
重新安装按本试点 Actor 标签更新，不重复叠加；不会生成每个螺钉独立 Actor 或新增逐灯 Tick。

## 用户体验入口

资产及地图保存完成后，在开发游戏控制台输入：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

返回原公寓：

```text
open /Game/GameMaps/L_CyberpunkApartment
```

不改变默认地图，也不自动将试点加入打包烹饪清单。
本轮不启动游戏、PIE、预览渲染、截图或运行测试；源制作、编译与保存回执不代表用户视觉/玩法验收。
