# 火系特效 Realistic V5 · 2026-09-22

用户不满意火把和 Free Spline VFX 两版表现，在盘点本地其他素材后授权采用建议方案。本轮改用 Realistic Starter VFX Pack Vol.2 和 Military Trench 的原生火焰材质与序列，保持当前写实岩体、施法手势及技能数值。

## 原素材依据与适配

通过 UE ObjectExporterT3D 读取原 Cascade 系统的 LOD0 发射器、寿命、颜色、动态参数与 SubUV 设置，同时读取材质实际连接。原始导出和精简参数保存在 `SourceAssets/FireMagicRealistic20260922`。没有播放预览或运行比较。

| 选用素材 | 实际输入 | 本轮用途 |
| --- | --- | --- |
| Realistic `P_Fire_Small` / `M_Fire_B` | `T_Fire_D`，8×4 序列、ParticleColor、DepthFade | 刀刃小火、脚边火环及地面低火 |
| Realistic `P_Fire_Small`、`P_flamethrower`、`P_Molotov` / `M_Fire_C` | `T_Fire_F` 6×6 序列与 `T_Fire_B` 遮罩；动态 X 为遮罩偏移、Y 为透明度指数 | 武器翻卷余焰、陨星喷流尾焰、落地上卷火与持续火场 |
| Military Trench `P_Fire` / `M_Fire_SubUV` | 6×6 `T_Fire_SubUV` 与 `T_Fire_Tiled_D`；0.7～1 秒原寿命、0～35 帧播放 | 陨石包覆火和尾焰分离层 |
| Realistic `P_Explosion_Big_A` / `M_Explosion_B` | 12×12 序列、颜色与 packed 纹理，动态 X 为 Glow | 落地爆燃 |
| Realistic `M_Smoke_C` | 8×8 烟雾序列及原混合材质 | 少量尾烟和落地烟气 |

原系统为 Cascade；本轮在独立 Niagara 系统内适配武器端点、世界空间飞行轨迹、范围和结束参数。材质完整复制原图，保留原纹理解码、透明度和遮罩，不再使用 Spline 的统一 8×8 火焰材质。按源图集尺寸配置渲染器；每个粒子随寿命播放一次序列，由错开的出生时间形成变化。

火焰发光补入 `EyeAdaptationInverse`，防止再次被场景曝光压黑。源系统中数百至百万级的 HDR 颜色/Glow 参数按本项目曝光重新调整，保留暖色主题与烟火层次；动态材质参数使用原语义。武器与陨星贴体火降低数量和尺寸，烟气采用较低密度/透明度，减少对刀刃和写实岩体的遮挡。

## 运行资产

目录 `/Game/Skills/FireMagic20260921/RealisticV5`，共五个材质、六个 Niagara 系统：

- `NS_ArmorNaturalFire`：24/s 小火、10/s 翻卷附焰、13/s 世界空间挥动余焰，继续使用实际刀刃/枪口端点。
- `NS_ArmorNaturalAura`：低矮脚边火环。
- `NS_MeteorNaturalMantle`：Military Trench 包覆火，每秒 24 个，贴近岩体并向飞行反方向抬升。
- `NS_MeteorNaturalWake`：Realistic 尾焰、少量 Trench 火舌和轻烟，沿上一帧到当前帧的位置生成，保留轻微扰动和阻力。
- `NS_MeteorNaturalImpact`：3 个原版爆燃序列粒子，0.065 秒后接燃烧瓶来源火舌，0.16 秒后接烟气。
- `NS_MeteorNaturalAfterfire`：Realistic 小火与燃烧瓶来源火舌构成持续火场，保留半径、扩散和结束淡出。

`FPSFireMagicComponent.cpp` 的运行/预载路径与 `FPSMeteorStrike.cpp` 的实际加载路径已切到 V5。RealisticV3 岩体与碎片、0.65 秒坠落、全部伤害/修炼/冷却、六边图标和手势继续使用既有设置。

作者 `Tools/Skills/build_fire_magic_realistic.py`，通过 MCP 桥逐阶段执行 `materials → weapon → aura → mantle → trail → ground → impact`。材质、系统均已编译保存；恢复需要已许可的 Realistic Vol.2、MilitaryTrench、原火系作者链与 Niagara 模板依赖。V4 系统作为构建容器来源保留，创建 V5 后删除其所有发射器，再构建新层；运行火焰不引用 Spline 的图集或材质。

## 构建与交付边界

两处 C++ 引用改动已完成常规 `FPSGAMEEditor Win64 Development` 构建，返回 `Succeeded`，日志 `SourceAssets/FireMagicRealistic20260922/editor-build-01.log`。当前编辑器启动时间晚于该次基础 DLL 更新，无需依赖 Live Coding。接入期间结束了一次正在运行的 PIE，以完成编辑器资产写入；没有新启动游戏、截图、预览或验收测试。效果仍由用户实机判断。

第三方原始素材、T3D 导出、UE 资产及读取的完整源参数保留本机，不作为公开再分发资源。
