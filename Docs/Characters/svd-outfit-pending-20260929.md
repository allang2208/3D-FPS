# 待办：SVD 锁子甲右臂进入镜头

状态：**用户于 2026-09-29 要求暂停，未修复完成；下个对话继续。**

## 当前用户反馈

SVD 装备锁子甲时，ADS 与换弹仍有疑似右臂的错位模型进入镜头。裸臂状态尚未确认。上一轮删除肩部封面后用户仍复现，不能报告已修复。

## 本机现状与证据

- 工程及独立 Git 根：`D:/FPS3D/FPSGAME`。默认后台工作，不自动启动/重启 UE；现有实例调用桥 `Tools/AssetPipeline/mcp_call_codex.ps1`，禁止跨对话协调消息。
- 活动 SVD：`/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock`。
- 当前锁子甲：`/Game/Characters/ModularOutfit20260924/SVDShoulderOpening20260929/SK_SVD_chainmail_shirt`。配置仍指向这套，未接入本轮候选。
- 本轮曾读取 PIE：衣袖确实使用上述修正资产并跟随 AKMViewmodel，源手臂材质槽 0/1 已隐藏；裸臂覆盖槽隐藏，腕部 underlap 保留。读取时源和衣袖均为 LOD0。
- 锁子甲 LOD0 最长静态边约 3.60 cm；旧 LOD2 静态约 14.45 cm、离线换弹约 16.46 cm、ADS/idle 合计约 15.74 cm。低 LOD 有独立缺陷，但不是当前 LOD0 异常的已证实根因。最大异常边属于左臂，不能直接解释用户报告的右臂。
- 新候选 `/Game/Characters/ModularOutfit20260924/SVDLODRepairCandidate20260929/SK_SVD_Chainmail` 已保存，三档静态最长边约 3.60/5.89/5.89 cm；只修减面保护，未发布、未进行异常帧对照。
- 右肩衣袖与裸臂的最近顶点距离最高约 6.7 cm，含粗采样误差；相机侵入或绑定问题尚未确认，不据此盲目缩衣服。
- `live-ads.png` 实际是退出 ADS 后的持枪图，`live-reload.png` 也没有确认异常帧。不能用文件名作为 ADS/换弹验收证据。
- 两分钟临时采集器暂停时已明确注销；`pause-cleanup.json` 回执为 unregistered=true，ads=0/reload=0。没有留下自动采集。未对游戏实例替换候选、修改输入或保存装备。

## 下一对话待办

- [ ] 读取本文件及 `skills/ue5-fps-arms-animation/references/garment-quality-pipeline.md`，确认实际配置与实例；不要把本候选当活动资源。
- [ ] 在用户已运行的游戏中捕获实际出错 ADS 和换弹帧；同帧保存 is_aiming/is_reloading、瞄具/握把、网格路径、LOD、骨骼和相机变换。不要因切回聊天丢失 ADS。
- [ ] 按组件定位究竟是衣袖、裸臂 underlap、手套还是源网格；可逆隔离须恢复原状态。
- [ ] 对比裸臂；检查当前改装瞄具取景前移、运行时姿态及 LeaderPose。此前日志含 LPVO 与 canted_foregrip，不能只检查默认 PSO/默认换弹。
- [ ] 根因确认后修正；保留手腕搭接、内衬/袖口、手部接触与其他枪型已有修复。不要用仅降低厚度、隐藏整条手臂或换低 LOD 参数代替定位。
- [ ] 完成针对性画面对照后再决定是否发布候选；依照衣物管线记录结构、动作、层间和运行画面各自状态。

## 保留位置与历史范围

`SourceAssets/SVDRuntimeDiagnosis20260929/` 保留脚本、实际快照、候选 source/LOD0/1/2、图片、日志与回执；这些含授权资产导出及运行数据，留本机不公开。

前序成果包括手腕 underlap、内衬收边、针织长袖/炭灰短袖、201 左腕、短袖攀爬及各枪锁子甲权重、SVD 肩面删除、衣物候选关卡。对应文档在 Docs/Characters；这不表示全部实机问题已解决。母版 `GarmentFoundation20260929` 仍是结构基准，NativeProbe 与 SVD 新候选保持未发布。旧失败二进制若仍是对比/恢复依赖不按日期盲目移动。

归档清单：`Docs/Publication/OutfitPause20260929/archive-manifest.json`。仅本轮明确失败或被替代的脚本/重复输出移入 `trash/svd-outfit-pause-20260929/`，保留源码输入、活动资产和暂停证据。
