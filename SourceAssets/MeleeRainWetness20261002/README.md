# 近战雨天湿润接入 20261002

当前六种近战：苍蓝星辉双手符文剑、寒晶双手剑、高地双手剑、学徒长杖、伐木斧、矿镐。排查原装、剑的四槽改件及共享配重、长杖六槽改件、工具五档强化、金色原生符文和大旋风临时表面副本。

排查发现原天气组件只扫描 AKMViewmodel 枪械分支，并只给 HasInventoryWeapon 的枪械累积实例湿度。这六种近战的物理表面均未包含 WeaponWetness，也没有湿润映射。

已后台保存 61 个母材质的湿润层，以及 71 条持久材质/实例映射：

`/Game/Weather/MeleeWetness20261002/DA_MeleeWetMaterials.DA_MeleeWetMaterials`

- 原干燥纹理、UV、金属度、透明度、发光和符文参数保留；追加水膜、粗糙度降低、轻微颜色加深与细小水珠法线。
- 共享握柄的显式 Substrate ShadingModels 输入同时接入。
- 水晶外壳保留透明/透光及发光；受保护的内部水晶和组合视模手臂不加水珠。
- 所有原材质和槽名保留；高地裂角护手继续使用本次剑身金属适配材质，不改模型和 UV。
- WeaponWetness 默认 -1 使用世界天气 MPC；持有武器由运行时设为非负的实例湿度，复用原动态材质指针，保留照明和护手充能更新。
- 运行时纳入剑、工具、法杖和第三人称手部挂点武器分支；切换武器保留各自湿度，沿用遮雨、渐湿、120 秒干燥和量化写入机制。

`audit.json` 是用户要求排查时读取的当前资产槽与材质来源。`install_receipt.json` 记录已保存母材质、映射、摘要和备份路径；`Before/` 保留此次修改前的原资产。制作及落盘脚本为 `audit_materials.py`、`install_wetness.py`；`queue_install.ps1` 自动等待可用接入窗口，调用已有批次互斥后台流程，不关闭运行进程。

运行时源修改在 `Source/FPSGAME/WeatherViewEffectsComponent.cpp`。Game Development 构建已完成（`build-game-final.log`）。现有后台构建也已生成对应 Editor 目标文件（12:05:46）及 `UnrealEditor-FPSGAME.dll`（12:06:51），均晚于最终源修改（12:04:42）；链接输入包含本组件目标文件。当前已有编辑器于 12:07:08 启动，本任务没有启动或重启它。未做运行、视觉验收；由用户测试。
