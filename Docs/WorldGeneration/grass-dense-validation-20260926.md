# 密集高草场景运行检查（2026-09-26）

后续状态（2026-09-27）：草片宽三角问题已实施 v11 修正并完成新的运行与截图复查，见 [形态修正记录](grass-shape-fix-20260927.md)。下文保留 v10 原始失败证据，传送回程问题没有被本次草材质修正覆盖。

用户本轮明确要求检查各功能，故启用独立游戏进程、GPU 回读与运行截图。没有通过编译结果代替运行结论。

## 结论

**不能判定全部正常。** 核心草地交互的 24 项自动运行检查通过；真实画面仍存在强压平后的草片拉宽／折片，且主场景 → 草场 → 主场景的返回阶段发生地图加载失败并退出。丘陵完整往返尚未完成。

## 已完成的运行检查

环境：UE 5.8.2、D3D12 实际渲染、1280×720、独立 `-game -RenderOffscreen`，不是 NullRHI 或 Python commandlet 物理查询。使用 `-ClearwaterNoMenu` 绕过会暂停游戏的启动菜单。

| 范围 | 结果 | 证据 |
| --- | --- | --- |
| 地图／实例／实际材质 | 通过 | 两组 HISM 合计 25,494 丛，实际主材质 M_TemperateMeadow；RT A/B 引用有效 |
| 玩家落地与移动 | 通过 | 出生 Z=98.15 cm，真实 CharacterMovement 着地；独立步行超过 6.5 m |
| 单次压草与作用范围 | 通过 | GPU 当前读取侧产生非零强度，作用范围外保持清空 |
| 窗口移动 | 通过 | 草痕固定在世界位置；跨 4 m 网格移动后仍保留 |
| 同批多个事件与窗口移动 | 通过 | 同帧两个分开的 stamp 在 recenter 后均保留 |
| 冲击接口与波前参数 | 通过 | AddImpulse 的压平 RT 有效；半径 650 cm、强度 .9、波前时间正常发布 |
| 恢复计时 | 通过 | 约 6.013 秒内强度从 .8804 降到 .5332，与 18 秒线性恢复容差一致 |
| 持续新事件时旧草恢复 | 通过 | 持续向另一处写入新脚印，旧位置仍恢复到零附近 |
| 控制台总开关／API 开关 | 通过 | 关闭后清空 RT 和队列，MPC bEnabled=0；重开能恢复 |
| 低画质开关 | 通过 | FoliageQuality=0 关闭形变，恢复到 3 后没有旧草痕 |
| 真实行走踩踏 | 通过 | 清空后的真实角色行走重新产生 GPU 草痕 |
| 空中不踩草 | 通过 | 离地移动期间没有新增压平；该项隔离重力以保持空中状态，不代表完整跳跃动画验收 |
| 脚步反馈池 | 通过 | 行走期间观测到 3 个有效贴花、2 个有效扬尘；随后归零，固定 12 个贴花组件，无持续增长 |
| 脚印贴花材质域 | 通过 | 运行组件使用 Deferred Decal 材质 |
| 门的交互范围 | 通过 | 主场景和草场中，3 m 被拒绝，1.3 m 被接受 |
| 主场景 → 草场 | 通过 | 实际模拟 E 键，载入 L_GrassDeformDenseTest |
| 草场 → 主场景 | **失败** | E 键触发 Travel 后，DayNight_Lighting 加载失败，进程退出 |
| 丘陵 → 草场 → 丘陵 | 未完成 | 往返检查在主场景返回故障处终止；单独复测待完成 |

核心 24 项结果：`Saved/GrassDenseValidation20260926/functional-01/results.txt`，结尾 `COMPLETE checks=24 failed=0`。此计数是自动断言数量，**不含视觉折片验收，也不表示传送往返通过**。

首版日志中 stamp/recenter 的部分说明字段打印 `-1`：C++ 实参求值先生成说明文本，再调用同一断言的 GPU Read，导致说明字段早于回读。实际布尔断言使用 `Read() && PeakAt(...)`，先回读再判断；该说明顺序已在测试源码修正，不能把旧说明字段当作 GPU 实际强度。恢复计时字段在独立 Read 后记录，不受此问题影响。

## 问题 1：强压平出现拉宽／折片

- 原始近景证据：`Saved/GrassDenseValidation20260926/baseline/captures/grass_before_1.png` 与 `grass_after_1.png`。
- 新草场固定相机证据：`Saved/GrassDenseValidation20260926/functional-01/01_before.png` 与 `02_stamped.png`。
- 原始测试固定风相位后，空白对照的平均像素差为 .147/255；压草前后为 4.921/255，约 17.90% 像素差超过 10/255。这证明实际渲染在响应，同时截图可见明显宽三角／扇形草片。
- 因而不是“RT 写入但材质完全不动”，而是形变后的形态仍不合格。当前代码按顶点世界 XY 采样径向方向，同一草片不同顶点可能收到不同弯曲方向；这是进一步定位候选，尚未单独证明为唯一原因。

## 问题 2：回到已访问主场景时加载失败

`Saved/GrassDenseValidation20260926/portals-01/runtime.log`：

- 13:26:03 UTC：实际进入 L_GrassDeformDenseTest，门的范围断言通过。
- 13:26:04.181：`ScenePortal: Travel /Game/GameMaps/DayNight_Lighting`。
- 13:26:04.448：`Failed to load default map ... Failed to load package '/Game/GameMaps/DayNight_Lighting'`。
- `UGameEngine::HandleBrowseToDefaultMapFailure` 请求退出。进程退出码为 0，但回程检查未完成，因此不能将退出码视为通过。
- `Content/GameMaps/DayNight_Lighting.umap` 当时存在，大小 2,365,156 字节；同一进程最初也成功加载过它。尚未确认是源地图包在切换后保留了空包状态，还是准备／清理时序导致；没有据此修改引擎或传送逻辑。
- 首轮较快触发返回；补充夹具增加每张地图生成玩家后等待 8 秒，并支持单独从丘陵开始，待复测区分时序和普遍回程问题。

## 测试产物及边界

- 测试源：`Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformFunctionalAudit.cpp`，仅非 Shipping 且带审计旗标时运行。
- 入口：`Tools/GrassDeform/run_functional_audit.ps1 -Kind Functional -Label <label>`；传送用 `-Kind Portal`，可加 `-FromHills`。
- 测试存档使用 `ColdSteelProfile=GrassAudit-<label>`；传送审计下丘陵使用 `TemperateHills_GrassPortalAudit` 槽位。
- 首轮旧 GrassDeformAudit 的“步行后草痕总面积应增加”判据混入了先前大草痕的恢复，因此记录了假阴性。独立行走测试先清空再行走，已经通过。
- `-nosound` 下只确认脚步事件、粒子和贴花状态；没有宣称脚步音频听感通过。
- 火球、陨石、女巫与弹坑的 AddImpulse 调用做了源码入口核对；本轮实测公共冲击接口，没有逐个施放这些技能。
- 没有做打包版、多机、性能基准或长时间压力验收。
- 本轮没有修复草形变或传送的功能逻辑。为建立测试增加非 Shipping 审计入口与丘陵测试存档隔离；必要构建中仅拆开锻造头文件中逗号相连的静态常量声明，数值保持不变。

补充夹具源码已完成，尚未形成新的可运行 DLL：Editor 重编译先被并行开发中 `ColdSteelSkillModel.cpp` / `BowWeaponComponent.cpp` 的角色成员访问错误阻塞（`Saved/BuildEditor/grass-functional-audit-build-05.txt`）。相关声明修改后，又在 `FPSQuickCombatComponent.cpp:295 / :374` 访问受保护的 `AFPSGAMECharacter::Bow` 处失败（`Saved/elite-grille-build-editor-final-20260926.log`）。没有继续改动这些并行玩法文件。这属于后续复测的构建阻塞，不撤销此前已完成的 24 项运行结果及返回失败证据；不能宣称延时返回／丘陵往返已经运行通过。
