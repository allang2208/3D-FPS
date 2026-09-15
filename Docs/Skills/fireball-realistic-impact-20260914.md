# 火球写实命中反馈（2026-09-14）

2026-09-15 按用户要求将实际伤害半径扩大至本文热浪范围，现有爆焰／热浪尺寸保留；当前半径、直击与衰减规则见 [火球数值优化](fireball-balance-20260915.md)。本文“伤害半径不变”的表述仅指当时的视觉制作阶段。

后续范围成长更新还补上 Niagara SpriteSize 的显式缩放：此前组件缩放改变了粒子位置，但不能据此声称贴图尺寸同步放大。当前统一由实际伤害半径派生组件扩散与 `User.ImpactGrowth` 尺寸倍率，详见上方当前数值文档；本文旧灯光上下限与独立参考半径已被替代。

用户确认现有火球“基本合格”，随后授权按建议优化命中效果，要求偏写实。本轮落实优先级最高的三项：方向性爆燃、热冲击波、短促照明与分层音效。少量火星／薄烟用于收尾；表面材质分支和焦痕留在后续阶段。

## 当前表现与接入

运行资源统一放在 `/Game/Skills/Fireball/ImpactRealistic20260914`，由 `FPSFireballComponent` 的软引用加载：

- `NS_FireballImpactRealistic`：接触爆燃 1 个、向外翻卷的爆焰 6 个、薄烟 3 个、短火星 14 个；均为一次性发射，自身生命周期结束后由 Niagara 池回收。
- `M_FireballHeatShockwave`：没有彩色发光圆环，以噪声法线折射背景。命中实体使用沿命中法线的平面热浪，空爆使用球壳；加强版在 0.36 秒内扩散并衰减，Actor 在 0.40 秒销毁。
- `S_FireballImpactLayered`：1.25 秒单声道分层混音，包含短低频压力、爆燃主体、少量余烬噼啪。`ATT_FireballImpact` 开启空间化，近场半径 120 cm、外侧衰减距离 2400 cm；每次整体音高在 0.96–1.04 内轻微变化。

爆燃取现有授权 Epic Niagara Examples 的 `MI_Explosion_8x8` 和 `T_Explosion_EOO`，按粒子寿命顺序播放一次，不再沿用原火球爆炸中的循环 Roil 序列作为主爆燃。使用独立父材质副本 `M_ImpactCombustion`，保留原曝光补偿、柔和透明度、世界深度；黑体美术温度范围调到 950–4200，发光增益 1.6。此参数用于美术配色，不代表现场测得的物理温度。

`FPSFireballProjectile::Explode` 将 FX 放在真实接触点外侧，局部 Z 对齐表面法线。组件激活之前设置 `User.SurfaceHit` 和 `User.LocalUp`，池中复用的实例也会覆盖这两个参数。撞墙／落地使用朝表面外的半球方向，空爆使用向四周展开的分布；升腾保持世界向上，不随墙面法线横向“上飘”。火焰／火星的运动坐标不再跟随镜头。

火球原点光源在命中后短暂复用：放在接触点外侧 22 cm，暖橙色，启用阴影，约 9800–21000 流明峰值，240 ms 内迅速衰减。作用半径为 360–760 cm；余下时间停止 Actor Tick，原有拖尾独立结束。本轮没有增加相机震动或全屏闪白。

伤害中心仍是原投射物碰撞中心，伤害半径、遮挡判断、耗魔、冷却、经验、技能手势与存档规则不变。新增参数只是命中外观；实现继续遵守现有本地单人生命周期，不宣称联机同步。

## 方向性爆燃与热冲击波加强

用户追加要求加强这两项效果并扩大范围。调节集中在 `FPSFireballProjectile.cpp` 的 `FireballImpactVisuals`，沿用当前命中系统与材质：

- 爆燃组件视觉缩放提高到原来的 1.50 倍，火焰翻卷的运动距离和尺寸同步扩大；原有表面外向半球、空爆分布与世界向上升腾继续生效。薄烟／火星随同一组件扩大，数量与透明度不变。
- 热冲击波最大半径提高到原来的 1.65 倍，`HeatStrength` 从材质默认 0.038 改为运行时 0.060，折射强度约增加 58%。起始尺寸也按加强后的半径计算，避免首帧尺寸跳变。
- 热浪时长从 0.26 秒延长到 0.36 秒，衰减曲线由 `(1-T)^2` 调为 `(1-T)^1.35`，中段保留更明显的热扰动，末端仍淡出至零。

这些是视觉参数，未扩大技能伤害半径。保持现有发射器数量、材质深度设置、悬浮／飞行效果、短光与音频参数。本次不重制二进制资源；完整资产恢复后，运行时仍会覆盖热浪强度。

## 作者源与恢复

- 主入口：`Tools/Skills/build_fireball_impact_realistic.py`。完整 `build_fireball_assets.py` 在 fluid_burn 后调用此步骤。
- 音频源：`SourceAssets/FireballImpactRealistic20260914/author_audio.py`，从已使用的 `SourceAssets/Fireball20260914/fireball_hit.wav` 进行滤波／包络处理，加原创短压力和噪声细节。输出 `Pressure.wav`、`Combustion.wav`、`Embers.wav`、`FireballImpactLayered.wav`，分轨可继续编辑。
- 依赖：Epic Niagara Examples 爆燃 EOO／法线和发射器模板、项目已有薄烟材质、剑气同源 `Realistic_Starter_VFX_Pack_Vol2/Textures/T_NoiseNormal_A`。不修改或公开再分发第三方母版。
- 制作参数和来源：作者目录 `sources.json`、`audio-source.json`、`installation.json`。初始来源读取脚本为 `read_sources.py`。
- 新命中资源使用独立路径；旧 `NS_FireballExplosion`、`M_FireballShockwave`、`S_FireballImpact` 保留为旧阶段和生成链输入。既有悬浮／飞行资源不作视觉调整。

恢复时先恢复原始 WAV 和授权资源，再运行 `author_audio.py` 生成混音，随后在 UE 使用 `-AllowCommandletRendering` 执行命中制作入口，进行必要的实际 RHI 材质编译。含 DepthFade 的材质继续关闭 OutputTranslucentVelocity，避免再次出现棋盘格；不使用会绕过深度测试的 AfterMotionBlur。

## 本次交付边界

初版 Editor C++ 构建成功，输出模块后缀 `9141501`，日志为作者目录 `native-build-suffix.log`。首次常规链接因当前编辑器占用 DLL 失败，随后采用独立模块后缀完成构建。

范围加强版已完成必要 Editor 构建，输出模块后缀 `9141802`，最终日志 `native-build-impact-boost-nonunity.log`，退出码 0。构建期间遇到其他模块生成头文件过期、双持音效的 `TObjectPtr` 无法推导为 `auto*`、旧 Unity 编译产物重复定义 `IsReloading`；重新生成头文件，给 `PistolDualWieldCombat.cpp` 的两处 `Sounds.FindRef(...)` 加 `.Get()`，并用 `-DisableUnity` 完成构建。未修改双持玩法逻辑。已经打开的编辑器需重启工程加载本次 C++。

资源制作在 D3D12 下完成，Niagara 编译返回 `valid=1`，三份新父材质及所需实例、系统、声音和衰减资源均保存，记录 `FIREBALL_REALISTIC_IMPACT_INSTALLED`。制作进程因已打开编辑器占用本地 MCP 的 8000 端口返回 1；该条端口错误与已完成的资源保存分别记录，见 `asset-build.log`。

按用户规则，没有启动游戏、运行测试、截图、渲染预览、听觉预览或做视觉验收。最终爆燃方向、写实程度、热浪与声音力度由用户重启后体验判断；本轮结果是完成制作和接入，不是已获用户验收。
