# 雷枪：换用悬钟射线配方（交叉 ribbon + 汇聚蓄力）

针对 ThunderFlux 管体方案始终"线条感强、显廉价"的反馈，按用户指示整体换用悬钟 M-09 凝视射线的表现配方：蓄力期内卷粒子 + 汇聚丝束 + 虹膜光斑，发射段用同款交叉 ribbon 光柱加粗并改雷电蓝白配色。伤害、贯穿、感电、修炼、散射、联机契约不变。

## 资产（/Game/Skills/ElectricMagic/LanceRay）

由 `Tools/Skills/author_thunder_lance_ray.py` 生成（快照删除式重建，`LanceRayProduction=ThunderLanceRayV1` 元数据守卫），源 HLSL 在 `SourceAssets/ThunderLanceRay20261005/Authoring/`：

- `M_ThunderLanceBeam`（LanceBeam.hlsl）：M09 GazeBeam 同款——高斯软带 + 内部流动纹理 + 两端收束；改电蓝 `(.07,.22,.62)→(.38,.72,1)` 渐变 + 白热芯脊 `exp(-14across²)`；保留 FirePower→0 时的"发散预警"剖面用于消散期（束越散越淡，不是直接熄灭）。输入契约不变：`UV/Strength/Clock/FirePower/Exposure`。
- `M_ThunderLanceFilament`（LanceFilament.hlsl）：丝束 ribbon 材质——**用户确认环绕线条换成真实闪电后已不接入**（资产留盘可复用）。
- `M_ThunderLanceIris`（LanceIris.hlsl）：虹膜光斑，深蓝边缘→亮青中心，`InstanceAlpha` 兜底 1。
- `SM_ThunderLanceRibbon` / `SM_ThunderLanceIris`：直接导入 M09 GazeV08 的两份 FBX 几何（三片 60° 交叉 ribbon，±50cm 长 ±1cm 半宽；1cm 凸面盘），provenance 已记。
- `NS_ThunderLanceGather` + `M_ThunderLanceGatherSpeck/Streak`：克隆 `NS_M09_EyeGather_V10`（M09 眼部聚能粒子，源自百目熔渣收敛栈），三发射器（火花/弧丝/微尘），`User.Charge` 驱动塌缩；改电蓝 `float4(.30+.16s,.58+.20s,1.,α)`、聚能半径 42/34/27→62/48/38cm。

## 发射柱（AFPSLightningArc::InitializeColumn）

签名换为 `(Ribbon, IrisMesh, BeamMat, IrisMat, Start, End, Spell, ChargeRatio, WidthScale)`，原 4 层管全部替换：

- `RayBeamA/B`：两个 ribbon 组件，相对转 30°（6 片平面、任意视角可读体积），半宽 115cm 与 ×.72，充能比驱动 `lerp(.55,1)`。
- `RayIrisTail/Head`：首尾虹膜盘（枪口光斑 + 末端矛头辉光）。
- **环绕线条按用户要求换成真实闪电**：`FireLanceBody` 在主束 SpawnArc 后追加 4 条 `InitializeArc` 电弧（Jitter .042 → 振幅≈束半径、Segments 26 密集折角、Duration=Hold+.1、Fade≥.5），与束同寿命并随复制态同步到远端。ISM 丝束方案已移除。
- Tick 参数语义改 M09 契约：`Strength`=Alpha（ramp-in + `pow(1-T,1.7)` 余晖）、`Clock`=Age、`FirePower`=快攻缓收包络；消散期 FirePower→0 自动切发散剖面。层错峰：B 束 .06、虹膜 .12、丝束 .45 余辉。
- 末端灯、侧弧、爆闪、残余弧链路不变；M25 妖法同签名复用（WidthScale=.32）。

## 蓄力期（FPSElectricMagicComponent）

`AtContact` 在原有 `ChargeFX`(NS_ThunderCharge) 和魔法阵之外新增：`GatherFX`（NS_ThunderLanceGather，朝向=视线，规模 1.6）、`ChargeIris`（虹膜盘贴在发射点，半径 9+16×Charge）。**汇聚线条按用户要求换成真实闪电**：充能期间每 ~130ms 从 ~45-80cm 壳面向发射点 SpawnArc 一条短命电弧（.10/.16s、6 段、Jitter .18），由 `NextChargeArc` 节流、`DestroyChargeVisual` 随清。

资产表：Assets[2]=Beam、[3]=Charge NS、[9]=Ribbon、[10]=IrisMesh、[11]=IrisMat、[12]=Gather；`NetInit` 远端副本同步换路径。

**客户端本地弧修补**：充能汇聚弧是首个在纯客户端本地 spawn 的 AFPSLightningArc——原 Tick 在 `!bNetInit` 时直接 return，本地弧会卡死在等复制字段。新增 `bInitialized` 标记（三个 Initialize* 内置真），非权威端先判 `!bInitialized` 再等 NetInit；复制副本在 NetInit 内即被初始化不受影响。

## 顺手修的两处无关编译错误（其他会话在途文件，最小改动）

- `ZhenmoRuneComponent.cpp`：`GetLifetimeReplicatedProps` 形参名 `Out` 改回 `OutLifetimeProps`（DOREPLIFETIME 宏要求该标识符）。
- `RuneSwordAzureDragon.cpp`：匿名命名空间 `MaterialPath` 常量与 `TacticalDeviceComponent.cpp` 局部变量在 unity 构建中重名触发 C4459，改名 `AzureDragonMaterialPath`。

## 音效（2026-10-06 增补）

- `S_ThunderLanceDischarge`（2.0s）：程序化合成——40ms 宽带爆响双击 + 密度渐稀的 1.4-8.2kHz 噼啪 + 118Hz 起振发射 hum + 62Hz 轰尾；发射时在杖尖（含纯客户端本地回放）和柱尾端点配合。
- `S_ThunderLanceCharge`（2.6s）：上升式噼啪密度 + 82→200Hz 升调 hum，蓄力开始随 gather 粒子同播。
- 合成脚本 `Tools/Skills/make_thunder_lance_audio.py`，导入 `import_thunder_lance_audio.py`；原创程序合成，无第三方采样（provenance 在 `Records/*.json`）。
- 接线：Assets[13]=Charge、[14]=Discharge；蓄力起点放 Charge(.9)，释放/客户端本地/服务端三处放 Discharge(1.0)。

## 判定检查结论（2026-10-06）

`FireLanceBody` 命中链完整可命中怪物：候选 `Nearby` 球形走廊（半径=半程+半宽+120）→ `Enemy()` 过滤 → `Along∈(0,Reach]` 轴向距离 → 侧向偏移 ≤ `HalfWidth(60cm)+min(Extent.X,Y)*.6` → `ECC_Visibility` LOS（忽略全部候选目标，墙体遮挡生效）→ 按距离排序逐个 `ApplyLightningHit`（ApplyPointDamage/LightningDamage）+ 侧弧 + 击退 + 感电。服务端 `NetRelease` 重跑同一函数，远端表现经弧复制。注意两点：命中走廊(~80-110cm)比视觉束(半宽115cm)窄，擦边不判定（刻意设计）；`TargetPoint` 取胶囊中心，瞄身体即可命中。未发现需要修复的判定缺陷。

## 验证边界

资产 commandlet `Records/commandlet-01.log` 零 error 保存 8 份；`FPSGAME Win64 Development` Result: Succeeded。未开编辑器/PIE/截图，实机观感由用户测试。ThunderFluxV3 资产保留在盘上未被引用（雷枪柱不再使用；如需回滚仅需换回资产路径）。

## 枪口放射特效定向化（2026-10-06 增补）

释放瞬间的杖尖放射从通用球面喷花（`NS_ElectricImpact`，命中/末端仍用）改成定向枪口冲击：

- 新增 `NS_ThunderLanceMuzzle`（`author_thunder_lance_muzzle.py`）：前锥高速电丝（local +X=瞄准向，360-640cm/s）+ 宽角侧溅碎片 + 慢速余辉火花 + 白热闪光芯；生成时组件按 `MakeFromX(Dir)` 旋转整个系统。
- `MuzzleFlashFX`：`SM_ThunderLanceIris` 虹膜盘改作**垂直瞄准轴的冲击盘面**——160ms 内 26→230cm×Visual 展开、Strength 1.7→0 淡出，取代原 billboard 圆环的方向感缺失；Tick 驱动，`CancelPending` 清理。
- 释放瞬间在垂直瞄准面拉 6 条径向闪电扇（`SpawnArc`，.09/.2s、5 段、Jitter .3、150-260cm×Visual），与束身环绕弧同一语言。
- `SpawnBurst` 加可选 `UObject* System` 参数（缺省仍走 Assets[4] ElectricImpact）；Assets[15]=Muzzle NS。
- 纯客户端（NM_Client）释放路径本地同步补一发 `MuzzleFlashFX`——burst/盘面不复制，远端玩家看到的仍是服务端 `FireLanceBody` 的产物（弧扇经复制到达）。
- 命中点/末端/感电过载的爆闪、音效、镜头震动全部不变；伤害结算未动。
