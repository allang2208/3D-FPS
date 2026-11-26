# 丘陵村防与守备机械 · 2026-11-26

本批收录高城门、高墙、登墙石阶、塔楼、村庄施工视角、修女科技链、守备机械、机械工坊与工匠升级面板。夜袭传送门沿用原系统。弩炮与投石机支持自动攻击和玩家接管。热油锅沿用服务器判定及客户端本地火焰表现。

## 当前交付

- 热油由服务器轮询地形，每个世界每帧最多 384 次地形探测，每轮每片最多 32 次。湿面三角形包围盒覆盖坡面。晚加入接收当前湿区；支撑物失效后撤销失去支撑的部分。
- 单个客户端世界的油火上限为每秒 300 个粒子。青铜火把的低火沿湿带发射，高火集中在较厚的油洼。预算是发射上限，GPU 帧耗待实测。
- 弩炮接管继承机架当前朝向。角色控制权落到本地时补建第一人称锅。投石机冲击环的地面方向绑定和裁剪盒已调整。

## 源码、依赖和恢复

[实现与制作脚本](Implementation/files.json) 按正式工程相对路径列出。公开主线缺少完整的丘陵城防宿主，独立 C++ 实现保存在 `Implementation/Source`，恢复时按清单的 `target` 接回工程。共享角色、控制器、建筑事务、存档及 HUD 的修改按[阶段差异](Integration/deltas.json)和[现行接点](Integration/current-consumers.json)合并。阶段补丁与 `Current` 差异可能重叠，后者是相对指定基线的选择性差异。恢复完整私有宿主时从 `CurrentHostText.zip` 按路径提取，并比对[宿主指纹](Recovery/current-host.json)。夜袭当前配置和包清单位于 [Configuration](Configuration)。

[正式包](Recovery/current-packages.json)、[退役包](Recovery/retired-packages.json)及[私有恢复归档](Recovery/archives.json)按 SHA-256 核对。NAS 的 `VillageDefenseRecovery.zip` 用 `paths.json` 将物理根类别和相对路径映射到 `blobs/<sha256>`。Fab 模型、角色与贴图、电影参考、原始下载、UE 包和编辑器模块留在获许可的本地制作环境。[器械来源和许可](../../../Content/ColdSteelData/Licenses/VillageSiegeEngines.txt)

## 待办与整理

正式工程最后一轮 `FPSGAMEEditor Win64 Development` 构建成功。旧版村建的 21 项真实 UDP 检查与新版热油的验收分开记录。待补双端坡面泼油、拆台重连、双人购买同级升级、操作中断线，以及单片／四片油同屏的 P95 和 GPU 耗时。[项目待办](../../Backlog.md)

[整理统计](cleanup-summary.json)涵盖隔离宿主、版本副本、一次性检查产物和退役资源。逐文件去向、哈希和挂载定义保存在本机 `ArtProduction/StorageLayout/VillageDefenseCloseout-20261126`。已选定的三视图、可编辑母版、正式材质与有用的结构化结果继续作为制作输入和证据。
