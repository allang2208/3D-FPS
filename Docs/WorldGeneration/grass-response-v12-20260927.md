# 草地响应 v12 制作记录

后续：用户明确要求测试后，已完成 34 项运行检查及实机 GIF；功能断言通过、视觉仍需改善，见 [运行检查记录](grass-response-v12-validation-20260927.md)。下文“本轮未测试”指最初制作轮次。

用户已批准 [效果提升计划](grass-response-improvement-plan-20260927.md)，本次落实 P1/P2。保留现有高草、密度、地图和传送门；P3 素材／阴影精修留待用户体验反馈。

## 参数与表现设计

配置入口：`Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformSettings.h/.cpp`。UObject CDO 为运行时和 Python 资产作者共同读取的配置源，可在 `DefaultGame.ini` 的 `[/Script/FPSGAME.GrassDeformSettings]` 节覆盖，下一次运行生效。

| 参数 | 默认值 | 用途 |
|---|---:|---|
| BodyRadiusCm | 80 cm | 同时至少为角色胶囊半径 × 1.8 |
| CoreFraction | .65 | 默认直径 1.6 m，强度核心宽 1.04 m |
| BodyStrength | .95 | 不再让慢走／蹲走因低速度丢失倒伏 |
| BendAngleDegrees | 78° | 身体核心旋转约 74.1°；竖直草理想高度约 27%，不是实机测量 |
| PressSeconds | .15 s | 身体前缘沿行进速度换算过渡距离，初次落地也平滑进入 |
| HoldSeconds | 2.5 s | 从各位置最后一次接触开始保持 |
| RecoverSeconds | 3.5 s | smoothstep 恢复，两端缓、中段抬起 |
| FlatWindScale | .03 | 低伏时约 3% 风，后半程逐渐接回 |
| ForwardBias | .85 | 行走／脚印主要朝行进方向，保留少量侧向拨开 |
| FootstepRadiusCm / Strength / CoreFraction | 26 / .85 / .35 | 脚底局部压痕；身体为宽通道 |

爆炸仍为径向压力＋最近一次 MPC 波前，保留火球／陨石／女巫／弹坑各自半径、强度和波速。首版共用 2.5＋3.5 秒恢复；没有新增持久损伤或每草类型独立计时。旧 `r.GrassDeform.FadeHz` 保留兼容注册，不再控制恢复。

## 实现契约

- `RT_GrassDeformA/B` 的 R 是保留的压力峰值，GB 是 `.5 + .5 × R × 方向`，不能把原始 R 当成当前倒伏量。
- 新增 `RT_GrassContactTimeA/B`，1024² R32F，R 为最后接触的游戏时间。时间纹理使用最近点采样，避免边缘与空白的时间混合。形变仍使用原过滤方式。
- 每次 stamp 和 recenter 分别输出形变／时间，**两次绘制完成后只交换一次 ReadIndex**。两张输出读取相同旧状态；整数像素窗口平移规则保留。
- 每帧材质按 `age = WorldTime - lastContact` 计算保持和恢复。重踩前先计算旧痕迹当前强度，再合并新压力，防止陈旧峰值被复活。原 Fade 材质成为历史资产，运行时不加载、不绘制。
- 人体接触使用 MPC 两个向量：位置／半径／强度，以及方向／压下距离。着地时每帧读取一个本地角色的状态，历史 stamp 限为 10 Hz，站立也刷新；没有逐草循环、实例变换、额外 trace 或运行时 GPU 回读。
- 离地释放接触层；单次位移超过 300 cm 不连出传送轨迹。恢复计时误差受 10 Hz 接触刷新限制，约一个刷新间隔；窗口外痕迹不永久保存。
- 关开关／低画质／世界退出统一清空两组 RT、接触、队列和波前。RT 总数据约 24 MiB，不含引擎额外开销；每接触事件或 recenter 为两次绘制，恢复本身无周期绘制。这是设计预算，未测性能。
- v11 的 PivotPainter UV1 草根、整片旋转、统一角度限幅和组合风保持。主材质仍为 `MA_Grass` 与 `M_TemperateMeadow`。
- `mf-v12` / `pass-v6` 为新版本标识，更新现有命名节点并保留 FunctionOutput GUID。生产脚本备份改动资产后进行实际 SM6 编译与保存。
- 既有 FunctionalAudit 的恢复断言同步为读取 R32F 时间后计算当前响应；本轮没有运行诊断。旧 v11 24 项结果不代表 v12 的观感或功能已通过。

## 交付状态

源码、当前 Editor DLL 和实际资产均已落盘：

- 普通后台构建：`Saved/BuildEditor/build-20260927-110637.log`，Result: Succeeded / Target is up to date。共享构建已编入本次源码，此次构建确认无需追加编译；没有启动游戏。
- 资产回执：`SourceAssets/GrassDeform20260927/authoring-20260927-110813.json`；保存 12 个资产，四个绘制材质及两个真实主材质的最终编译错误列表均为空。版本 mf-v12 / pass-v6。
- 资产修改前备份：`SourceAssets/GrassDeform20260927/BeforeV12-20260927-110813/`。
- 制作日志：`Saved/BuildEditor/grass-response-v12-assets-02.txt`。首次制作因配置对象没有 Python snake_case 属性别名退出，未开始改资产；已改为读取原生反射属性名。后续制作成功。重连节点途中产生的缺失输入警告不等于最终编译结果，最终完整图编译记录见回执。
- SKILL 参考 `skills/ue5-world-interaction/references/grass-gpu-deform-rt-window.md` 已更新为 v12 契约。

本轮未启动编辑器窗口、游戏、PIE，未做截图或自测。用户从原高草测试场自行体验“经过后低伏保持、再明显抬起”，反馈后再调表现。源码构建和材质编译成功不代表实际观感已验收。
