# 员工生活主题：正式随机地牢接入

用户已认可生活区构建，指定接入完整随机地牢。正式目标为
`/Game/GameMaps/L_Dungeon_Randomized`。

## 内容与抽选

新增第四个候选主题 `staff_living`，保留原有主题，每次地牢从四个主题中无重复选取三个，
仍使用三个分支与原有共用档案中心。生活主题保持固定先后顺序：

`StaffDormitory → StaffChangingShowers → StaffRecreation`。

三间房复用用户认可的 V7 资产，包含完整瓷砖、墙内厕所、接墙水壶、正常比例标识字体、
咖啡机空腔与杯子、布料、蓝色地毯和体育设施。不重建几何或退回早期修订。
模块体积纳入外墙厚度，作者端口位置保持不变；刷怪沿用现有 Distribution 怪物池与
已预留的 encounter 锚点，每房配置 3–5 个刷怪槽，进入现有封门、清怪和分支流程。

## 家具与搜寻容器

`StaffLivingRoomAssembly` 在装配前按 Seed 与节点选择宿舍家具和休息室椅子布局。
六间宿舍保留床位，通过四种已制作的家具方案分配书桌、椅子、书柜、书架和床头柜；
方案袋避免相邻重复。静态家具和相应容器使用同一份位置选择。

67 个容器由现有 `AColdSteelSceneContainer` 独立实例承载，使用
`Run<Seed>.Node<Node>.<作者容器ID>` 标识。保留准星聚焦后的绿/黄轮廓、原宝箱面板、
柜门旋转或抽屉平移、首次搜寻后保持打开，以及已有柜子随机开启标签。
奖励表仍待用户后续设计，不添加掉落内容。

容器网格走生成器已有的分批资源队列，实例进入节点所有权、装配隐藏、恢复碰撞和
销毁流程。轮廓材质作为生产地图中的独立后处理效果保存。

## 文件与执行入口

- `SourceAssets/DungeonStaffLiving20261002/Production20261002/Config/modules.json`：三间正式作者模块。
- 同目录 `Config/catalog-pending.json`：待正式落盘的完整四主题目录，不供当前旧二进制使用。
- `Scripts/build_native.ps1`：在现有 UE 批次互斥下构建 Editor 和 Game。
- `Scripts/install_background.ps1`：两种目标构建成功后，后台更新正式地图、同步目录并保存车站样板。
- `Scripts/retire_subjects.py`：正式地图保存后，将四张生活区样板归档到 trash，记录散列；共用资产和 Blender 源保留。
- `Receipts/native-build.json`、`Receipts/install.json`：分别记录实际构建与正式地图保存状态。

主题目录重建入口已接入生活区扩展；以正式保存回执启用，避免后续重建退回三主题。
旧生活区导入与制作入口在正式接入后转向生产入口，避免重新生成已退役样板。

## 本次状态

Editor、Game 构建均已成功，正式地图已通过后台 commandlet 保存，生活主题已启用。
`Receipts/native-build.json` 为 `stage=binaries_saved`；`Receipts/install.json` 为
`stage=map_saved`，记录四主题候选、三个分支、67 个搜寻容器和 747 个总硬依赖。
主题目录已同步至 Routes、ThemedRoutes、SplitLevels 制作源。

四张生活区旧样板已归档，安装回执的 `samples_retirement` 为 `archived`。
恢复清单在 `trash/staff-living-subjects-retired-20261002/manifest.json`。
正式地图原文件与原目录已在本次 `Backup` 中保留。

未启动可交互编辑器、游戏、PIE、截图、渲染或测试；用户自行试玩。

车站完整线路样板已另行保存，见 [车站线路样板](dungeon-station-line-subject-20261002.md)。
