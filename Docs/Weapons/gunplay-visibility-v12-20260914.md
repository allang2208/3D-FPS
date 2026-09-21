# Gunplay V12：恢复烟气与曳光的可见度

用户反馈 V11 烟雾几乎不可见，曳光也很难看到。本轮以枪口新生烟气可辨、旧烟迅速变薄、曳光沿射击方向可见为目标，避免再次通过增加烟雾滞留时间来恢复效果。

## 烟雾

V11 同时降低了单层不透明度、生成率和寿命，增加扩散稀释，又在瞄准中心将所有烟层乘以 0.25。多重衰减叠加压低了刚喷出的烟。

- `SmokeOpacity` 由 0.45 调为 0.55；腰射／普通 ADS／LPVO 系数由 0.20／0.12／0.085 调为 0.24／0.20／0.17。
- 生命周期起始快速淡入后，前段保留可辨认的密度，再按平滑曲线消散；扩散稀释系数由 1.6 降为 0.7。
- 视线淡化改为按粒子年龄渐入：新生烟不受中心衰减，扩散后的烟在小范围瞄准中心最多衰减 40%，向周围平滑恢复。使用 `ParticleRelativeTime` 接入粒子年龄，保留当前视口尺寸计算。
- 主烟单层 0.55–0.85 秒、余烟 0.80–1.10 秒及连续生成率上限 48 层/秒继续保留；侧向漂移和短促停火余烟继续使用 V11。

这次恢复的是枪口新生烟气的可见程度。连射不会将旧烟的寿命重新延长，也不通过每发重启烟团实现反馈。

## 曳光

原来的软圆柱材质把 Z 轴两端的透明度都降至零，同时按表面朝向衰减侧面。沿枪管方向看，侧面投影很窄，两端又不可见；原本 0.30 cm 的直径在正常射击距离也容易小于一个屏幕像素。

- `M_BallisticTracerVisibleV12` 增加两端径向柔化发光，保留暖色细亮芯和侧面渐变。
- 直径最低 0.8 cm，根据相机视野、视口宽度和轨迹深度适度增加，目标约 1.1 像素；腰射上限 5 cm、LPVO 上限 2.5 cm。
- 可见段上限从 75 cm 调到 180 cm，但始终限制在当前已经扫过的轨迹内；自发光参数从 7 调到 14。
- 保留深度遮挡、真实命中位置和逐帧回收。没有修改子弹速度、伤害、射程、穿透或输入逻辑，也不延长静止历史光段的寿命。

> 2026-09-21 更新：曳光已升级到 `M_BallisticTracerVisibleV13`（每颗子弹一条常驻光段、时域响应拒绝旧历史、尾部渐隐）。本文的 180 cm 段长上限、约 1.1 像素宽度、自发光 14 与「逐帧新建再回收」的口径均已被取代，见 [曳光弹表现升级方案](tracer-upgrade-plan-20260921.md)。烟雾部分（V12 及新生密度微调）仍然有效。

火光继续使用 V10，手枪尺寸和抛壳规则保持既有接入。

## 制作入口

- `Source/FPSGAME/Weapons/FPSWeaponFXComponent.h/.cpp`：烟雾可见度、曳光尺寸和资产引用。
- `Tools/AssetPipeline/build_gunplay_visibility_v12.py`：依赖 V11 烟雾、V2 曳光材质，创建三个新版资产。
- `SourceAssets/GunplayVFX20260914/SmokeSightlineV12.hlsl`、`TracerVisibleV12.hlsl`：项目原创材质算法。
- `/Game/Weapons/GunplayFX/M_MuzzleSmokeSheetV12`、`NS_FPS_MuzzleSmokeStreamV12`、`M_BallisticTracerVisibleV12`。

按用户规则仅制作、接入并完成必要构建，不启动游戏、不执行测试或视觉验收。以上是作者修改及设计预期，最终观感由用户测试。

三项资产已完成材质／Niagara 编译并保存，`Saved/Logs/GunplayV12-Assets-20260914.log` 记录 `GUNPLAY_V12_ASSETS_CREATED`。Commandlet 整体退出码 1 来自既存 GameFeatureData 配置及其他进程占用 MCP 端口的记录；Python 制作完成。

普通 Editor 原生构建完成：`Saved/BuildEditor/build-20260914-093605.log`，`Result: Succeeded`，包含 `FPSWeaponFXComponent.cpp` 编译与模块链接。未运行游戏测试。

## 新生烟气密度微调

用户认可 V12 方向，并要求适当提高刚喷出时的密度。只在现有透明度曲线上增加初段 20% 的乘数：年龄前 10% 保留该增量，在年龄 10%–35% 内平滑归零。主烟约在出生后 0.19–0.30 秒回到原有曲线；寿命、扩散、生成频率、中心视线处理、火光和曳光均沿用本版参数。

曲线源统一放在 `SourceAssets/GunplayVFX20260914/SmokeAlphaV12.hlsl`，完整生成器和专项入口 `Tools/AssetPipeline/tune_fresh_smoke_v12.ps1` 读取同一表达式。专项入口通过运行中的编辑器 MCP 修改当前烟系统，完成 Niagara 编译后保存，不启动或停止游戏。

本次已经由编辑器 API 完成编译和保存：编译返回 `UpToDate`、无错误且无待编译任务，`save_assets` 返回 `true`。无 C++ 变动，无需重新构建原生模块；未运行游戏测试或画面验收。

## 其他 Gunplay 优化建议（本轮未实施）

以下基于当前源码与用户反馈，未通过本轮游戏画面或试听作出结论。

1. **优先补命中材质反馈。** `FPSWeaponFXComponent::OnImpact` 当前以组件 `Metal` 标签或材质 0 的名称判断金属、木材，其余采用通用尘土，表现主要为 2–4 个粒子。建议改由命中物理材质识别金属、木材、石材、泥土等，配合材质对应的火花／碎屑、弹痕和撞击声。已有的有效伤害确认及命中准心继续复用。UE 的 [Physical Material／Surface Type](https://dev.epicgames.com/documentation/unreal-engine/physical-materials-user-guide-for-unreal-engine) 可以承担表面分类。
2. **完善连射枪声和停火尾音。** `FPSGAMECharacter.cpp` 已有六声部并发的步枪分支，也保留 `M4FireVoice->Stop()` 后重播的分支；后者会终止上一段录音，其听感影响仍需试听。建议将击发起音、机械声、环境尾音分层，让尾音在受控声部数内短暂重叠。使用已有并发机制以及 [Sound Concurrency](https://dev.epicgames.com/documentation/en-us/unreal-engine/sound-concurrency-reference-guide) 的声音回收淡出来约束堆叠。
3. **细调不同枪型的视觉后坐节奏。** 当前已有枪体位置与旋转弹簧、随机抖动、镜头脉冲、FOV punch 和分枪参数。建议进一步区分首发、连发和停火的回落过程，手枪体现短促上翻，步枪体现轴向后冲与较快回稳，高倍镜以可持续追踪目标为优先。属于现有表现层的节奏调校，保留弹道后坐力和弹药逻辑。

推荐先实施第 1 项；粒子、弹痕与声音的材质差异能为每一次击中提供更明确的反馈。
