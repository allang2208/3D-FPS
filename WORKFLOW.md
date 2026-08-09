# 并行开发工作流（动画线 ↔ UI 迁移线）

本仓库同时有两条开发线：
- **动画线**：3D 敌人动画 / 弹道手感 / 模型调优
- **UI 线**：把 2D 像素 UI 迁到 Godot（HUD / 菜单 / 背包等）

两条线**可以并行**，靠“文件所有权 + 谁先改谁提交”避免冲突，**不建 git 分支**。
两个会话共享同一个工作目录，互相能立刻看到改动——所以所有权就是防冲突的第一道墙。

## 1. 文件所有权

| 文件 / 目录 | 动画线 | UI 线 |
|---|---|---|
| `scripts/enemy.gd`、`enemy_models.gd` | ✅ | ❌ |
| `scripts/projectile.gd`、`gun.gd` | ✅（不改信号签名） | 只读 |
| `scripts/player.gd` | ✅（不动 take_damage/信号） | ✅（HUD 接线） |
| `scripts/main.gd` | 仅场景搭建 / 敌人配置 | 仅 `_build_hud` 与 `_on_*` 处理 |
| `assets/models/**` | ✅ | ❌ |
| `assets/sfx/**`（枪械/战斗音效） | ✅（枪声/换弹等） | ✅（`ui/` 子目录） |
| `assets/ui/**`、`ui/**`、`scenes/ui/**` | ❌ | ✅ |
| `project.godot` | ❌ | ✅（主题/字体/输入映射） |
| `tests/test_combat.gd`、`test_reload.gd` | ✅ | 只读 |
| `README.md`、`WORKFLOW.md` | ✅（改完即提交） | ✅ |

`main.gd` 是唯一共享文件：**动画线只碰场景搭建与敌人配置，UI 线只碰 HUD 相关函数**。
动手前先看对方有没有未提交的改动。

## 2. 提交纪律（谁先改谁提交）

1. 动手前：`git status --short`，确认工作区只有自己的改动（或干净）。
2. 改完**立即提交**，不要跨任务攒改动。
3. 提交前必须跑无头验证（见第 4 节），通过才提交。
4. 发现对方未提交的改动 → 不要覆盖，先停下协调。
5. 提交信息建议带前缀：`anim:` 或 `ui:`，方便回溯。

## 3. 稳定契约（UI 的数据源，禁止改签名）

- `player.gd`：`signal damaged(hp)`、`signal died`、`var hp`、`take_damage(d)`
- `gun.gd`：`signal shot(ammo, reserve)`、`signal hit`、`signal reloading`、
  `signal reloaded(ammo, reserve)`、`signal empty`、`var ammo`、`var reserve`
- `enemy.gd`：`take_damage(d)`；接触伤害由敌人自行结算

UI 只消费这些信号/属性；动画线改内部实现时必须保持这些接口不变。

## 4. 无头验证（提交前必跑）

```powershell
$godot = 'E:\3d\Godot_v4.7.1-stable_win64.exe\Godot_v4.7.1-stable_win64.exe'
& $godot --headless --path 'E:\3d\3-dfps' --import          # 新增脚本/资产后
& $godot --headless --path 'E:\3d\3-dfps' --quit-after 180  # 语法与运行
& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_combat.gd
& $godot --headless --path 'E:\3d\3-dfps' --script res://tests/test_reload.gd
```

## 5. 冲突处理

- 同文件冲突时：后改的一方把改动暂存（`git stash`），先让对方提交，再 `git stash pop` 应用并手工合并。
- 尽量把 `main.gd` 的改动拆成独立小提交，减少合并面。

## 6. UI 线补充

- UI 风格唯一真源：`DESIGN.md`（设计 DNA / Token / 一致性检查清单）。
- UI 完整闭环：`UI-WORKFLOW.md`（定风格 → 出图 → 验收 → Token → 组件 → 验证 → 提交）。
- UI 线动手前必读 `DESIGN.md` + 本文件；风格变更先改 `DESIGN.md` 再改代码。
