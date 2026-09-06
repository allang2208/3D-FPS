# 普通僵尸接入记录

## 2026-09-06 Low Poly V02（当前模型）

正式模型升级为 `assets/models/modern_zombie/modern_zombie_v02.glb`，并同步矿工、狂奔变体。按用户反馈保留原有简洁脸部，不新增眼球或牙齿；改善身体与关节曲面、衣服边缘及材质。普通僵尸 8572 三角面，31 骨；逐条核对全部 16 段动画采样与 V01 相同，玩法数值和时间合同保持不变。见 [Low Poly V02 制作与验证](../tools/ai-gen/humanoid-detail-v02-20260906/README.md)。

## 2026-09-06 现代僵尸 V01（动作与数值合同）

V01 阶段正式场景曾使用 `assets/models/modern_zombie/modern_zombie_v01.glb`（现由 V02 替代，V01 对照保存在制作目录）：Denys Almaral 的现代男性僵尸及作者原生动作，补充 Quaternius UAL 倒地与受击。统一低饱和尸肤、旧衣与干血材质；31 骨骼、1724 三角形、单个 2K PBR 材质。

主场景及副本普通僵尸继承 `modern_zombie.gd`，左右攻击交替播放，每段 1.567 秒、有效窗口 0.60–0.77 秒；跛行 2 秒并按实际速度推进；倒地 2.4 秒、保尸 1 秒。伤害、生命、追击速度与冷却不变。适配头部弱点锚点和躯干胶囊，修正原跛行片段循环末端。HitReact 与跑步片段仅作为资产备用。

制作源、来源授权、完整动作 GIF、验证与新时序见 [现代僵尸 V01](../tools/ai-gen/modern-zombie-v01-20260906/README.md)。以下旧记录保留作历史，不代表当前模型和时序。

## 2026-09-06 动作 V02

正式场景已切换 `assets/models/ordinary_zombie/zombie_v02.glb`。本轮参考原二维完整动作，优化攻击、移动、死亡及 0.1 秒显示姿态过渡；保留原数值、时长、命中窗口、冷却和保尸合同。制作源、重新导入后的 GIF 与报告见 [V02](../tools/ai-gen/zombie-motion-v02-20260906/README.md)，复用原则见 [人形动作连续性](../skills/godot-monster-workflow/references/humanoid-motion.md)。以下 V01 记录保留作来源历史。

V02 修复中间关键帧反复停速、躯干同步转动、摆腿接缝速度不连续，以及根骨局部轴导致的错误贴地修正。22 项僵尸行为与 6 项姿态连续性检查通过；主场景追击约 1.21m 并保持落地，默认 D3D12 Forward+（本机 GTX 750 Ti）完成四姿态渲染。无头烟测、战斗与换弹回归退出码 0；战斗脚本的 ADS crosshair 检查显示 status_bar_missing 而跳过。编辑器导入退出时报告资源/RID 清理提示，相关运行测试无脚本错误。完整手动战斗试玩与自然度最终评价待用户反馈。

无头主场景仍输出 Dummy renderer 的 `Parameter "material" is null`；旧 `zombie-publish-smoke.log` 已有同一调用点。不能把退出码 0 写成完全无引擎错误；本轮默认渲染器截图及专用僵尸测试未出现该错误。

2026-09-06，用户批准四段动画后授权接入和测试。主场景 `_build_enemies()` 在 (-3, 0, -4) 生成 `scenes/enemies/ordinary_zombie.tscn`，连接现有玩家及击杀回调。

## 数值

等级 3，生命 120，基础近战伤害 13，物防 25；物理伤害按 floor(d × 60 / 85)，至少 1，再交给现有 BuffSystem。元素伤害不套物防。追击速度 0.61 米/秒，警戒 14 米，起手距离 1.25 米，命中纵深 1.4 米、半宽 0.48 米。距离与速度是三维场景标定值，不直接照搬二维像素。

## 状态与动画

IDLE → CHASE → WINDUP → STRIKE → RECOVER，控制打断进入 STUNNED，死亡进入 DYING → CORPSE → 移除。攻击起手锁定方向与目标，前摇期间允许侧移躲避；射线检查墙体遮挡，单次攻击最多造成一次伤害。

Idle 4.8 秒；Walk 2.25 秒，按实际水平位移速度 / 0.305 推进动画，正常追击约 2 倍速。Attack 1 秒，有效窗口 0.333333–0.458333 秒（原接触姿态 0.375 秒），起手间隔至少 2 秒。Death 单播 2 秒，终帧保留 1 秒后移除。死亡取消攻击、关闭碰撞、仅通知一次击杀；头部碰撞随骨架移动。

## 资产与制作来源

正式资源 `assets/models/ordinary_zombie/zombie_v01.glb`。源文件及参考记录在 `E:/无尽轮回/3d/3-dfps/tools/ai-gen/zombie-3d-v01-20260905`；来自 game-dev 普通僵尸 v2 四段二维动画。内置 image_gen 补 A 姿，用户自有 TRELLIS.2 生成网格，再通过 Blender 脚本建立骨骼、蒙皮和关键帧；不是视频自动动作捕捉。头面与手指仍是样板精度。

## 验证

- Godot 4.7.1 无头导入和主场景 120 帧烟测完成。
- `tests/test_ordinary_zombie.gd`：22 项通过，覆盖动作加载、前摇、命中去重、冷却、侧移/背后躲避、墙体、眩晕、低帧跨窗口、护甲、追击、死亡保尸及移除。
- `tests/render_ordinary_zombie.gd`：实际主场景物理追击 120 帧约 1.21 米且处于 Walk；渲染四段姿态，默认 D3D12 Forward+ 和 OpenGL Compatibility 均退出码 0，无脚本错误。
- 关键帧目检确认贴图、蒙皮、落地和死亡姿态；追击同时检查高度，确保角色没有穿过地板。两种渲染器截图均保留。

日志和截图位于素材目录 `runtime-tests`。以上包含自动化运行和关键帧目检，未代替玩家完整手动战斗试玩。
