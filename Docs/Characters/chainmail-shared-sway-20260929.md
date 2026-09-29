# 锁子甲内外层同步运动与布料开销收敛

用户反馈：Chaos 袖口版本的内衬明显穿模，并出现卡顿。此版本取代 `ChainmailCloth20260929` 的第一人称运动实现。

## 已知原因与证据范围

上一版衣物显示 section 0（外层锁环和实体环）接入 Chaos，section 1（内衬与包边）保持普通蒙皮。外层 MaxDistance 达到 0.28 cm，原衣料厚度约 0.20 cm。活动量超过层间厚度，而且两层使用不同运动场，允许外层移动到内衬内侧。这是本次优先移除的穿插来源。

用户运行日志 `Saved/Logs/FPSGAME.log` 的 2026-09-29 03:13:54 UTC 段曾记录：

- `SK_Bow_ChainmailShirt` 的 LeaderBoneMap 越界警告。
- `SkinnedMeshSceneProxyDesc.cpp:455` 的 leader/follower 骨骼映射 ensure，调用栈经过 ClothingSystemRuntimeCommon 和 ChaosCloth。
- 本次错误堆栈回溯耗时 0.034 s。

这些是用户已有运行产生的记录，没有主动运行性能采样。单次初始化错误和 cloth 路径不能证明持续卡顿的全部原因，也不能据此给出帧率改善百分比。

## 调整

1. 显示模型回到已制作好的 V2 原生骨架模型，保留显示面数、厚度、UV、锁环材质和现有武器动作。
2. 不附加 clothing asset、模拟代理或布料碰撞体。服装组件继续普通 Leader Pose 跟随，组件 Tick 关闭，LOD 正常选择。
3. 每套双臂 presentation 只保留左右两个惯性弹簧状态。根据对应手部的位移与转动更新，6.5 Hz、阻尼比 0.85、最大偏移 0.12 cm，最多 12 个小步。
4. 顶点色 R/G 分别记录左右袖口活动权重。同一轴向位置的内衬、外层、包边共享同一函数；靠近袖口最后 1 cm 完全统一移动，向上约 4.5 cm 平滑衰减到零。掩码在 M4 母版计算一次，并按 V2 既有原生顶点顺序移植到 21 个配置，避免在不同 bind 姿态重新猜测袖口平面。
5. 三个材质槽保留原外观，使用相同的左右位移参数。材质中 `PreviousFrameSwitch` 同时接入上一帧位移，使新增 WPO 能提供对应速度信息。
6. 隐藏、OwnerNoSee、关闭强度、显隐切换、超过 0.1 s 时间步或手部大幅跳变时重置；停稳后跳过未变化的材质参数写入。

这是受限的外观惯性效果，不提供布料折叠或碰撞求解。原动画导致的身体/衣物适配问题仍需按具体姿态处理；本次不会通过增加另一套内衬模拟来解决。

## 文件与状态

- C++：`Source/FPSGAME/Characters/FPSOutfitSecondaryMotion.*`；`FPSModularOutfitComponent.cpp` 的启用标记改为 `chainmail_shared_sway_v1`。
- 作者源：`SourceAssets/ChainmailSharedSway20260929/Masks/*.json`，原显示几何继续来自 `ChainmailInterlace20260929/Authored/*.json`。
- UE 新家族：`/Game/Characters/ModularOutfit20260924/ChainmailSharedSway20260929/`。
- 制作：`Tools/ModularOutfit/build_chainmail_shared_sway.py`。
- 导入：`Tools/ModularOutfit/import_chainmail_shared_sway.py`。
- 发布：`Tools/ModularOutfit/publish_chainmail_shared_sway.py`，要求完整保存回执及常规模块构建回执后再切换。
- `fps.Outfit.ChainmailSway` 仍为 0–1，0 关闭外观惯性。
- 只修改锁子甲第一人称外观和运动，Body、装备数值和图标继续现有版本。

替换期间，配置先退回 V2 普通蒙皮（`interim.json`）；这与新运动正式发布是两个步骤。实际 UE 保存以 `Saved/*.json` 为准，常规构建以 `native-build.json` 为准，启用以 `published.json` 为准。没有这些回执时不得宣称整套已接入。

当前制作按用户规则不启动游戏、PIE 或性能测试。最终动态效果和卡顿变化由用户测试。

## 本次落盘结果

2026-09-29 已完成 21 个第一人称配置、3 个共享运动材质、每模型 3 个 LOD 的后台导入保存，装备 recipe 已切换到 `ChainmailSharedSway20260929 / chainmail_shared_sway_v1`。

常规 Editor 模块构建成功：`Saved/BuildEditor/build-20260929-113139.log`；后台导入正常退出：`Saved/chainmail-shared-sway-import-20260929.log`。此次未启动图形编辑器、游戏或额外测试。运行表现及帧耗改善未验证。
