# 冰锥 5080 模型与寒气升级

用户批准专用写实冰锥、冰材质与悬浮寒雾升级，并指定可使用 5080 管线。此轮只制作、导入、接入与必要构建，没有启动游戏、生成验收渲染或运行测试。

## 模型制作

- 内置 imagegen 制作同对象正／右侧／背三视图，保存 `SourceAssets/IceSpike5080_20260915/three_views.png` 和 `reference_prompt.txt`。该图是生成输入，不是 UE 实际效果图。
- 1536×1024 图片按三个 512×1024 区域分别裁切、去背景，接入 TRELLIS.2 真正多视图节点的 front/right/back。生成流程、当前输入定义和回执均保留。
- 5080：TRELLIS.2-4B，1024_cascade，结构分辨率 64，16/32/24 步，4K 母版纹理，seed 91571，prompt_id `7cefe280-5448-4d05-8940-4d12ff420fcb`，生成完成。固体自然冰锥开启填洞及外壳保留；不套用机械孔洞选项。
- 带纹理母版 476,094 面；游戏网格每种 18,000 三角面，2K 法线由母版烘焙。三个变体来自同一母版的轻微横截面、曲率变化，非三次独立生成。
- 冰体全长 54cm，局部 +X 指向尖端；运行中增加不同轴向转角。可编辑源 `IceSpike5080_Editable.blend`，游戏 FBX 与纹理位于 `Game/`。不再附加三块装饰玻璃片充当主体轮廓。

## 材质与寒气

- `M_IceHeart`：缩在外壳内部的乳白／淡蓝次表面内芯。`M_IceShell`：受光通透表层、烘焙法线、裂纹层和粗糙霜根。顶点红色存储从根到尖的归一化长度，用于霜根遮罩。不是完整体积折射模拟。
- 冰体没有自发光、屏幕颜色采样和折射输出。寒雾父材质使用 DepthFade，关闭输出透明速度，保留响应式 AA 与正常深度测试，避免重用火球曾经产生棋盘格的冲突配置。
- `NS_ColdMist`：悬浮时约每枚 18 粒／秒，从根部与侧面溢出、下沉扩散；寿命 0.40–0.66 秒，尺寸逐渐扩散。发射前 0.16 秒短暂加量，飞行时缩短到 0.10–0.16 秒，沿实际前后位置段分布，并向后运动。
- `NS_FrostCrystals`：悬浮稀疏细冰晶，飞行增加拖尾。冰晶尺寸远小于主体，不遮挡冰锥辨识。
- 雾粒子在世界空间生成；不将已生成粒子随摄像机旋转。近距离淡出与深度淡化缓和穿过镜头／墙面的观感。每枚冰锥的雾由独立短命宿主承载，命中／取消后停止新增，已有雾最多再保留 0.85 秒自然消散。

## 接入与恢复

运行目录 `/Game/Skills/IceSpike/FrostV2`：三种 `SM_IceSpike_01/02/03`、`M_IceHeart`、`M_IceShell`、`T_IceBaseColor`、`T_IceNormal`、`M_ColdMist`／`MI_ColdMist`、`NS_ColdMist` 和 `NS_FrostCrystals`。

`FPSIceSpikeComponent` 加载这些资源；`FPSIceSpikeVolley` 负责形态轮换、双层冰体和寒气阶段。命中碎冰与音频继续依赖首轮冰锥资源。伤害公式、数量成长、冷却、蓝耗、射程、要害暴击与存档不变。

恢复顺序：保留 5080 原始输出 → Blender 执行 `Tools/Skills/author_ice_spike_5080.py` → UE Python 命令行执行 `Tools/Skills/build_ice_spike_frost_v2.py` → 必要原生编译。原有冰锥与火球作者素材仍是派生资源的来源，保留用于恢复，不改写共享原包。

来源表为 `SourceAssets/IceSpike5080_20260915/provenance.json`。冰裂纹继续采用原 MIT 文件与许可；寒雾使用本机已有授权 Epic 片库副本。未购买或导入新的 Fab 付费模型，未发布素材二进制。

## 交付记录

模型生成、游戏网格导出及贴图烘焙完成；UE 资源导入和材质／Niagara 必要编译完成。导入记录：`Saved/IceSpike-FrostV2-Assets-20260915.log`；最终原生构建 `FPSGAMEEditor Win64 Development` 成功，模块后缀 `9150701`，146 个动作，112.55 秒，记录见 `Saved/IceSpike-FrostV2-Build-Final-20260915.log`。

用户需重新打开工程加载新原生模块，再测试实际游戏表现。本轮未运行游戏测试或视觉验收，不宣称效果已经获得用户确认。

## 后续：头顶固定排列

按用户要求，悬浮阵列取消绕身旋转、周期起伏与计时自转，改成随视角整体移动的头顶居中横排。位置由相机前方 44cm、上视锥边界计算，完整 54cm 冰锥的后半段留在画面上方，尖锐的前半段进入屏幕顶部。随数量保持左右对称，基础间隔 18cm，窄画幅或窄视野时压缩排布宽度。向头顶位置执行现有墙体／顶棚避让。凝聚缩放、寒气与从实际悬浮位置齐射继续保留。

必要原生构建使用独立后缀 `9150710`，记录 `Saved/IceSpike-Overhead-Build-20260915.log`；未启动游戏或视觉测试，由用户测试实际露出比例。

## 后续：自然小范围漂移

用户要求头顶排布更自然：保留横排槽位和尖端露出，在每枚冰锥的槽位内加入独立上下／左右漂移。凝聚时一次性随机各轴的噪声起点与速度，由连续 Perlin 噪声随时间驱动，不逐帧随机位置。左右最大偏移 2.8cm，上下最大偏移 2cm，随槽距和视野缩小幅度；不同冰锥各自缓慢变化，凝聚期间逐渐加入漂移。继续取消绕身旋转和自转，寒气与实际发射位置跟随本体。

必要构建使用独立后缀 `9150711`，日志 `Saved/IceSpike-Drift-Build-20260915.log`。未启动游戏或视觉测试，由用户测试漂浮观感。

## 后续：闪光与高光柔化

用户反馈冰锥闪光，询问是否自发光并要求优化。读取实际已保存的材质输入：M_IceHeart/M_IceShell 的 EmissiveColor 均未连接；NS_FrostCrystals 的精灵使用 M_IceMote，其 Unlit 材质将粒子颜色直接连接 EmissiveColor。冰体表层原粗糙度下限为 0.065、Specular 为 0.52、法线强度 0.60。由此确认有自发光冰晶及尖锐表层高光两项来源；未启动游戏逐层复现，不将其声称为唯一视觉根因。

- 冰晶改用新增 `M_FrostCrystalSoft`：受环境光照的半透明霜屑，无自发光输出，保留近距离和深度淡出。悬浮发射率 4→2.2 粒／秒、最大粒子 Alpha 0.45→0.24，寿命增加至 0.45–0.65 秒；平滑淡入／淡出，出生时 Alpha 为 0，避免短亮点突然出现。飞行发射率 38→25，寿命 0.18–0.30 秒。
- 表层粗糙度范围改为 0.19–0.40，Specular 0.24；内芯粗糙度 0.27–0.45，Specular 0.30。法线强度统一改为 0.35，减弱细碎尖锐高光，保留冰裂纹和通透轮廓。
- 寒雾 Emissive Gain 0.16→0.06，保留淡薄寒气。

作者脚本 `Tools/Skills/build_ice_spike_frost_v2.py` 支持 `-IceLightOnly`，只更新冰体光照、冰晶与寒雾亮度，不重导模型。完整重建入口也已同步参数。修正前材质／粒子资产与输入快照现已移入 `trash/skills-magic-20260915/SourceAssets/IceSpike5080_20260915/SoftLight20260915`；制作结果仍在原源目录，归档见 [清单](skills-magic-archive-20260915.json)。

必要材质及 Niagara 编译完成，最终命令行退出 0，记录 `Saved/IceSpike-SoftLight-Final-20260915.log`；未进行游戏测试或截图。初次制作中 Niagara CPU VectorVM 不支持表达式 `smoothstep()`，已展开为等效的 Hermite 多项式后完成编译；不要误用为 GPU／材质也不支持该函数。

## 后续：整体可见与加大漂浮（2026-09-16）

用户反馈悬浮位置太高、只能看到尖端，且浮动幅度太小。按实际网格尺寸重算头顶位置，并加大漂移。

- 网格实测（`SourceAssets/IceSpike20260915/engine-authoring.json`）：54 cm 全长沿局部 +X，包围盒半长 27、横截面半径 6.1／5.49。尖端朝视线外，因此最靠近镜头、画面占位最大的是较粗的根部。
- 原方案在相机前方 44 cm、高度取 `(44+4)*上视锥正切`，位置取“上视锥边界切过网格中心”，只有尖锐前半段进画面。44 cm 处单是根部圆盘就覆盖超过半个垂直视野，无论怎么下移都无法整体入画，所以这次把整排移到前方 72 cm，再按同一上视锥几何降低高度：`高度 = (72 − 27) × 上视锥正切 − 6.1`，即根部圆盘刚好贴上视锥边界，整根 54 cm 冰锥完整可见，横排仍留在画面上方、不挡准星。
- 漂移加大：左右上限 2.8→7 cm（仍随槽距缩放），上下上限 2→5.5 cm（取可见高度的 24% 与上限的较小值），并且高度里先减去上下漂移幅度，保证浮动到最高点时冰锥仍然完整。横排基础槽距 18→22 cm，避免更大的左右漂移让相邻冰锥穿插。
- 现场调参：`fps.IceSpike.HoverDropCM`（额外下降厘米数，0 为当前几何解）与 `fps.IceSpike.DriftScale`（漂移倍率，1 为当前值）在 PIE 中即时生效；用户确认手感后把数值写回默认。ADS／冲刺改变视野时按同一几何公式自动跟随。

未编译、未进 PIE；位置和漂移观感由用户测试。

## 后续：火焰拖尾残留渲染器（2026-09-16）

用户反馈悬浮冰锥有非常刺眼、类似火球红光的光效。按 Niagara 工具集实际读回两个运行系统和火球系统的渲染器列表，定位为继承自火球拖尾链的第二渲染器，已移除并读回确认。

诊断（只读证据 `Saved/IceSpike-Glare-Inspect.json`，由 `Tools/Skills/inspect_ice_spike_glare.py` 生成）：

- `NS_RocketTrail` 的 `RocketTrail` 发射器本来就有**两个**精灵渲染器：`[0]` 是拖尾材质，`[1]` 是 `MI_RocketFlareCore`（火箭火焰核心，暖色高亮）。`NS_IceMotes` → `NS_FrostCrystals`／`NS_ColdMist` 逐级复制时只改了索引 0 的材质，索引 1 原样保留，因此悬浮和飞行的每颗粒子都被额外画了一遍火焰核心 —— 这就是“红色火焰特效”。
- 工具集读回的渲染器类全部是 `NiagaraSpriteRendererProperties`，两个冰系统里并没有 Niagara 光源渲染器；`.uasset` 中的 `NiagaraLightRendererProperties` 字符串只是派生时留下的类型表残留，不代表实际有灯。
- `MI_ColdMist` 的参数为黑体温度 0–5000、Emissive Gain 0.06、`Use Particle Color For Emissive` 关闭，实际不产生可见自发光；`M_FrostCrystalSoft`、`M_IceHeart`、`M_IceShell` 与命中特效 `P_IceSpikeImpact` 内都没有火焰／闪光引用。

修复（`Tools/Skills/clear_ice_spike_flare_renderers.py`，headless 执行并读回）：

- 两个运行系统各删除索引 1 的 `MI_RocketFlareCore` 渲染器，只保留索引 0 的自有冰材质渲染器；材质、模块、粒子颜色未改动。
- 读回结果：`NS_FrostCrystals` 与 `NS_ColdMist` 各剩 1 个渲染器（`M_FrostCrystalSoft`／`MI_ColdMist`），二进制中 `RocketFlare` 引用数为 0；记录 `SourceAssets/IceSpike5080_20260915/FlareCore20260916/authoring.json`，日志 `Saved/IceSpike-NoFlare-20260916.log`。
- `build_ice_spike_frost_v2.py` 增加 `strip_source_renderers()`：以后从 `NS_IceMotes` 派生时，凡材质仍指向 `/Game/NiagaraExamples/` 或 `RocketFlare` 的渲染器一律丢弃，重建不会再把火焰核心带回来。
- 火球自身的 `NS_FireballTrail`／`NS_FireballVelocityTrail` 保留该渲染器，属于火球既有表现，本轮未改。
- 首轮遗留的 `NS_IceMotes`（当前没有任何运行引用，仅作为派生母版）保持原样；如需彻底清理，可在确认不再派生后单独处理。

改动前资产存于 `trash/skills-magic-20260916/IceSpikeFlare20260916/` 并记录散列。本轮未启动游戏、未截图，实际观感由用户测试。

## 后续：中轴留空、左右两翼排列（2026-09-16）

用户反馈悬浮冰锥与近战武器位置重叠，要求以玩家中轴为对称轴把中间让开，改在左右两侧更宽的位置生成，并注意等级提升会增加枚数。

- 原排列是以中轴为中心的等距横排（`Slot = I − (N−1)/2`），枚数越多越往两侧铺，但中轴上始终有冰锥，正好压在近战武器的持握与挥砍区。
- 现改为两翼阶梯：`Slot = ±(GapUnits + floor(I/2)) × Spacing`，偶数索引走左翼；中轴保留 0.9 个槽距（默认约 20 cm）的空档。两翼共用同一条槽位阶梯，因此升级新增的那一枚永远落在更外面一格，同翼相邻两枚相隔两格，增枚不会与已有冰锥挤在一起。
- 各枚数位置（视野 75°、16:9，槽距 22 cm）：2 枚 ±19.8；3 枚 ±19.8、−41.8；4 枚 ±19.8、±41.8；5 枚 ±19.8、±41.8、−63.8 cm。奇数多出的那一枚放在左翼，避开右手近战武器。
- 整排宽度仍以 72% 视锥半宽为上界：窄视野（ADS）或窄画幅时槽距按 `HalfRowWidth / LadderTop` 自动压缩（ADS 下 5 枚压到 16.6 cm），两翼始终在画面内；漂移幅度随槽距一起缩小。
- 现场调参新增 `fps.IceSpike.WingGap`（中轴空档，单位＝槽距，默认 0.9，最小 0.15），与 `fps.IceSpike.HoverDropCM`、`fps.IceSpike.DriftScale` 一起在 PIE 即时生效。
- 悬浮高度、漂移幅度、凝聚缩放、墙体避让与从实际位置发射的逻辑不变。

本轮做了单文件编译校验（`cl` 直接编译 `FPSIceSpikeVolley.cpp`，无诊断）；编辑器处于打开状态，未做完整 Editor 构建，未进 PIE。

首次上线的修正：`Slot` 改成“相对中轴的厘米偏移”后，位置表达式仍保留了 `Slot*Spacing`，等于把槽距乘了两次（最外侧约 436 cm），冰锥整体被推到镜头外，用户反馈完全看不到。已改为 `Right*(Slot+DriftX)`，`Slot` 只相加一次；单文件编译通过，并用 `LiveCoding.CompileSync` 成功热补丁到当前会话（`LogLiveCoding: Live coding succeeded`）。磁盘 DLL 仍是修正前的构建，需要关掉编辑器跑一次 `Tools/Build/Build-Editor.ps1` 才会持久化；热补丁会复位 `fps.IceSpike.*` 三个调参变量为默认值。

二次加宽（用户反馈右侧一根仍与剑类武器重叠）：中轴空档 0.9 → 1.4 槽距，槽距上限 22 → 26 cm（新增 `fps.IceSpike.SlotSpacing`），可用画面宽度 72% → 80%。默认位置随之改为（视野 75°、16:9）：2 枚 ±36.4；3 枚 ±36.4、∓62.4；4 枚 ±36.4、±62.4；5 枚 ±32.3、±55.4、∓78.6 cm，**以上数字覆盖本节前面的旧值**。完整 Editor 构建成功，磁盘 DLL 内含 `fps.IceSpike.SlotSpacing` 字符串（`TEXT()` 在 Windows 上是 UTF-16，ASCII 扫描查不到，需按 UTF-16 校验）。构建过程中并行的体素地形会话先后修掉了 `TemperateHillsWorld.cpp` 的命名空间限定与我此前补的 `C2065`、以及 `FPSVoxelCavePad.cpp` 的 `bEnableDistanceFields`（应为 `bGenerateDistanceFields`），两者都不是本次改动。
