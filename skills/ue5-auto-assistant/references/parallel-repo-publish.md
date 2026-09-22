# 并行会话下的仓库发布（暂存、退役、推送）

现场事实：`D:/FPS3D/FPSGAME` 是**一个工作区、多个会话共用**（2026-09-22 实测 500+ 个文件同时处于未提交状态）。发布本会话成果时，难点不是写代码，而是把"我的行"从共享文件里精确摘出来。

## 铁律（WORKFLOW 第 7、8 节）

禁止 `git add -A` / `git add .` / `git clean` / `reset --hard`；禁止 stash；按本次明确路径暂存；不夹带他人未验收功能；只做普通推送并显式 `HEAD:main`；推送后回读远端。

## 暂存分三档

1. **整文件属于本次会话** → `git add -- <精确路径…>`，最省事也最安全。
2. **同文件多会话** → `Tools/AssetPipeline/stage_session_hunks.py --file a --marker <本次独有串> [--exclude '<hunk 头>'] --write out.patch`，再 `git apply --cached out.patch`。
   - 标记要选本次**新增行**里独有的 ASCII 串（中文经 argv 传递可能被控制台编码搞坏）。
   - hunk 里混着别人的大块时（例如 JSON 中一次插入横跨多个条目）标记无法自动分开，必须用 `--exclude` 按 hunk 头剔除；先只加 `--write` 之外的预演看它 keep/drop 了哪些。
3. **单个 hunk 无法拆**（JSON 整段重写、行号全变）→ 直接构造暂存内容，不碰工作区：
   ```powershell
   git show :<path>            # 取索引版本
   # 只改自己的行 → 写临时文件
   git hash-object -w --path <path> <tmp>          # 得到 blob
   git update-index --cacheinfo 100644,<oid>,<path> # 写进索引
   ```

## 踩过的坑

- **`git apply --cached` 对工作区 CRLF / 索引 LF 的文件直接失败**（"patch does not apply"，本仓库按 .gitattributes 归一为 LF）。别反复重试、别加 `--ignore-whitespace`，改走第 3 档。
- **用条目 `id` 做作用域会串味**：JSON 里条目 id 与顶层 key 不必同名，且遇到不认识的条目不会重置状态，规则会一路套到文件末尾（实测把几十个物品的 `ue_icon` 改成同一个值）。作用域必须用顶层 key 行 `^  "key": \{$`，并且**改完先逐行断言"只有目标行变化"**再写索引。
- **PowerShell 读 `git show` 输出按 ANSI 解码中文**：`Select-String`/`Get-Content` 判断"HEAD 是否已有某段中文"会得到相反结论。这类核对用 node（`execSync('git show :path')` 按 UTF-8 处理）。
- **提交前必跑**：`git diff --cached --stat`、`git diff --cached --check`、二进制筛查（`--numstat` 里 `- -` 的行）、`--name-only` 确认没夹带别人的 `.cpp/.h`。

## 退役与推送

- 确认退役的文件移入 `trash/<task>/`，README 记录原路径、字节数、SHA-256、原因和替代物；`trash/` 与 `Content/ColdSteelData/*` 已被 .gitignore 忽略，**不进提交**（二进制按第 5 节默认不提交）。
- 推送：`git fetch origin main` → 确认 `origin/main..HEAD` 只有自己的提交 → `git push origin HEAD:main`（非强制）→ `git ls-remote origin refs/heads/main` 与本地 `rev-parse HEAD` 比对，并确认归档标签仍在（`git ls-remote --tags origin`，找 `godot`）。

## 旧 Godot 工程在哪（2026-09-22 核实）

磁盘上**已无 Godot 游戏工程**（旧文档里的 `E:\3d\3-dfps` 不存在，`E:\3d` 只剩 Godot 时代的暂存/预览目录和便携引擎 `Godot_v4.7.1-stable_win64.exe`）。完整工程历史保存在当前 UE 仓库的标签 **`archive/godot-before-ue5-20260910`**（远端同名 tag，commit `a56dd1db`，树内含 `project.godot`、`scripts/`、`scenes/`、`assets/`、`data/`、`addons/`）。要查看或运行：`git archive` 导出，或 `git worktree add <dir> archive/godot-before-ue5-20260910`，用完 `git worktree remove`。仓库其余 `.gd` 只是迁移参考导出器。