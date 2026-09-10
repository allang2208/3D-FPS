# 无尽轮回 3D FPS（后续开发转 UE5）

**2026-09-10 起，后续开发以 Unreal Engine 5 为主。** 当前本地工程为 `D:/FPS3D/FPSGAME/FPSGAME.uproject`（UE 5.8.2）。新功能、天气、场景与武器迁移使用对应 UE5 技能。

根目录保留 Godot 原型和历史；[unreal/](unreal/README.md) 保存已发布的 UE5 源码与验证快照，尚不包含完整可独立运行的 UE 工程和受许可限制的美术资源。下方 Godot 操作说明用于维护旧原型。

从 three.js 原型迁移到 Godot 的 3D FPS 工程，资产沿用 AI 管线（AI 生图 → TRELLIS.2 → GLB）。

并行开发约定（动画线 / UI 迁移线）见 [WORKFLOW.md](WORKFLOW.md)。

## 打开与运行

Godot 编辑器（便携版）：`E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe`
选择“导入”，打开本目录的 `project.godot`，按 F5 运行。

无头命令（CI/自动验证用）：

```powershell
# 重新导入资源（新 GLB 放进来后跑一次）
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --import
# 跑 120 帧检查脚本错误
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --quit-after 120
# 行为冒烟：黑狼 AI 移动 + 射击扣血（tests/test_combat.gd）
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_combat.gd
```

## 操作

WASD 移动 · 鼠标视角 · 空格跳 · Shift 疾跑 · 左键射击（飞行弹道 + 下坠 + 命中火花 + 受击闪红）· 右键长按机瞄 · 空仓自动换弹 / R 手动换弹 · 1~4 使用快捷栏 · Tab/B 背包面板 · Esc 释放鼠标 · 死亡按 R 重来

## 结构

```
3-dfps/
  project.godot     # 项目配置（Godot 4.7 / Forward Plus / Jolt）
  scenes/main.tscn  # 主场景入口（场景由 main.gd 代码搭建）
  scripts/
    main.gd         # 环境/光照/地面/墙体/玩家/黑狼 GLB；HUD 部分转发信号到 ui/status_bar.gd
    player.gd       # 第一人称控制器 + 血量/受伤/死亡
    gun.gd          # AKM：ADS 机瞄 + 换弹动画（弹匣滑出）+ 弹簧后坐 + 姿态（bob/sway/疾跑）+ 弹壳/烟雾 + 枪声分层/击杀反馈
    casing.gd       # 弹壳抛壳（重力/旋转/落地弹跳）
    camera_fx.gd    # 相机反馈：视角后坐弹簧 + FOV 指数平滑/机瞄变焦 + Trauma/Perlin 抖动
    projectile.gd   # 标准弹道飞行：90m/s、轻微下坠、逐帧扫描防穿墙、命中火花
    impact_fx.gd    # 命中火花粒子
    enemy.gd        # 通用敌人 AI：追击/游荡/接触伤害/死亡重生
    enemy_models.gd # 代码拼装：僵尸犬 / 蜘蛛
  assets/models/
    black_wolf_trellis.glb  # TRELLIS.2 生成的 PBR 黑狼
  ui/
    status_bar.gd   # 状态栏（UI 迁移线）：生命条/弹药/击杀/换弹状态/命中/死亡面板
    style.gd        # UI 风格集中定义（配色/字体/稀有度；换肤只改这里）
    backpack.gd     # 背包数据模型：36 格 + 快捷栏 1~4 绑定（堆叠/实例绑定/名称回退）
    equipment.gd    # 装备栏数据模型：15 槽 + 武器槽规则（单手/双手/盾/锁定）
    backpack_hud.gd # 背包/装备 UI：快捷栏 + 装备与背包面板（竖排稀有度/徽章/锁定）+ 弹出动画
    item_tooltip.gd # 物品浮窗三段式（主信息+改造+附魔）：悬停跟随/点击固定/贴边翻转
    item_db.gd      # 物品库：药水 + 加载 assets/data/equipment.json（125 件装备）
    player_status.gd# 角色属性数据模型（旧版 combat-formulas 公式：六维/战斗属性/上限）
    status_page.gd  # 角色状态页：角色头+4 状态条+基础/战斗/详细/轮回四区块+公式悬停浮窗
    skillbar.gd     # 快捷栏技能绑定数据层：唯一性换位/冷却/法杖门槛/长按标记/特殊攻击槽
    skills_db.gd    # 技能库（data/skills.json）：等级公式求值（火球先迁）
  scripts/fireball.gd # 火球：朝瞄准方向飞行 + 范围爆炸 AOE（旧版公式/距离衰减）
  assets/ui/shaders/panel_blur.gdshader  # 面板毛玻璃背景（复刻旧版 backdrop-filter blur）
  assets/data/equipment.json             # 旧版装备数据（整份迁移，图标重映射到 ui/icons/equip）
  assets/ui/icons/equip|skills|icons     # 旧版装备/武器/物品/技能图片全量移植（327 张，压到 128px）
```

## 状态栏（HUD）测试

```powershell
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_status_bar.gd
```

覆盖：初始血量/弹药、受伤扣血 + 红闪、弹药/换弹提示、命中标记、击杀计数、死亡面板。

## 背包栏（Backpack）测试

```powershell
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_backpack.gd
```

覆盖：堆叠/满包拒绝、药水回血 + 状态栏更新、快捷栏绑定/实例回退、信号（item_added/bound）、
冷却拦截与恢复、面板开关、浮窗显示/毛玻璃背景、拖拽绑定/交换/解绑、背包已满提示。

## 装备栏（Equip）测试

```powershell
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_equip.gd
```

覆盖：装备/卸下/交换、武器槽规则（单手→主手/副手、双手→主手并卸副手、盾）、双手锁定、
拖放装备、右键卸下、装备浮窗（名称/稀有度/属性）。

## 属性栏（Status）测试

```powershell
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_status_page.gd
```

覆盖：旧版公式（六维→物攻/物防/魔攻/魔防/暴击/上限）、状态页签切换、公式悬停浮窗、hp/击杀同步。

## 技能栏（Skillbar）测试

```powershell
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_skillbar.gd
```

覆盖：技能绑定唯一性/换位/解绑、冷却拦截与遮罩、法杖门槛灰化、长按标记、特殊攻击槽。

## 火球（Fireball）测试

```powershell
& 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe' --headless --path 'E:\3d\3-dfps' --script res://tests/test_fireball.gd
```

覆盖：skills.json 公式求值、Q 键触发、MP 扣除、冷却、火球生成与伤害计算。

## 当前状态与下一步

- 可玩闭环：三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）、玩家 100 血、接触伤害、死亡按 R 重生、
  弹药 30/90 + 换弹、飞行弹道（可见子弹 + 下坠 + 火花）、命中反馈、击杀计数。
- 武器手感（移植自 Unity FPS 参考）：部位伤害（狼头 Hitbox ×2，金色命中火花 + 爆头击杀音调）、
  弹道后坐力 pattern（连发固定序列 + 停火回退）、移动/空中扩散惩罚、冲刺开火延迟、
  贴墙 2m 内子弹从相机出（防弹道被墙面吞掉）。
- 背包栏（UI 迁移线）：底部快捷栏 1~4 + Tab/B 背包面板（36 格），治疗药水回血、拖拽绑定/交换、
  右键使用；已复刻旧版弹出效果（面板滑入+毛玻璃、equipPop、数字键闪烁、0 数量抖动、冷却遮罩、
  拖拽/悬停高亮、物品浮窗、背包满提示）；配色/字体集中在 ui/style.gd，后续按情绪板换肤只改这一处。
  标准分辨率 1920x1080。装备与背包面板按旧版 system-panel：右侧贴边滑入（translateX 0.25s）、
  45% 屏宽、全高、毛玻璃；排版按旧版 gear-layout 上下分栏——上装备栏 3x5 大宽格、下背包 5 列小方格
  （表头 背包+0/36）。装备栏（15 槽）已迁移：竖排稀有度、已强化/改造/附魔徽章、双手武器锁定、拖放装备/卸下；
  物品浮窗为旧版三段式（主信息+改造+附魔）。配色已按旧版精确移植（暗金棕槽/白底浮窗/红棕血条/
  蓝灰面板），集中在 style.gd。属性栏已迁移：面板页签（角色状态/装备背包，CapsLock/Tab）+ 角色头
  + 生命/魔法/体力/经验条 + 基础/战斗/详细/轮回四区块 + 公式悬停浮窗。技能栏互动已迁移（技能本体未移植）：
  Q/E/X/C 技能槽（绑定唯一性/换位、拖出解绑、冷却遮罩+秒数+白闪、中级魔法法杖门槛灰化、长按标记、
  特殊攻击槽数据位），物品侧 1~4 保持。技能迁徙从火球开始：Q 默认绑定，朝瞄准方向飞行、
  命中/到射程范围爆炸 AOE（伤害=80+10Lv+魔攻×(2+0.5Lv)+智力×(2.5+0.75Lv)，20s 冷却、50 MP）。排版按 DESIGN.md：黑体（思源黑体→雅黑回退）、
  字号阶梯（24 标题/14 正文/10~12 角标）、4px 间距网格、数值右对齐。MP 系统未实装，魔力药水暂不发放。
- 敌人仍是整体平移 + 占位起伏/摆腿；下一步把 three.js 里的程序化骨骼动画（18 根骨骼 + 蒙皮权重）
  移植成 Godot 的 Skeleton3D + AnimationPlayer，或接 Godot 4.6+ 的 IKModifier3D 做真正的四足步态。
- 后续内容：更多武器、掉落/计分、更多敌人类型（抽象敌人走物体级动画）、地图扩充。
