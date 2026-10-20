# SVCH 空仓拉栓与回待机修复 R11

2026-10-18。范围为用户反馈的空仓换弹末尾瞬移、拉栓手没有接触实际拉柄，并复查相邻普通换弹。使用认可的 SVD 源动作、原生 V9 手模和 R10 左手抓匣配置。

## 原因与修复

`RifleReloadHandoff::Supports` 原先漏掉 SVCH，而 `FinishWeaponAction` 已会在结束时清除 SVCH 的动作构图偏移。这使动作期间的位置偏移一直保留到最后，再突然跳回待机。现在 SVCH 接入与同源 SVD 一致的回位窗口：空仓末尾 123/120 秒逐渐撤回位置和角度偏移，最后 0.10 秒交接到持续播放的待机。窗口位于拉栓闭合之后，不增加换弹时长，也不重定时源动画。普通换弹使用同源的 102/120 秒收势段。

SVCH 拉柄与源 SVD 拉柄的空间位置不同，原配置直接沿用源手部位置；稳定拉动阶段最近的手部表面仍距目标拉柄约 34.36 mm。R11 以实际 `SVCH_BoltCarrier` 拉柄表面为目标，对整条右臂做刚体配准，仅在空仓动作的 `clavicle_r` 增加位置、角度差值。源帧 260–286 渐入，286–350 保持，350–400 退出。右腕、手指、臂内关节局部姿态及拉栓机械轨迹保留，R10 左手抓匣配置保留。

`WeaponReloadStages` 同时补齐 SVCH 分支，使用该枪的插匣、开始拉栓和拉栓闭合时刻，避免落入默认步枪的阶段时钟。

逐帧检查进一步发现大尺寸拉柄在回弹的 345–347 帧会擦入原手型。保持手腕、手指局部姿态不变，增加 344–356 帧的短暂整手让位，峰值约 10.59 mm，随后平滑归回原收手轨迹；接触前 303–310 帧另有约 0.15 mm 的贴面修正。修正沿用实际源时钟，仅影响同一右锁骨轨道。

## 资产与证据

- 保存目标仍是 `/Game/Weapons/SVCH/Refined20261018/R5/DA_SVCH_BaseGrip`；历史目录名不代表配置版本。
- [可编辑动作源](../../SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/SVCH_R11_ReloadGrip_Editable.blend)
- [接触与源姿态检查](../../SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/charge_validation.json)
- [安装回执](../../SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/install_receipt.json)
- [逐帧运行衔接记录](../../SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/runtime_review.json)
- [普通换弹至待机预览](../../SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/reload_normal_handoff.gif)
- [空仓换弹至待机预览](../../SourceAssets/SVCHRefinement20261018/R11ChargeHandoff/reload_empty_handoff.gif)

当前源动画在 R10 交付之后已有共享更新，本轮读取实际已保存姿态作为 `CurrentSource` 基线，不恢复旧源文件。保存时核对 12 条当前源动画的散列，V9 网格、权重和认可源动作不由本轮修改。另 11 个动作的握持配置与 R10 完全一致，空仓动作除右锁骨轨道外一致。

几何检查覆盖 516 个源姿态；稳定拉动阶段检查实际拉柄距离、闭合包络交叠和手栓相对漂移。运行检查使用独立存档、原厂弹匣、离屏游戏，逐 tick 记录普通／空仓换弹末尾的相机相对组件和枪根变换。最终状态与数值以本轮 `validation_receipt.json` 为准；音频、联机及全配件组合不属于本轮范围。

## 最终复查

后台 `FPSGAMEEditor Win64 Development` 构建成功，最终握持资产已保存。独立运行正常结束，两种换弹均回到 10 发，全部有效动作画面均显示原生 V9。

| 换弹结束到待机的单帧变化 | 普通换弹 | 空仓换弹 |
| --- | --- | --- |
| 枪根位移 | 0.0579 mm | 0.0064 mm |
| 枪根旋转 | 0.000850° | 0.000306° |
| 组件位移 | 0.0591 mm | 0.0067 mm |
| 逐 tick 记录 | 360 帧 | 480 帧 |

空仓拉动保持段取得 17 个实际运行样本，手相对拉柄最大位置漂移 0.0125 mm。源姿态的接近、拉动和松手阶段共检查 141 帧，闭合拉柄包络未检出穿插；拉动和松手关键帧的机匣检查也未检出手部嵌入。画面复查包含左手抓匣、右手抓柄、松手回握以及换弹结束后的待机，未再看到本次反馈的拉栓落空和末尾突跳。

整理源文件时发现 V9 包的散列与 R9 归档不同。重新从当前已保存资产读取后，确认仅有 12 个顶点的权重条目顺序不同，所有实际骨骼权重、顶点、三角面和参考变换完全一致。该包保存时间早于本轮源采集；本轮没有修改 V9 资产。可编辑源已同步当前包的读取结果和散列，见 `native_v9_geometry_comparison.json`。

复现顺序：`author_charge.py` → `author_release_clearance.py` → `validate_charge.py` → `install_profile.py`；`export_editable.py` 输出两种换弹的武器和 V9 action。`run_runtime.ps1`、`review_runtime.py` 和 `finalize_review.py` 保存运行画面与最终回执。
