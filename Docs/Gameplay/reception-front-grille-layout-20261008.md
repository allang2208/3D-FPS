# 接待大厅正门与等候区调整（2026-10-08）

用户要求：复用已有铁栅门封住大厅正门，移开挡门的桌椅，修复门框闪动，翻正两侧告示牌。

## 修改范围

- 正式地图 `/Game/GameMaps/L_Dungeon_Randomized` 的 `FacilityReceptionHall` 模块。
- 复用 `/Game/Dungeons/AtmosphereV2/GateWater/Meshes/SM_DungeonRefinedGrille`，保留现有焊接网格、铰链、锁具、材质和碰撞。设为固定关闭的设施正门；正式路线仍从侧破洞进入。
- 两组西侧沙发中心调整为模块局部 UE 厘米 `(-2290,1050,0)` 和 `(-2290,-1050,0)`。茶几保持在各自沙发前方，杯子、杂志与托盘随整组移动；保留中心正门前的空间。
- 整体替换旧 `PortalFrames`：两端门洞的金属门框下表面比混凝土/门廊顶板低 35 mm，避免顶面共面闪动；立框在横框下表面终止，不重复叠面。
- 西侧两块落地告示牌及紧固件绕支架中心旋转 180°，文字朝向大厅，保留原 UV 与比例。
- 门头牌等比调整至原尺寸的 `1.9/3.2`，完整放入门楣与二楼板之间，避免顶部文字被遮挡。
- 保留已完成的侧入口灯光、工作台与神像起始区、主题路线、端口和占用范围。

## 制作与接入

源文件：`SourceAssets/DungeonFacilityFlow20261007/FrontEntry20261008/`。
新修订网格命名空间：`/Game/Dungeons/FacilityFlow20261007/FrontEntry20261008/`。
按既有 Blender 源局部调整牌面、紧固件和桌面附件；不修改共享铁栅门资产。
后续正式配方重建通过 `extend_catalog.py` 的已安装修订入口保留本次设计。
写入前备份地图及外部 Actor/Object 包，并保留当前完整配方。布局库仅重新绑定配方签名，布局位置不改变。

## 状态

用户关闭 UE 后，四组修订网格及正式地图配方已在后台完成导入和保存。铁栅门直接复用现有资产，没有重新建模或修改源资产。
`install-receipt.json` 与 `latest-attempt.json` 均记录 `map_saved`；重建入口已启用。
保存日志：`SourceAssets/DungeonFacilityFlow20261007/Receipts/import-20261008-220256.log`，进程退出码 0。
当前配方签名：`a2cd088d50d9966f50df9286768613299a4d203f`。备份目录为本批 `Backups/20261008-220325/`。

未启动游戏、截图、渲染或测试；最终视觉与走路体验由用户测试。

## 2026-10-09 入口左右收口补齐

根据用户斜视截图，原门框后沿停在模块 X=-2424.5 cm，铁栅门位于 X≈-2453.3～-2436.6 cm，侧向视角会露出进深断口。已将西入口左右立框及门楣后沿延伸至 X=-2479 cm，与既有门体、雨棚侧墙相接；朝大厅的前沿和东侧门框保留。采用替换完整门框组合件，未叠加共面的遮挡片。

新资产：`/Game/Dungeons/FacilityFlow20261007/EntryFrameFit20261009/Meshes/SM_EntryFrameFit_PortalFrames`。Blender 源、FBX、导入脚本及地图备份位于 `SourceAssets/DungeonFacilityFlow20261007/EntryFrameFit20261009/`。已通过后台 commandlet 导入并保存正式随机地牢地图（exit 0），全目录重建也保留该修订。未启动编辑器界面、PIE、截图或验收测试。重新生成地牢后查看。
