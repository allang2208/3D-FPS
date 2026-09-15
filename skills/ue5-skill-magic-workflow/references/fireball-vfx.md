# 火球 VFX：缓燃、尾焰与材质用途

2026-09-15 实际伤害半径已按用户要求匹配现有热浪，并统一等级成长算法，见 [火球数值优化](fireball-balance.md)。当前热浪直接使用施法快照的实际半径；爆焰、烟雾、火星与暖光共用 `Radius / 210.375` 的空间缩放。一级外观保留，后续随实际范围同比成长；不再保留独立视觉半径，也不能重复乘本文历史阶段的 1.65。

项目特效使用已授权的 Epic Niagara Examples 和用户导入的 Dr.Game Free Spline VFX；第三方纹理、材质函数和系统留在本机。沿用 `Docs/Skills/fireball-*-20260914.md` 的来源与制作记录，不把资产发现、编译成功或用户对手臂的认可写成全套 VFX 已验收。

## 缓慢悬浮燃烧

- 2026-09-14 后续用户要求更写实的一团燃烧火焰，已采用原创 Mantaflow 流体烘焙主序列。运行路径仍为 `NS_FireballSlowBurnCore`，内部改为两个视角的 64 帧 RGBA 燃烧层、短外焰、薄烟和轻微热扰动。新来源为 `SourceAssets/FireballFluidBurn20260914`，接入脚本 `Tools/Skills/build_fireball_fluid_burn.py`；具体制作与未测试边界见项目 `Docs/Skills/fireball-fluid-burn-20260914.md`。下列旧缓燃素材保留为重建依赖，不再是最终主体图源。

- 当前核心 `/Game/Skills/Fireball/NS_FireballSlowBurnCore`：柔和内焰、低频翻滚与短外焰分层，降低规则球壳、亮线、环形描边与强闪烁。用寿命、随机起帧、缓慢 SubUV 和柔边形成体积，避免单个平面无限放大。
- 外层取 Free Spline VFX 的 `T_Vfx_Stamp_FireFlame_88`（8×8，黑底 RGB）。使用纹理制作短焰外壳，不搬整套样条发射器、地形吸附、烟尘和灯光。
- 材质采用正确的图集采样、预乘透明及根部／边缘软化；保留世界深度。粒子根部嵌入内焰，让接缝被遮住，不用高亮圆轮廓掩盖平面边缘。

## 飞行时尾焰沿真实速度反向

- 悬浮允许短促向上燃烧；飞行后局部 +X 与实际速度对齐，外焰位置、速度和 SpriteAlignment 一起过渡到 -X。只旋转整个 Niagara Component，不一定能改变世界空间速度或贴图朝向。
- 当前拖尾 `/Game/Skills/Fireball/NS_FireballVelocityTrail` 跟随真实投射物位移，保留世界空间轨迹；不继续叠加悬浮阶段的向上加速度。
- 当前外焰方向交接约 60 ms；接触、飞行、爆炸和脱手悬浮位置由同一个投射物／技能状态驱动，不能在手势收回时拉回球体。

## 棋盘格与制作 API 经验

- 2026-09-15 命中范围成长：局部空间组件变换会缩放粒子位置，但 Niagara SpriteSize 以世界尺寸提供给渲染器，不能假设它随组件自动放大。现在四层命中的 SpriteSize 显式乘 `1 + User.ImpactGrowth`，运行时传入 `实际半径 / 210.375 - 1`；组件位置只缩放一次。用 `update_fireball_impact_growth.py` 增量制作现有系统，完整命中生成器也保留该参数。

- 2026-09-14 镜头残影调整：主体／短外焰／薄烟使用 AfterDOF，Niagara Renderer 显式 Precise；ResponsiveAA 是 TAA 兼容项，不能单独当作 TSR 修复。含 SceneDepth／DepthFade 的材质禁止同时开启 Output Translucent Velocity，否则当前 UE 5.8 SM6 编译失败并显示棋盘格；实际已关闭该输出，保留深度淡化。NullRHI 制作成功及 Niagara valid=1 不能代表 SM6 材质成功，相关标记改动需进行真实 RHI 的必要编译。UE 5.8 的 AfterMotionBlur 会禁用深度测试，不将其作为默认消残影捷径；残影改善未获视觉验收。
- 悬浮外围 `FireballHoverHeatHalo` 参考现用剑气 `WristRiftV3/M_RuneRift`，复用 `T_NoiseNormal_A` 与 IOR 折射，新建柔边环状遮罩；约 60×68 cm、HeatStrength 0.035，沿现有 Flight/FlightAge 在发射后 0.04–0.22 s 淡出。热浪不写速度，不遮盖中心燃烧；增量入口 `tune_fireball_motion_heat.py`，完整 fluid_burn 同步。
- 流体主体与外焰须保留 EyeAdaptationInverse 曝光补偿，透明度在最终 DepthFade 后预乘；从 NE_Core 克隆时清空旧爆炸 CutoutTexture，避免有色火焰被曝光压黑或被错误多边形裁剪。

- 原外焰出现棋盘格是缺少 `NiagaraSprites` 材质用途，运行时换成默认材质，不是改贴图清晰度可以解决。UE 5.8 生成脚本显式使用 `set_base_material_usage(...MATUSAGE_NIAGARA_SPRITES..., True)`；有实例用途覆盖时也保存对应 `set_material_usage_override`。重新编译并保存父材质、实例。
- Niagara CPU VectorVM 的 Custom HLSL 不支持本例使用的 `smoothstep`，按 `t=saturate((x-a)/(b-a)); t*t*(3-2*t)` 展开；不要与材质 HLSL 的可用函数混为一谈。
- 动态材质参数的 Niagara 类型使用 `Vector4f`；不要因为都是四通道就替换成 `LinearColor`。材质输入名可能本地化，用编辑 API 取得真实 pin 名。

## 重建链和归档边界

2026-09-14 用户确认悬浮／飞行火球基本合格后，命中升级到 `/Game/Skills/Fireball/ImpactRealistic20260914`：非循环 `T_Explosion_EOO` 爆燃，按真实命中点、法线和世界上方向展开；激活前覆盖 SurfaceHit／LocalUp，保持池复用正确。原彩色圆环替换为热折射波，实体用平面、空爆用球壳；0.24 秒短暖光和分层声音同步接触。随后按用户要求加强范围：运行时爆燃缩放乘 1.50、热浪半径乘 1.65，HeatStrength 覆盖为 0.060，热浪时长 0.36 秒、衰减指数 1.35；调节入口为 `FPSFireballProjectile.cpp` 的 `FireballImpactVisuals`。作者入口 `build_fireball_impact_realistic.py`，来源和未测试范围见项目 `Docs/Skills/fireball-realistic-impact-20260914.md`。保留原技能结算中心与数值；焦痕和表面类型分支未在本阶段接入。新命中尚未获用户视觉验收。

当前 `Tools/Skills/build_fireball_assets.py` 依次调用 flames → flight → slow_burn → outer_flame。后面的生成器导入前面模块的函数／常量，也可能读取其生成的基础系统。即使旧核心不再运行，生成器和中间资产仍是恢复依赖，不能一并当废案移走。

当前完整重建在上述链条末尾追加 fluid_burn；先恢复其两张原创燃烧 RGBA 图集，或执行离线模拟和图集烘焙再导入。透明度与发光分开存储，在最终深度淡化后预乘；循环混合使用预乘线性颜色，避免交接暗边。离线资产烘焙是制作，不能写成已进行游戏视觉验收。

最新完整链在 fluid_burn 之后调用 impact_realistic；先恢复命中混音 WAV 或执行 `SourceAssets/FireballImpactRealistic20260914/author_audio.py`。音效是现有源的再制作与原创 DSP 混合，不能称为现场录制资产。原爆炸／冲击波和生成器保留为历史恢复依赖。

外焰可单独用 `build_fireball_outer_flame.py` 更新；已有资源仅需补用途时用 `fix_fireball_outer_material_usage.py`。材质编译属于必要制作，实机渲染属于另行授权的检查。日志分别记录脚本保存、着色器编译、进程退出与实际观感，不将启动时的已有 GameFeatureData 报错误记为成功的零错误运行。
