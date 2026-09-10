# 后坐力与枪械稳定性接入

目标：让装备改造中的后坐力、枪械稳定性与实际开火共用计算结果，保留瞄具与弹道对齐以及现有配件的平衡。

## 数据和职责

- `Weapons/WeaponHandling.h/.cpp` 是统一计算入口。`gunsmith.json` 的 `base.recoil`、`base.camera_shake` 仍然兼容原存档；配件继续使用 `recoil_mult`、`shake_mult`，各倍率相乘。
- 最终指数限制在 0–400，非有限结果回退到参考值 100。后坐力越低越好。`camera_shake` 是抖动指数，越低越好，不直接冒充稳定性评分。
- 后坐力驱动控制方向的垂直/横向逐发偏移、枪身 kick 与 flip。统一参考弹道系数 0.70，旧角色默认对象中的同名值改为只读的运行结果，避免编辑器参数与面板出现两套值。
- 稳定性驱动枪身及镜头随机抖动、镜头可恢复 kick 和 trauma；回稳将整个反馈弹簧的时间按 `1 / sqrt(clamp(shake/100, .25, 4))` 缩放，保留阻尼比和峰值响应。固定后坐轨迹的恢复计时与腰射散布不受此评分控制。
- 实战仅使用已应用配件。草稿只预览数值和外观；存档提交失败不改变射击。重新应用角色数据时从基准重算，避免自动保存时倍率重复叠加。
- 单机角色拥有反馈状态，GameInstance 改造系统计算配置，物品实例仅保存配件 ID。没有新增存档字段，没有新增联网合同。

## 展示标尺 v1

- 后坐力：参考指数 100，最终值为基础指数乘配件倍率。
- 枪械稳定性：0–100 分，越高越好。非零抖动时为 `100 / (1 + .5 * shake/100 + .5 * recovery_time_scale)`；零抖动为 100。参考 M4 是 50 分。
- 首发上跳：统一轨迹第一发 `.009 rad × .70 × recoil/100`，原厂约 0.361°。
- 连射上跳/发：第 9 发起的单发上限 `.028 rad × .70 × recoil/100`，原厂约 1.123°。是控制方向的增量，不是全部视觉运动与随机晃动的总和。
- 镜头回稳90%：开镜弹簧振幅包络衰减90%的理论时间，`2*ln(10)/(15+8) * recovery_time_scale`，原厂约200ms。不是镜头精确回到开火前瞄准点，不自动替玩家压枪，也不是枪身所有振动全部结束的时间。
- UI 通过悬停说明解释标尺，改造总览与装备提示都使用同一个计算结果。右侧支持滚动，增加四行明细后共18行。

这是一版游戏标尺，不是现实枪械物理测量，也不代表命中率。当前保留镜头/瞄具驱动弹道的既有合同；本次没有改成独立的纯视觉镜头震动架构，`VisualRecoilScale` 仍为开发者武器手感调节项，不能当作玩家无影响精度的舒适度选项。

全息镜、大弹鼓正式配置没有新增后坐力或稳定性增益。测试时仅在独立进程内临时给两个既有配件设置倍率，测试结束恢复，JSON 和玩家存档不受影响。

## 复现

编译当前 UE5.8.2 FPSGAMEEditor 模块，然后运行 `Tools/UI/run_weapon_handling_acceptance.ps1 -RunId <新的标识>`。运行输出位于 `Saved/WeaponHandlingAudit/`：断言CSV、实际镜头弹簧采样CSV与运行面板截图。必须使用独立 `WeaponHandlingAudit` 存档，该检查拒绝操作普通存档。

专项覆盖：草稿/应用/撤销、保存失败、倍率叠加、武器基础指数、重复配置绑定、读档/拆除、真实反馈函数的角度与冲量、零值、不同帧率和单帧卡顿、装备提示、实际面板收益颜色。反馈数值检查直接调用实际反馈函数；不将这些检查冒充玩家输入验收。常规输入由现有 `run_gunplay_acceptance.ps1` 另外回归。

## 本次运行结果

- 编译成功：`UnrealEditor-FPSGAME-2026091043.dll`。日志 `Saved/WeaponHandling-build-final.log`。
- 1920×1080 专项运行：42 PASS / 0 FAIL，`Saved/WeaponHandlingAudit/final-1920-runtime.log`。截图 `final-1920-handling-panel.png` 为明确标注“验收样本”的临时配件倍率演示。
- 控制器输入常规射击：49 PASS / 0 FAIL，`Saved/GunplayUpgrade/handling-finite-60/assertions.log`。场景 `/Game/GameMaps/L_MilitaryTrench_FPS_Test`，固定60Hz；独立存档 `HandlingFiniteAudit_60`。覆盖开镜、连射、换弹、冲刺滑铲、近墙枪口遮挡及动画机械接触。
- 1280×720 改造工作台与滚动压力：44 PASS / 0 FAIL，`Saved/GunsmithWorkbenchAudit/handling-final-1280.log`。实际正式配件截图 `handling-final-1280-draft.png`；18行总览、未来12个配件卡片滚动、拖动旋转、全息瞄具与折叠照门均通过。
- 初次沿用旧脚本在 `DayNight_Lighting` 中运行，得到42 PASS / 7 FAIL：该场景现已启用无限备弹，旧脚本的有限备弹、干击和后续动作计数前提不成立。保留原始失败记录 `Saved/GunplayUpgrade/handling-final-60/`，没有为使测试通过而关闭正式场景无限备弹规则；转到现有有限弹药战壕场景后上述49项全部通过。
- 编译中的既有鼠标捕获API弃用警告、引擎 ToolsetRegistry 的 PythonTestRunner 启动错误与本次修改无关；各专项进程正常退出。没有手动玩家长时间试玩，也没有把固定步长检查当成FPS性能测试。
