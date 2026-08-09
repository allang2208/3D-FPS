# 火球技能迁移记录（Phaser → Godot 4.7）

> 2026-08，`fx(fireball):` 提交序列。沉淀两段式技能实现与粒子特效的关键坑，
> 便于后续技能（寒冰/雷击等）与特效复用。同内容已沉淀到 godot-3d-dev skill 的
> `references/fireball-fx.md`。

## 技能流程

- 第一段：凝聚火球悬浮左手握持位（相机前下方偏左 `cam.basis * (-0.42, -0.24, -0.85)`，sin 浮动），30s 有效；
- 第二段：沿瞄准方向投掷，射线命中 / 到射程 → 爆炸（双层冲击波 + 三层火焰 + 四溅火星 + 烟尘 + 音效 + AOE 伤害）。
- 数据源 `ui/skills_db.gd`（伤害 = floor(damageBase + matk*magicMul + int*intMul)，AOE 距离衰减）；
  `ui/skillbar.gd` 管理两段触发（凝聚不耗 CD，投掷后进入 CD）。
- 命中判定用 `PhysicsRayQueryParameters3D`（HIT_MASK = 墙体+敌人），与视觉球体无关——
  **最终移除球体 mesh，纯粒子火焰承担全部视觉**。

## 粒子特效关键坑（实测踩过）

### 1. color_ramp 不生效 → 火焰永远是白色（最大坑）
GPUParticles3D 粒子颜色经顶点 COLOR 传材质，StandardMaterial3D 必须
`vertex_color_use_as_albedo = true`，否则粒子用材质 albedo（白色）。
火球与爆炸粒子都踩过——之前"黄色"其实是球体/光晕的颜色，不是粒子。

### 2. 粒子尺寸 = draw_pass quad × scale
quad 0.5 × scale 0.1 = 0.05m。此前 quad 0.045–0.09 × scale 0.05–0.115 =
0.003–0.01m 芝麻点。放大要动 quad（0.5–0.7）+ scale（0.3–0.8）。

### 3. Godot 4.7 ParticleProcessMaterial API
- `scale_curve`（CurveTexture）替代 3.x `scale_curve_min/max`；`CurveTexture.curve = Curve`。
- `turbulence_noise_speed` 是 Vector3。
- 发射面：`emission_shape = EMISSION_SHAPE_SPHERE` + `emission_sphere_radius` +
  `emission_shape_offset`（下移 = 火焰从球底升起；offset 0 + 大 spread = 包裹全球）。

### 4. shader EMISSION 不经过 alpha
半透明球体调 ALPHA 无效，EMISSION 仍全量发光；隐形球体必须同时降 EMISSION，或干脆不建 mesh。

### 5. ADD 叠加过曝成白团
主体火焰用 MIX（保留真实颜色），ADD 只用于火星/光晕；白热内焰少量小粒子。

### 6. RibbonTrailMesh = 竖柱
悬浮浮动时 ribbon 渲染成垂直光柱；飞行也可能拉红柱。悬浮不用 ribbon，尾迹用世界空间粒子点排布。

### 7. 火焰燃烧配方（当前火球采用）
三层（白热内焰 / 黄焰主体 turbulence 翻涌 / 橙红外焰勾边），球面发射 + UP 方向 +
scale_curve 生长（越往上越宽）+ color_ramp alpha 提前淡出（防顶部堆积成柱）+
软边圆点贴图（64px `a=(1-d)^2`）。

## 验证方法

- 语法：`--headless --check-only --script res://scripts/fireball.gd`
- 窗口渲染探针：`--script tests/probe_xxx.gd --rendering-driver opengl3`（勿 --headless）；
  PowerShell 用 `Start-Process -Wait -RedirectStandardOutput/-RedirectStandardError`
  （`&` 对 GUI 程序不等待，吞输出 + 留僵尸进程）。
- 像素分析（PIL）：白/黄/红阈值统计、按行扫描查光柱、ASCII 字符画目检；粒子动态强 → 3 帧平均。
- 主场景依赖并行线资产（枪模），纯特效验证用隔离探针（只建相机 + fireball，不加载 main.tscn）。

## 关键提交

`48dd87e`（去 RibbonTrail 红柱）、`2488b1c`（火焰燃烧三层 + 放大）、`eed6a56`（缩 30% 防光柱）、
`afdbef7`（球体改暖橙芯防红球）、`052fef5`（修 color_ramp + 火焰包球）、`9917b17`（移除球体纯火焰）、
`8db2178`（中心火芯加大）、`72a9c35`（爆炸升级四层 + 双层冲击波）。

## 冰锥 / 闪电（第二轮迁移，`064070b`）

- **冰锥（iceSpike）**：两段式——N 颗冰锥环绕相机悬浮（水平椭圆 + 垂直分层错速）→ 齐射。
  命中/撞墙 = 碎裂（冰屑带重力 + 小冰环 + 音效 90ms 节流）；到达射程静默消失。
- **闪电（lightningStrike）**：单段——锁定相机准星前方 aimRadius 内最近敌人，
  蓝紫闪电链（锯齿折线 + billboard 软点链）连接，chainRange 内传导，每跳 ×(1−chainDecay)；
  命中点蓝紫冲击波 + 白紫粒子；无目标/超距失败（不耗魔不冷却，main.gd 回滚）。
- **接线**：skills_db.effect() 扩展 spike_count / aim_radius / chain_range / chain_targets /
  chain_decay / stun_ms / electrify 等字段；main.gd 绑定 Q=火球 / E=冰锥 / X=闪电。
- **新坑**：`Camera3D.new()` 自动名是 `@Camera3D@id`（类型查找替代名字查找）；
  3D 投射物要汇聚躯干高度（0.8m）否则从敌人头顶掠过；skills_db._eval 需兼容纯数值；
  隔离探针假敌人须 StaticBody3D + CapsuleShape3D + collision_layer=2 才能被射线命中。

## 技能栏全面迁移（第三轮，`8bcc482`）

- **数据**：skills_db 公式求值换 Godot Expression（Math.floor/round/pi 替换），
  新增 `effect_raw()` 全量求值、`exp_formula/exp_rewards/sounds` 暴露；26 技能全部可解析。
- **音效**：补齐 frozn / holy-light-1 / icewall / 陨星×3 到 assets/sfx。
- **修炼**：`ui/skill_progress.gd`（命中/击杀/多杀经验 → 升级，expFormula 求值），
  技能脚本发 `cast_finished(hits, kills)`（静态 cast 用 Callable 回调），
  `skill_page.gd` 修炼列表显示 Lv + 经验条（set_progress/set_db 注入，不改 UI 线 setup 签名）。
- **技能实现**：`area_skill.gd` 配置化覆盖圣光/暴风雪/冰墙/陨星/雷暴领域/灼锋焰甲/无人机，
  `thunder_lance.gd` 贯穿雷枪（射线-线段距离贯穿，阈值 0.8）；Q/E/X/C 绑定
  火球/冰锥/闪电/暴风雪，其余可绑定/修炼。
- 验证：修炼 exp=34（3hit+1kill+multiHit 正确）、圣光命中、雷枪贯穿双杀、隔离探针全过。

## 冰锥特效复刻优化（第四轮，`3570b48`）

- 本体：原版 4 张冰锥贴图随机 billboard（Sprite3D + icearrow 系列）+ 圆柱立体芯；
- 尾迹：对齐旧版（发射率≈60ms、scale 0.9→0.1 渐小、白/冰蓝/蓝三层渐隐、寿命 0.3s）；
- 碎裂：ADD 冰屑 12 粒带重力（−7m/s²）+ 白色爆闪 + 冰环 flicker（0.55+0.45·sin(t·8π)）；
- 悬浮：环绕中心前移相机前方 0.55m（第一人称 4 颗全可见）+ 错相位 sway 浮动；
- 验证：飞行尾迹/碎裂特效 ASCII 目检达标，命中致死（hp 0）、正常收尾。

## 发射卡死修复（`212d1ad`）

- 根因：enemy.gd 血量属性是 `_hp`（私有），`c.get("hp")` 返回 Nil；
  Godot 4.7 的 `int(Nil)` 报 `Nonexistent 'int' constructor` 且每帧中断 → 发射后卡死。
- 修复：5 个技能脚本统一 `_hp_of(node)` helper（`get("_hp")` + nil 短路，`Object.get` 仅 1 参）。
- 验证：test_fireball 全过（含 fireball_hits_wolf=true）、冰锥发射链路正常（命中致死、收尾）。

## 冰锥水平悬浮修复（`700ab85`）

- 根因：billboard 模式忽略 Sprite3D 的 rotation（4.7 实测，贴图 bbox 仍 24×140 纵向），
  之前"旋转 90°"白做，冰锥贴图剪影始终垂直。
- 修复：PIL 预旋转生成 4 张横向贴图（ice_spike_h_01~04，bbox 140×24 横向），
  billboard 直接显示横置；GLM 读图 + 像素测量双重确认 4 根全水平。

## 冰锥特效 v2 升级（`c9ceac9`）

- 去重：移除圆柱 mesh，纯 billboard 横向贴图（原版 2D 精灵还原），消除"贴图+模型"重复；
- 悬浮：前方扇形松散分布（x/y/z 三轴错开 + 每颗独立相位频率），
  各自上下/左右/前后 sin 浮动（0.03~0.05m），替代死板椭圆转圈；
- 验证：像素 bbox 宽>高（横向）、GLM 确认"4 根水平扇形散开无重复轮廓"、
  两帧中心位移确认浮动生效。

## 冰锥特效 v3（`545a73c`）

- 尖端朝瞄准：billboard 贴图无法表达尖端方向（永远面向相机），改 3D 锥体
  （CylinderMesh 收缩横置 + 发光），look_at 瞄准点 → 尖端直对瞄准方向；
- 平行投掷：发射 dir = 瞄准方向（含俯仰），4 根同向平行飞（不再汇聚一点），
  发射前 y 对齐 0.8m 躯干高度避免掠过敌人；
- 验证：fly dir 全一致、命中致死、悬浮尖端朝前。

## 冰锥 v4/v5（`77977c9` + `c7a4381`）

- 追踪：飞行每帧 raycast 准星瞄准点，冰锥方向实时指向（近距离精准命中）；
- 寒气：大光雾（billboard 软点）+ 柔和蓝白尾迹（去颗粒/边角/粒子感）；
- 碎裂 100% 迁移：12 粒白/浅蓝/蓝冰片（1.4~4.5m/s 带重力渐小渐隐）
  + 0.98m 双层冰环（浅蓝描边+填充圆盘、320ms flicker）+ 白闪。

## 冰锥打不中修复（`937f4fc` + `0c6c836`）

- HUD 桥接未就绪防护（main 技能触发判空，防 Nil 崩溃）；
- 准星 15° 锥形内锁定最近敌人（不依赖 raycast 命中，矮/偏移敌人也能追踪）；
- 瞄准点偏移降到躯干中部 +0.3（避免与冰锥 0.8m 发射高度同高擦过胶囊顶端）。
