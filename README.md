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

WASD 移动 · 鼠标视角 · 空格跳 · Shift 疾跑 · 左键射击（射线命中 + 枪口闪光 + 曳光 + 受击闪红）· Esc 释放鼠标

## 结构

```
3-dfps/
  project.godot     # 项目配置（Godot 4.7 / Forward Plus / Jolt）
  scenes/main.tscn  # 主场景入口（场景由 main.gd 代码搭建）
  scripts/
    main.gd         # 环境/光照/地面/墙体/玩家/黑狼 GLB
    player.gd       # 第一人称控制器
    gun.gd          # 程序化拼装枪械 + 射线射击/闪光/曳光
    wolf_enemy.gd   # 黑狼 AI：追击/游荡/受击扣血/死亡重生
  assets/models/
    black_wolf_trellis.glb  # TRELLIS.2 生成的 PBR 黑狼
```

## 当前状态与下一步

- 黑狼有基础 AI（14m 内追击、远处游荡、3 秒重生）与受击反馈，但仍是整体平移 + 占位起伏；
  下一步把 three.js 里的程序化骨骼动画（18 根骨骼 + 蒙皮权重）移植成 Godot 的 Skeleton3D + AnimationPlayer，
  或接 Godot 4.6+ 的 IKModifier3D 做真正的四足步态。
- 玩家暂无生命值/死亡判定，HUD 只有准星与黑狼血条；后续按 three.js 原型的里程碑补齐。
