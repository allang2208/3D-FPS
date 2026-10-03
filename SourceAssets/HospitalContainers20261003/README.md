# 医院线路搜寻容器 · 2026-10-03

本批新增六类原创精确建模容器，共十二个独立模型部件：医疗推车抽屉、病人物品箱、壁挂急救柜、器械消毒盒、标本运输箱和排水检修工具箱。实体柜壁、内部托盘/隔板、把手、锁扣和真正的铰链轴均随源文件保存。打开时移动抽屉、柜门或盒盖。

复用 `AColdSteelSceneContainer` 的搜寻交互、视线范围内的绿色/黄色轮廓和原宝箱面板；打开后保持打开。此次不设计奖励池。

## 已落盘内容

- 制作源：`Authored/HospitalContainers_Source.blend`、十二个 FBX、原创中英标签 PNG；资产许可为本项目原创几何/标签，钢、橡胶与玻璃沿用已入库共享材质。
- UE 资产：`/Game/Dungeons/HospitalContainers20261003`。十个不透明部件使用 Nanite；含透明玻璃的急救柜门和标本箱主体保留常规网格。
- 正式地牢：`/Game/GameMaps/L_Dungeon_Randomized` 的 Drainage、AbandonedIsolationWard、AbandonedAnatomyTheatre 模块规则和硬引用。
- 医院测试图：`/Game/GameMaps/Design/L_Hospital_Theme_Subject`，种子 `20261003`。车站测试图继续保留，本批不修改。
- C++：WardBedScatter 根据真正生成的直立病床寻找床旁空位，使用同一占位表、门口禁放区域及盖子打开范围。与整体房间生命周期一同销毁，没有额外逐帧生成。
- Editor 和 Game 目标已完成必要编译；导入和地图保存使用后台 commandlet、共用批次互斥，不启动编辑器界面。

## 摆放范围

| 区域 | 容器 | 每局目标数 |
| --- | --- | --- |
| 排水区 | 检修工具箱 | 2 |
| 隔离病房 | 五间病房各一辆医疗推车、急救柜 1、病人物品箱 2–3 | 8–9 |
| 解剖剧场 | 医疗推车 1、器械消毒盒 1–2、标本箱 1、上层看台容器 2–3 | 5–7 |

病人物品箱每个房间最多一个；目标数量受实际床位、可用空间影响，阻塞时跳过而非强行放置。医疗推车的五个备选位置在病床生成前预留抽屉活动空间，旧装饰推车不重复生成。准备台上的器械盒按台面高度摆放。

第二次用户反馈后，测试图已重新安放十四个固定种子的容器实例，上层看台按实际 +216 cm 地板高度贴近弧形墙设置；额外床旁箱仍在进入游戏后尝试生成。正式地牢根据每局种子选择候选位置。原图八个实例的引用、尺寸和可见标记在用户指定的排查中正常，未将该读取结果称为游戏显示验收。

本次抽水泵、洗手台贴墙接口及杂物删除由 `SourceAssets/HospitalPolish20261003` 保存；其源模型、安装回执与医院描述变更为当前依赖。

`Config/layout.json` 是容器预设位置源；`Scripts/catalog_rules.py` 对最新描述只合并本批医院字段，保留其他模块修改。医院测试图重建源、隔离病房重建源与剧场安装源也保留同一规则。

## 制作入口

1. Blender 后台执行 `Scripts/author_containers.py`。
2. Python 执行 `Scripts/prepare_layout.py`。
3. 必要时执行 `Scripts/build_native.ps1`。
4. `Scripts/install_background.ps1 -Phase assets` 实际导入、构建并保存资产。
5. `Scripts/install_background.ps1 -Phase scenes` 保存正式图、医院测试图及 scoped 作者配置。

实际结果写入 `Receipts/native-build.json`、`assets.json` 和 `install.json`。修改模型源后需按资产归属处理重新导入；脚本不会覆盖来源散列不同的既有模型。

## 用户测试入口

```text
open /Game/GameMaps/Design/L_Hospital_Theme_Subject
```

返回地图：

```text
open /Game/GameMaps/DayNight_Lighting
```

按用户约定，本批没有运行测试、PIE、游戏、截图、渲染或验收；交由用户自行试玩。
