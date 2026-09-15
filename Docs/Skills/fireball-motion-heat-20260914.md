# 火球镜头残影与悬浮热浪（2026-09-14）

用户要求优化移动镜头时的火焰残影，并参考近战剑攻击的空间扭曲，在悬浮火球周围加入热浪。此次为材质及 Niagara 制作接入，不改技能数值、施法手势、伤害、飞行轨迹或存档。

## 镜头移动时的火焰

两层流体燃烧主体、短外焰、薄烟使用 `AfterDOF`；主体及拖尾 Sprite Renderer 显式选择 `MotionVectorSetting=Precise`。`Responsive AA` 用于 TAA 兼容；不把它当成 TSR 消除残影的单独开关。首次制作曾启用半透明深度／速度输出，后因与 DepthFade 冲突而关闭，详见下方修复记录。当前材质不写半透明速度，不能声称仍使用该方式消除残影。

该调整针对镜头跟随火球与背景运动信息不一致时的时序重投影和运动模糊。没有进行动态画面对照，因此不声称已经证实全部残影消失。保留现有世界空间飞行尾焰的短寿命，它是设计效果。

仍保留场景深度测试及 DepthFade。UE 5.8 的 `Material.h` 明确注明 `AfterMotionBlur` 会禁用深度测试，因此本轮没有使用这个绕过方式。全局 TSR、运动模糊与画质配置不变。曝光补偿、预乘透明和上轮清除的爆炸裁剪纹理继续保留。

引擎资料：[Epic TSR FAQ](https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-frequently-asked-questions-for-unreal-engine)、[TSR 技术说明](https://dev.epicgames.com/documentation/unreal-engine/temporal-super-resolution-in-unreal-engine)。实现依据还包括本机 UE 5.8 `Material.h` 和 `NiagaraRendererProperties.h`。

## 悬浮热浪

参考实际剑气 `/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift` 及其作者脚本，复用现有授权素材 `/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A`，使用相同的流动法线与 IOR 折射机制。

- 新材质：`/Game/Skills/Fireball/FluidBurn20260914/M_FluidHoverHeatHalo`。独立制作外围环状遮罩，内外缘软化并随噪声变形，中心弱化；不复用剑气的蓝光或挥砍弧面。
- 尺寸约 60×68 cm，位置位于火球根部上方约 6 cm，缓慢升腾及 2.5% 呼吸变化。`HeatStrength=0.035`，小于普通剑气的 0.085，弱透明覆盖为遮罩的 0.025 倍。
- 发射器 `FireballHoverHeatHalo` 替换旧 `FireballFluidHeatHaze`，生成率 1.25/s、寿命 1.6 s，平滑交叠；本地空间跟随球体。使用现有 `User.Flight`／`User.FlightAge`，发射后 0.04–0.22 s 内淡出，不新增 C++ 状态。
- 热浪在景深前折射背景，保持世界深度及 12 cm 接触淡化。热浪本身不写运动速度，以免用透明环的速度替代其后面的世界几何。

## 文件与交付

- 增量入口：`Tools/Skills/tune_fireball_motion_heat.py`，只更新当前材质、Renderer 和热浪发射器，保留燃烧层现有时间参数。
- 完整生成器：`Tools/Skills/build_fireball_fluid_burn.py` 已同步，新生成资源使用同样的运动与热浪设置。
- 新增薄烟专用父材质 `M_FluidThinWispMotion`，修改项目副本，原 Epic／剑气资源保持原样。
- 作者目录：`SourceAssets/FireballMotionHeat20260914`，包含修改前备份 `Before/`、制作日志及完成保存后写出的 `installation.json`。

首次命令行制作被打开的编辑器占用资产文件打断；占用解除后重试制作。只运行了必要的材质／Niagara 编译与资源保存，没有启动游戏、自测、截图或渲染验收。实际转镜头残影与热浪强度由用户重新加载资源后测试。

制作重试以退出码 0 完成，记录 `FIREBALL_MOTION_HEAT_INSTALLED`，主体与拖尾编译均返回 `valid=1`。记录在作者目录 `authoring-retry.log` 与 `installation.json`，属于资源制作完成记录。

## 后续：默认棋盘格修复

用户实际试玩反馈“全是马赛克”。运行日志中四个父材质均报告 PCD3D_SM6 编译失败，首个错误为 `(Node DepthFade) Translucenct material with 'Output Velocity' enabled will write to depth buffer, therefore cannot read from depth buffer at the same time.` UE 随后用默认棋盘格代替火焰与薄烟。此次回归由上轮开启 OutputVelocity 引入，原图集和热浪贴图没有损坏。

修复关闭 `M_FireballFluid_A/B`、`M_FluidShortFlamesExposure`、`M_FluidThinWispMotion` 的 Output Translucent Velocity，保留现有 DepthFade、曝光补偿、场景遮挡与环状热浪；完整生成器及增量入口同步，避免重建再次出现冲突。残影问题目前保留 AfterDOF、TAA ResponsiveAA 与 Renderer Precise 设置，其改善程度仍需用户判断，不视为已完全解决。

已打开编辑器可运行 `Tools/Skills/fix_fireball_velocity_depth_conflict.ps1`，通过制作接口改材质、实际 RHI 编译并精确保存。编辑器关闭时使用同名 `.py` 配合 `-AllowCommandletRendering` 编译保存；此脚本不创建场景、不启动游戏或截图。修复备份为作者目录 `BeforeVelocityConflictFix/`，保存结果为 `velocity-conflict-fix.json`，命令行编译日志为 `conflict-fix-sm6.log`。

上轮 `-NullRHI` 制作成功和 Niagara 的 `valid=1` 不能证明 SM6 材质可编译；今后修改包含 SceneDepth／DepthFade 的材质渲染标记，必要制作编译使用真实 RHI，不能仅用 NullRHI 回执宣布材质编译完成。默认不运行游戏测试的用户规则继续生效。

本次修复命令行以 D3D12 运行并以退出码 0 完成，四个材质均记录编译和保存完成。薄烟在载入旧版本时先出现同一冲突警告，关闭标记后重新编译保存；日志中的该条旧版本警告不等于修复后再次失败。未重新进入游戏验证视觉效果。
