# 火球 VFX：缓燃、尾焰与材质用途

项目特效使用已授权的 Epic Niagara Examples 和用户导入的 Dr.Game Free Spline VFX；第三方纹理、材质函数和系统留在本机。沿用 `Docs/Skills/fireball-*-20260914.md` 的来源与制作记录，不把资产发现、编译成功或用户对手臂的认可写成全套 VFX 已验收。

## 缓慢悬浮燃烧

- 当前核心 `/Game/Skills/Fireball/NS_FireballSlowBurnCore`：柔和内焰、低频翻滚与短外焰分层，降低规则球壳、亮线、环形描边与强闪烁。用寿命、随机起帧、缓慢 SubUV 和柔边形成体积，避免单个平面无限放大。
- 外层取 Free Spline VFX 的 `T_Vfx_Stamp_FireFlame_88`（8×8，黑底 RGB）。使用纹理制作短焰外壳，不搬整套样条发射器、地形吸附、烟尘和灯光。
- 材质采用正确的图集采样、预乘透明及根部／边缘软化；保留世界深度。粒子根部嵌入内焰，让接缝被遮住，不用高亮圆轮廓掩盖平面边缘。

## 飞行时尾焰沿真实速度反向

- 悬浮允许短促向上燃烧；飞行后局部 +X 与实际速度对齐，外焰位置、速度和 SpriteAlignment 一起过渡到 -X。只旋转整个 Niagara Component，不一定能改变世界空间速度或贴图朝向。
- 当前拖尾 `/Game/Skills/Fireball/NS_FireballVelocityTrail` 跟随真实投射物位移，保留世界空间轨迹；不继续叠加悬浮阶段的向上加速度。
- 当前外焰方向交接约 60 ms；接触、飞行、爆炸和脱手悬浮位置由同一个投射物／技能状态驱动，不能在手势收回时拉回球体。

## 棋盘格与制作 API 经验

- 原外焰出现棋盘格是缺少 `NiagaraSprites` 材质用途，运行时换成默认材质，不是改贴图清晰度可以解决。UE 5.8 生成脚本显式使用 `set_base_material_usage(...MATUSAGE_NIAGARA_SPRITES..., True)`；有实例用途覆盖时也保存对应 `set_material_usage_override`。重新编译并保存父材质、实例。
- Niagara CPU VectorVM 的 Custom HLSL 不支持本例使用的 `smoothstep`，按 `t=saturate((x-a)/(b-a)); t*t*(3-2*t)` 展开；不要与材质 HLSL 的可用函数混为一谈。
- 动态材质参数的 Niagara 类型使用 `Vector4f`；不要因为都是四通道就替换成 `LinearColor`。材质输入名可能本地化，用编辑 API 取得真实 pin 名。

## 重建链和归档边界

当前 `Tools/Skills/build_fireball_assets.py` 依次调用 flames → flight → slow_burn → outer_flame。后面的生成器导入前面模块的函数／常量，也可能读取其生成的基础系统。即使旧核心不再运行，生成器和中间资产仍是恢复依赖，不能一并当废案移走。

外焰可单独用 `build_fireball_outer_flame.py` 更新；已有资源仅需补用途时用 `fix_fireball_outer_material_usage.py`。材质编译属于必要制作，实机渲染属于另行授权的检查。日志分别记录脚本保存、着色器编译、进程退出与实际观感，不将启动时的已有 GameFeatureData 报错误记为成功的零错误运行。
