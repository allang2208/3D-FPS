# 电矛：矛形剪影、雷电扭动与穿透反馈

针对"像静止光柱、命中/穿透反馈弱"的观感问题做第二轮表现优化。方向由用户确认：保留光束，加矛形头部；驻留时长做成可调参数。伤害、贯穿顺序、感电、击退、修炼、散射与准星契约不变。

## 束形与运动

`FluxCommon.hlsl` 新增 `SpearProfile(q)` 轴向轮廓：近杖端收窄到 .55（读作从杖尖射出）、q≈.88 头部膨起 +.30、q>.95 急收成尖头。`FluxDisplacement.hlsl` 在径向翻卷之外加侧向蛇形位移——沿 side/up 两个垂直方向叠加低频与高频正弦（相位由各层 Seed/密度场错开），按 Role 分级：芯 .02、中 .09、外层与电丝 .20（乘层半径），束身轮廓真正折线扭动而不是等径直管。电丝层额外周期性离面抬升，让电弧脱离宿主管面。

`FluxMask.hlsl` 的 `front` 建立时间从 45ms 改为 90ms 的可见前扫（发射行程感），并加 `tipTaper` 使尖端亮度随塌缩收束，不再以平头亮盘收尾。材质 flash 节点（`build_thunder_flux_v3.py`）接入 P/Origin/Axis/Length，新增常驻矛頭亮带（q≈.88 高斯 +2.6）和一次沿轴前冲的出发闪光（~110ms 扫完全长后衰减）。

`FluxFilaments.hlsl` 电丝 4→7 条不等距折线路径，每条带二级分叉（branch/fork），22Hz 重抽路径、亮段以 Age*140 高速前冲、逐条闪变；线宽随 q 向尖端变细。

## 分层消散与可调生命周期

`FElectricMagicTuning` 新增 `BeamHold`/`BeamFade`（默认 .45/.6），`skills.json:thunderLance` 增加 `"beamHold": 0.45`、`"beamFade": 0.6`（解析处限幅 [.05,4]/[.05,2] 秒）。`ColdSteelElectricMagicModel` 的 `H.Duration`/`H.Fade` 对 thunderLance 改读这两项，stormDomain 仍用 .42/.22。原 2 秒驻留是当时临时观察参数，正式收回。

`AFPSLightningArc::Tick` 的柱分支改为按层错峰消散：相干芯先灭（延迟 0）、中层 .10×Fade、外层 .20×Fade、电丝 .45×Fade 最后消散——光柱"碎裂成游离电丝再消失"的放电收尾。`SetLifeSpan` 相应放宽到 Hold+Fade×1.55。

## 命中与穿透反馈

贯穿每个敌人时从束轴对应距离点向受击点拉一条短命视觉电弧（`InitializeArc` 复用，Segments=5、Duration=.08、Fade=.2、Jitter=.22、无接触灯、亮度40），把"枪穿过人"连起来。命中爆闪规模乘充能视觉强度并随感电层数放大（每层 +.08，上限 5 层）。

末端爆闪按方向定向：打墙取 `EndHit.ImpactNormal`，空中消散取反束方向；并散布残余放电弧（阻挡 3 条、空端 2 条，长 160–320cm、.12s 驻留、.3s 淡出）。杖前爆闪 ×1.2 基础规模乘充能强度。

## 充能视觉回报

`FireLance` 的 `Ratio`（充能/满充，下限 .2）驱动 `Visual=lerp(.55,1)`：`InitializeColumn` 新增 `ChargeRatio` 入参，束径 ×Visual、Emission ×lerp(.65,1)、末端灯 ×Visual；杖前爆闪、命中爆闪、末端爆闪同样乘 Visual。20% 充能是细弱束，满充才是完整巨枪。伤害仍用独立 `Ratio`，不混。

## 作者脚本修复（重要）

定位到 ThunderFluxV3 材质自 10/01 Strength 轮起一直编译失败回退默认材质的根因：`UMaterialEditingLibrary::DeleteAllMaterialExpressions` 在 range-for 迭代中删除元素，每次只删掉约一半表达式；幸存旧 Custom 节点被 `BreakLinksToExpression` 断开输入后残留图内，报 `missing input 1 (P)`。`build_thunder_flux_v3.py` 改为 `get_material_expressions` 快照后逐个 `delete_material_expression`，本轮编译零告警。旧记录中"旧 Custom 节点缺输入的中间态告警"实为持续残留，已由本轮修复。

## 验证边界

四份资产经后台 D3D12/SM6 commandlet 重新保存，退出码 0、无材质编译告警，回执 `Saved/ThunderLanceSpear20261002/asset-authoring.json`、日志 `asset-commandlet-02.log`。Game 构建最终 Result: Succeeded，日志 `Saved/ThunderLanceSpear20261002/build-game-02.log`；构建要求编辑器关闭，本轮 Editor 目标未构建（用户编辑器仍在运行，重启后随普通构建生效）。未开编辑器、未运行 PIE、未截图验收，实机观感由用户测试。电弧预算仍走 48 上限共享池（贯穿目标侧弧与末端残余弧计入同一池），爆闪池 24 不变。

# 第三轮：去线稿化、慢演化与全局淡入淡出（2026-10-04）

针对"线条感太强、缺乏淡入淡出、闪电跳跃感太强、过于廉价"的观感反馈做第三轮表现优化。诊断：上一版把"电"做成画出来的折线（参数化 strokes + 22Hz 硬重抽 + 高速前冲），读作描边线稿而非发光等离子体；瞬间全亮/线性全灭无过渡。本轮方向：电丝改为阈值化放电通道，一切运动降速，所有元素加软过渡。

## 电丝：参数化折线 → 阈值化脊场放电通道

FluxFilaments.hlsl 整体重写：不再绘制 N 条参数化折线 strokes，改为对滚动密度场做双阈值——B 通道"亮脊"提供自然分叉的放电通道形状，R 密度决定放电允许存活的区域，smoothstep(.56,.72) 窄热通道 + smoothstep(.30,.62)×.38 宽软放电光晕。通道随场滚动连续生长、合并、溶解，自带淡入淡出；闪烁只调制亮度（6.3/11Hz 复合正弦），不再调制路径位置。离面抬升频率 22→7Hz。uild_thunder_flux_v3.py 给 filament 的 mask Custom 补接 NoiseTex 输入与 shared 前缀（FluxCommon）。

## 全局淡入淡出

- FluxMask.hlsl：front 前扫通过后加 .55+.45*smoothstep(.08,.26,Age) 亮度 ramp，束体升到满强是 260ms 渐入而非瞬亮；轮廓边缘 ngularCoverage 基线 .40→.50、指数 .70→.50，剪影更软。
- AFPSLightningArc::Tick：柱 BeamAlpha 乘 min(1,Age/.10) 淡入；消散从线性改 pow(1-T,1.7)——先发快速衰减、余晖长拖尾的等离子冷却曲线。末端灯与通用弧（侧弧/残余弧/连锁）同样加 min(1,Age/.06) 淡入与同一条衰减曲线。
- skills.json beamFade .6→.8，放电收尾读得出。

## 跳跃感收敛（一切降速）

FluxDisplacement.hlsl：翻卷滚速 42→14，蛇形三频 14/31/11→5.5/11/6，外层蛇形振幅 .20→.16、中层 .09→.08——从频闪抖动改成缓慢有力的摆动。侧向命中电弧加宽 .6→1.1、驻留 .08→.10（读得出淡入），末端残余弧 .5→.8。

## 验证边界

四份资产经后台 commandlet 重新保存，0 error、无 missing input/Failed to compile，日志 sset-commandlet-03.log。Game 构建结果见 uild-game-03.log。未开编辑器、未运行 PIE、未截图验收，实机观感由用户测试。

## 修正：电丝阈值不可达导致整层熄灭（2026-10-04）

第三轮后用户反馈"几乎看不到效果"。根因：电丝 eins 以 ield.b（脊通道）为主驱动（权重 .80），该通道偏弱时 eins 到不了 .56 阈值，hot/halo 双双趋零——Additive 电丝层整层熄灭，只剩半透明管体。修正：eins = density * (.60 + .50 * coarse.b) + detail.b * .10，density 用与束体同源的 coarse.r*.66 + detail.g*.34 保证覆盖，B 通道退为分叉调制；阈值降至 hot=.48–.64、halo=.24–.52×.50；flicker 基线 .68→.78、ramp 基线 .55→.65。commandlet sset-commandlet-04.log 零 error 保存。教训：**阈值化场的阈值必须在主驱动通道的可达量程内；用未知强度的辅助通道做主驱动要先验证或退为调制项。**
