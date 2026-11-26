---
name: ue5-landscape-authoring
description: 构建或修改 UE5 户外自然地编。适用于丘陵与森林高度场、村墙和道路接坡、林地 PCG 生态层、草被、湿地、岩壁与林雾，以及按丘陵景观或道路景观主题重建 FPSGAME 地图。
---

# 户外地编构建

**第一条　文件落盘与引用。** 在包含 `FPSGAME.uproject` 的工作副本，先查 `Docs/Production/README.md` 的功能条目和 `WORKFLOW.md` 第 4.1 节。由此确定可编辑原件、正式输出和工作目录。游戏资产用 `/Game/...` 包名，制作脚本相对工程根或已配置的源根寻址。交付时在同一条目登记实际位置、发布与恢复版本。

## 从需求选入口

- **丘陵景观**管山形、村墙整地、林内生态、草被、闭合水坑和林雾。**道路景观**管东门林道、采石场进场路、路床、路肩侵草和落叶。单主题外观修改直接走该主题的材质或点集配方。改变共享标高、中心线或水岸时，列出要一起更新的碰撞、遮罩和依附物。
- **先定位正在运行的图。** FPSGAME 正式地图为 `/Game/GameMaps/L_ForestPathVillage`，正式图使用林道子关卡副本，摄影样板为 `/Game/ForestPathStudy/Maps/L_ForestPathForest`。从目标组件反查它的地面材质实例、数据页、覆盖函数与灯光拥有者。相同的物体名称可能同时出现在这三处。
- **以项目数据选择配方。** 从工程根读 `Tools/WorldGeneration/ForestVillage/landscape_themes.json` 查主题的图、组件、资源和制作入口，用 `Docs/WorldGeneration/hills-landscape-themes.md` 核对当前组合。样板时间码、原片字幕、扫描件来源、独立高度图和各版恢复回执在 `Docs/Production/HillsForestPathStudy.md`。以对应版本追溯历史参数，以当前注册表和实际绑定决定写入位置。

## 构建次序

1. **定地形骨架和不能动的标高。** 在平面上标出山脊、鞍部、谷线、建筑承托点、门槛、村门、河岸和采石作业面，再画路心和坡肩。把位置、高程单位、种子与约束遮罩保存成制作输入。
2. **建立可行走的地面。** 从可用参考提取真实尺度的坡肩和地面起伏，生成整山与路床，统一 Landscape 和外围地块的共享高度。地面、碰撞、岸线及地图同源。整地、拼缝、位移、路面与陡崖做法见[高度场、道路与地表](references/terrain-and-surfaces.md)。
3. **按生态与玩法所有权布置。** 用同一最终高度和遮罩分发两主题落点。保留原始点位身份，将近草、可采伐树、局部水体和林雾交给各自已有的系统。实施细节见[生态组合、光照与运行成本](references/ecology-and-atmosphere.md)。
4. **按改动范围落盘。** 单改落叶边缘只重绘图集和受影响的材质。改了山体或中心线，重建受影响地块的渲染和碰撞、重投依附物，刷新水文、两主题共享边界及 M 键地图所读数据。保留已认可密度、旧存档和无关主题的独立修改。
5. **按用户要求交付。** 默认后台制作、保存与必要的 `FPSGAMEEditor` 构建。注明已修改的配方、已保存的包以及使用的恢复清单。用户要求复核时，选择与变化对应的固定机位、真高程采样、主客机或性能测量；分别记录落盘、运行读回和视觉结论。已有玩家采样时，先按[两机位 F6 对照方法](references/ecology-and-atmosphere.md#读取用户导出的-f6-数据)处理原始窗口。

仅做模块建筑、立面或 Shape Grammar 排布时使用[模块建筑 PCG](../ue5-pcg-building/SKILL.md)。修改全项目天气逻辑时使用[天气与昼夜](../ue5-weather-workflow/SKILL.md)。改变持久对象身份或同步协议时使用[存档与复制](../ue5-save-load-replication/SKILL.md)。

修改扫描泥路的实物尺度和车辙裁剪，见[村外道路的扫描材质](references/terrain-and-surfaces.md#村外道路的扫描材质)。迁移 Nanite、流送或核对客机树木与地面，见[迁移林图的渲染和联机预算](references/ecology-and-atmosphere.md#迁移林图的渲染和联机预算)。
