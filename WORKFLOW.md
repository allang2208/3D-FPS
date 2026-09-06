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

## 7. 资产建模纪律（换模型 / 重导出 / 拆件）

重建模或换枪模时，**绝对不要让游戏处于“引用坏掉”的中间态**（否则编辑器/游戏直接打不开）。

1. **新资产先独立生成**：一律用新文件名（如 `akm_voxel_v2.obj`），不要先覆盖正式文件名。
2. **先验证再置入**：在独立环境验证通过后，更新正式引用 → `--import` → 对应资产验证与冒烟 → 提交。保留有效 `.import`；仅在确认单个资源导入缓存异常时定点处理。枪械还需 `test_ads_calibration`。
3. **不要提前动 `.import` / `.tres` / 正式资产**：中途删改会导致引用缺失、项目无法打开，
   用户还要测其他功能，禁止制造这种状态。
4. Godot OBJ 导入会把网格归一化到原点（0..1.005），`gun.gd` 已按 AABB 中心反移居中；
   换新网格后必须跑 `test_ads_calibration`（瞄具/枪口/ADS 自动校准是否仍正确）。
5. 部件拆分（弹匣等）：源 GLB 用 `tools/ai-gen/strip_mag_glb.py`，体素用
   `tools/ai-gen/voxelize_glb.py`（自动 split_magazine）；拆完验证弹匣区无残留
   （源 GLB 弹匣区 `y<-0.05` 顶点数 = 0；体素枪体只剩弹匣井自然底面）。
6. 详细体素管线见 `docs/voxel-pipeline.md`。

## 8. 仓库整理与推送

1. 先核对当前仓库根目录、`git remote -v`、分支及上游。用户指定 URL 与 origin 不一致时，确认目标后再推送，不自行改远端或把两个项目历史合并。
2. 清理仅限本次任务归属明确的废案、临时文件及已无引用的派生资源。先搜索代码、场景、工具的引用；有用原始源文件、许可证、可复现脚本和最终预览保留。历史记录注明已淘汰，不伪装为当前实现。
3. 禁止全库 `git clean`、`reset --hard`、`git add -A`；不删他人文件、不处理无关未提交改动。删除使用明确路径，Godot 的配套 UID/import 随对应源文件同步整理，不例行清空 `.godot`。
4. 只暂存本次明确文件。暂存区已有他人内容时不代为提交；检查 `git diff --cached --name-status`、完整差异、`--check`、新增大文件和许可证。提交消息说明当前结果及验证范围。
5. 推送前 `git fetch origin`，核对 `origin/<目标分支>..HEAD` 的每个待推提交。包含无关未发布提交时不得整批推送；在独立发布工作区整理本次提交，保留用户工作区。常规并行开发仍遵守不新建分支约定，此项仅用于有必要的隔离发布。
6. 运行第 4 节检查和本次相关场景测试；区分已有故障、当前失败与未验证范围。只用普通非强制推送并显式指定目标分支。非快进拒绝后重新 fetch、检查差异，不强推覆盖。
7. 推送成功后用 `git ls-remote` 回读目标分支 SHA，确认与本次提交一致，报告提交、目标和未包含的改动。
