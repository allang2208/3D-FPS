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
```

## 操作

WASD 移动 · 鼠标视角 · 空格跳 · Shift 疾跑 · 左键开火（枪口后坐占位动画）· Esc 释放鼠标

## 结构

```
3-dfps/
  project.godot     # 项目配置（Godot 4.7 / Forward Plus / Jolt）
  scenes/main.tscn  # 主场景入口（场景由 main.gd 代码搭建）
  scripts/
    main.gd         # 环境/光照/地面/墙体/玩家/黑狼 GLB
    player.gd       # 第一人称控制器
    gun.gd          # 程序化拼装枪械 + 后坐
  assets/models/
    black_wolf_trellis.glb  # TRELLIS.2 生成的 PBR 黑狼
```

## 当前状态与下一步

- 黑狼是静态 GLB，目前只有占位起伏动画；下一步把 three.js 里的程序化骨骼动画（18 根骨骼 + 蒙皮权重）移植成 Godot 的 Skeleton3D + AnimationPlayer，或接 Godot 4.6+ 的 IKModifier3D。
- 暂无敌人 AI / 伤害 / UI，按 three.js 原型的里程碑补齐。
