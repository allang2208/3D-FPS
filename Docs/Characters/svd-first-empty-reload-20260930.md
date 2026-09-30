# SVD 首次空仓换弹色块：运行时排查记录

状态：**尚未复现用户报告的上方大色块，未确认根因，本轮没有发布新的姿态、网格或材质修复。** 不能把下面的未复现记录作为用户问题已解决的证据。此前锁子甲公共近镜头保护及肘部修复继续保留。

用户明确授权仅启动 UE 排查这次 SVD 问题。本轮使用独立 `ColdSteel_SVDFirstReload*` 审计存档、实际 DayNight 地图与正常武器动作入口；960×540、D3D12、固定 60 Hz、水平相机。没有修改用户正常存档，没有测试其他枪械。捕获进程均已结束。

## 已取得的有效记录

输出根目录：`Saved/SVDFirstReload/`。每帧 JSON 记录源姿态、相机、当前动作、时间、衣袖/裸臂/世界模型路径、材质及可见状态；换弹开头 1.6 秒逐帧截图，后半段抽帧。

| 独立运行 | 条件 | 结果及范围 |
| --- | --- | --- |
| `ColdSteel_SVDFirstReloadBefore03` | 默认 SVD，初始空枪 | 首次换弹 frame 102 开始；衣袖直到 frame 238 才加载，未覆盖用户要求的首次带衣袖开头；第二次弹量设置无效，不能算双次对照 |
| `ColdSteel_SVDFirstReloadBefore04` | 衣袖到位后，斜握把＋LPVO，连续两次空仓换弹 | 开始 frame 0 / 376，751 帧；未见所述上方色块；首次衣袖显示有短暂默认棋盘格过渡 |
| `ColdSteel_SVDFirstReloadBefore05` | 上述配置，从 ADS 退出进入首次空仓换弹 | 两次换弹完成；未见上方色块；衣袖首次显示有左下方默认材质/时域过渡，不等同于用户所述上方异常 |
| `ColdSteel_SVDFirstReloadBefore06` | 先驻留 SVD 衣袖资源，以空枪装备，装备动作结束直接空仓换弹 | 开始 frame 102 / 477，852 帧；首次开头 96 帧完整查看，未见上方色块；资源预驻留属于诊断条件，不能作为生产修复 |

另已准备 `-Realtime` 条件，用真实帧间隔检查首次加载卡顿；07 启动前发现已有独立 UE 资源缓存 commandlet，启动器保留现场并拒绝另起进程，**07 没有执行**。因此本轮固定步长记录不能排除真实首次加载卡顿相关问题。没有关闭他人的 commandlet。

04–06 的配件来自之前实际日志：`canted_foregrip / lpvo_1_6x / ext_mag / qr_performance / titanium_brake / laser`。加载的确实是 `A_SVD_canted_reload_empty`。当前衣袖为 `ChainmailCameraClearance20260929/SVD/SK_SVD_Chainmail`，三个 CameraFade MID 的启用参数为 1，参考肩点对应 SVD 绑定。没有用默认 PSO/默认换弹代替改装枪条件。

06 的逐帧拼图与记录：`first-opening-0.png`、`first-opening-1.png`、`first-opening-2.png`、`analysis.json`。01/02 没有有效动作记录，不计为复现；03 的不完整对照明确保留为失败采集。旧启动器误把进程正常退出当作采集完成，现已要求日志明确含 `capture_complete=1`，后续采集另写 `capture.json`。

## 不能据此成立的结论

- 包已加载不保证当帧就是正式着色效果；已观察到首次衣袖显示的材质过渡，但未证明它造成上方色块。
- 本机 UE 5.8 本轮的 `IsGameThreadShaderMapComplete()` 对衣袖、皮肤和枪体都持续为 false，已有 ShaderMap 的材质仍正常显示。不能用这个布尔量单独阻止衣袖显示，也不能据此认定锁子甲着色器损坏。
- “第一遍”不能只按冷热加载解释；已分别排查默认空枪、待机换弹、ADS 退出、空枪装备衔接，但还缺少用户异常那一帧的图像与准确进入动作路径。
- 尚未捕获异常，故未继续挪肩、转肘、缩衣袖、隐藏整臂或扩大近镜头裁切距离。

## 后续入口

采集源码：`Source/FPSGAME/Weapons/SVDFirstReloadCapture.cpp`；只有显式 `-SVDFirstReloadAudit` 且独立审计存档时执行。正常运行不采集、不断弹、不改装备。

启动器：`Tools/ModularOutfit/run_svd_first_reload_capture.ps1 -Label SVDFirstReload<新名称>`；`-FromADS` 和 `-ColdEquip` 分别用于上述条件。它沿用桥的批次互斥，已有 UE 实例时不另开，限时只结束自己创建的捕获进程。该入口是诊断工具，不是修复，也不构成后续测试授权。

最终采集器源码已纳入当前基础 DLL；后台构建返回 `Target is up to date` / `Result: Succeeded`，日志为 `Saved/BuildEditor/svd-first-reload-recorder-final-20260930.log`。最终增加的采集回执/LOD 字段没有再运行；前述运行证据对应已注明的版本和条件，构建结果不是修复验收。

下一步需要用户确认首次换弹前是否 ADS，并提供上方色块的短录屏或截图，以对齐部位、触发前动作和实际配置。若有可复现的当前游戏现场，优先在该现场捕获，勿再把未复现作为已修复。
