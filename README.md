# 无尽轮回 3D FPS（Godot 4.7）

从 three.js 原型迁移到 Godot 的 3D FPS 工程，资产沿用 AI 管线（AI 生图 → TRELLIS.2 → GLB）。

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

WASD 移动 · 鼠标视角 · 空格跳 · Shift 疾跑 · 左键射击（飞行弹道 + 下坠 + 命中火花 + 受击闪红）· R 换弹 · Esc 释放鼠标 · 死亡按 R 重来

## 结构

```
3-dfps/
  project.godot     # 项目配置（Godot 4.7 / Forward Plus / Jolt）
  scenes/main.tscn  # 主场景入口（场景由 main.gd 代码搭建）
  scripts/
    main.gd         # 环境/光照/地面/墙体/玩家/黑狼 GLB
    player.gd       # 第一人称控制器 + 血量/受伤/死亡
    gun.gd          # AKM：弹药 30/90 + R 换弹 + 散布(bloom) + 枪口闪光
    projectile.gd   # 标准弹道飞行：90m/s、轻微下坠、逐帧扫描防穿墙、命中火花
    impact_fx.gd    # 命中火花粒子
    enemy.gd        # 通用敌人 AI：追击/游荡/接触伤害/死亡重生
    enemy_models.gd # 代码拼装：僵尸犬 / 蜘蛛
  assets/models/
    black_wolf_trellis.glb  # TRELLIS.2 生成的 PBR 黑狼
```

## 当前状态与下一步

- 可玩闭环：三只敌人（黑狼 GLB + 僵尸犬 + 蜘蛛）、玩家 100 血、接触伤害、死亡按 R 重生、
  弹药 30/90 + 换弹、飞行弹道（可见子弹 + 下坠 + 火花）、命中反馈、击杀计数。
- 敌人仍是整体平移 + 占位起伏/摆腿；下一步把 three.js 里的程序化骨骼动画（18 根骨骼 + 蒙皮权重）
  移植成 Godot 的 Skeleton3D + AnimationPlayer，或接 Godot 4.6+ 的 IKModifier3D 做真正的四足步态。
- 后续内容：更多武器、掉落/计分、更多敌人类型（抽象敌人走物体级动画）、地图扩充。
