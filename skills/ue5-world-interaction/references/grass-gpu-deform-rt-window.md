# FPSGAME GPU 草交互：RT 窗口压平（grass-deform，2026-09-26）

状态：M1–M4 代码、资产、构建全部收敛，**实机仍无可见形变，未解决**（用户暂停）。待办与诊断顺序见 `Docs/Backlog.md` 的 G1；契约冻结与排障全记录见 `Docs/WorldGeneration/grass-interaction-gpu-20260925.md` §10.5（v2）与 §10.6（v3 修正）。

## 架构一句话
一对以玩家为中心的**持久 RGBA16F 渲染目标资产**（`RT_GrassDeformA/B`，1024²，48 m 窗口，4 m 网格吸附）承载"草交互掩码"；C++ WorldSubsystem（`UGrassDeformSubsystem`）做 ping-pong `DrawMaterialToRenderTarget`（stamp/fade/recenter 三个 pass 材质）并经 `MPC_GrassDeform` 发布窗口契约；全部草材质经 `MF_GrassDeform` 采样，输出加性混入 MA_Grass 的 WPO 链（风之后）。通道语义：R=压平 0..1，GB=弯折方向编码，A=impulse 时间戳（波前环数学用）。10 Hz 无痕踩踏（纯投影、无 trace）+ 事件制爆炸 impulse（Fireball/Meteor/Witch/Crater 各一行 `AddImpulse`，数值全在 `GrassDeformTuning.h`）。

## 三条硬教训（v1/v2 实机"无任何反应"的根因，全部实证）
1. **MPC 装不了纹理，MID 到不了渲染组件。** UE 5.8 `UMaterialParameterCollection` 只有标量/矢量（引擎头文件实证，无 SetTextureParameterValue）；"子系统建 MA_Grass 的 MID 绑 RT"也不通——草实际以 MI 子材质（`grass_0X_YY_Mat`）渲染，子系统 MID 从未被赋给任何渲染组件。可行模式：**RT 做成持久资产，作为 MF 里两个 `TextureSampleParameter2D`（`GrassDeformRTA/B`）的默认值**（默认值沿材质链被所有 MI 继承，零运行时绑定），MPC 标量 `ReadIsB` 在着色器里 uniform 分支选读侧。这是"全局运行时纹理下发到所有实例"的通用解法。
2. **FunctionInput 未接线 = 静默取 preview 默认值（0），不报错。** MA_Grass 的 MF 调用节点从未接 `WorldPos/UpwardFactor/HeightMask` → HeightMask=0 把 WPO 输出恒置零，与断点 1 叠加成"完全无反应"。且事后无法脚本修复：`UMaterial.Expressions` 对 Python 是 protected（拒读，无法枚举调用节点）。终版（mf-v4）：三个输入全部在 **MF 内部自供**（WorldPosition 节点、`saturate(VertexNormalWS.z)`、TexCoord0.V + 标量参数 `GrassDeformMaskFlip` 应对 UV 高度掩码方向翻转），调用节点只取 WPO 输出、永不需接线。**设计材质函数时默认调用方不会给你接输入。**
3. **开关路径要保活 MID。** 旧 `SetEnabled(false)` 把 pass MID 一并置空且无人重建，一次关/开循环后系统永久哑火。现在 Release 只解绑 RT 指针；重绑定时 `ClearRenderTarget2D` 清空两张 RT（禁用/重载不残留旧掩码）。

## 文件地图
- C++：`Source/FPSGAME/WorldGeneration/GrassDeform/`（GrassDeformSubsystem.h/.cpp、GrassDeformTuning.h 全部调参常量、GrassFootstepFeedbackComponent.h/.cpp）。
- M2 爆炸钩子：`Skills/FPSFireballProjectile.cpp`、`Skills/FPSMeteorStrike.cpp`（只挂 bExplosion 分支，燃场 tick 不重复盖章）、`Monsters/WitchProjectile.cpp`（陡坡拒绝前盖一次）、`WorldGeneration/TerrainDestruction.cpp`（与弹坑同心）。
- M3 脚步反馈：AutoFootstep 插件 `FAutoFootstepPlayed` 静态多播委托 + 组件订阅（Niagara puff 有界池 + 12 个 decal 拖尾池、逐 decal MID 淡出）。**`Plugins/` 不入 git**，委托改动仅存本机。
- 资产脚本：`Tools/GrassDeform/setup_assets_m1.py`（MPC/MF/3 pass/2 RT + MA_Grass 自动补丁；幂等；版本标签 `mf-v4`/`pass-v2`/`rt-v1` 走 asset metadata，重跑自动重建旧版）、`setup_assets_m3.py`（NS/贴花材质/DA）。编辑器被占用时走桥 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript ...`；工程空闲时 `run_asset_setup_m*.ps1` headless。
- **`Content/*` 不入 git**：全部 10 个 uasset（MPC、MF、3 pass、2 RT、NS、decal 材质、DA）由上述脚本随时重建。

## 调试入口
控制台：`GrassDeform.Status`（RT 绑定/MPC 发布/质量门）、`GrassDeform.DumpRT`（导出掩码 PNG）、`GrassDeform.Stamp` / `GrassDeform.Impulse`（手动盖章）。cvar：`r.GrassDeform` 总开关、`r.GrassDeform.FadeHz`；`r.GrassDeform.RTSize` 已退役（尺寸由 RT 资产定义）。`sg.FoliageQuality 0` 强制关。用户测试模板：`Docs/Performance/grass-deform-test-template-20260926.md`。

## 未决嫌疑（G1 诊断顺序）
先跑 `GrassDeform.Status` + 走几步 + `DumpRT`：**掩码为空** → C++ 侧（pass DrawMaterial、窗口吸附、traceless 投影、MPC Center 是否跟随）；**掩码有脚印但草不动** → 材质侧（MA_Grass 调用节点是否仍指向重建后的 mf-v4、草 MI 是否覆盖 WPO/相关参数、`GrassDeformMaskFlip` 方向、**Nanite foliage 的 WPO 路径**——工程 `r.Nanite.Foliage=1`，需专项确认 Nanite 网格是否评估该材质的 WPO，以及 Substrate/MDF 管线是否吞掉偏移）。

## 性能形态（设计值，实机未验证）
常驻成本 = 草材质每顶点 1 次 RT 采样 + 十余条 ALU；子系统 10 Hz 踩踏投影（无 trace）、变化检测后才发布 MPC、fade 按 `FadeHz` 分帧；爆炸为一次性 impulse。RT 显存 2×1024²×RGBA16F ≈ 16 MB。已知边界：窗口 ±24 m，远距爆炸不留草痕（§10.5 v2 接受）；全局单一 WaveOrigin，同时刻多波前环不共存。
