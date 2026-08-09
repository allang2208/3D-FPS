# 无尽轮回 3D FPS（Godot 4.7）

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
  assets/ui/shaders/panel_blur.gdshader  # 面板毛玻璃背景（复刻旧版 backdrop-filter blur）
  assets/data/equipment.json             # 旧版装备数据（整份迁移，图标重映射到 ui/icons/equip）
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

## 当前状态与下一步

- 可玩闭环：三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）、玩家 100 血、接触伤害、死亡按 R 重生、
  弹药 30/90 + 换弹、飞行弹道（可见子弹 + 下坠 + 火花）、命中反馈、击杀计数。
- 背包栏（UI 迁移线）：底部快捷栏 1~4 + Tab/B 背包面板（36 格），治疗药水回血、拖拽绑定/交换、
  右键使用；已复刻旧版弹出效果（面板滑入+毛玻璃、equipPop、数字键闪烁、0 数量抖动、冷却遮罩、
  拖拽/悬停高亮、物品浮窗、背包满提示）；配色/字体集中在 ui/style.gd，后续按情绪板换肤只改这一处。
  装备与背包面板按旧版 system-panel：右侧贴边滑入（translateX 0.25s）、56% 屏宽、全高、毛玻璃。
  装备栏（15 槽）已迁移：竖排稀有度、已强化/改造/附魔徽章、双手武器锁定、拖放装备/卸下；
  物品浮窗为旧版三段式（主信息+改造+附魔）。排版按 DESIGN.md：黑体（思源黑体→雅黑回退）、
  字号阶梯（24 标题/14 正文/10~12 角标）、4px 间距网格、数值右对齐。MP 系统未实装，魔力药水暂不发放。
- 敌人仍是整体平移 + 占位起伏/摆腿；下一步把 three.js 里的程序化骨骼动画（18 根骨骼 + 蒙皮权重）
  移植成 Godot 的 Skeleton3D + AnimationPlayer，或接 Godot 4.6+ 的 IKModifier3D 做真正的四足步态。
- 后续内容：更多武器、掉落/计分、更多敌人类型（抽象敌人走物体级动画）、地图扩充。
