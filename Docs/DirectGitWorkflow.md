# D 盘直接开发与推送

2026-09-10 起，唯一日常工作目录是 `D:/FPS3D/FPSGAME`。本目录的 `.git` 是独立版本库，main 跟踪 `https://github.com/allang2208/3D-FPS.git` 的 origin/main；不依赖 E 盘旧仓库或它的 `.git/worktrees`。

开发时直接修改 D 盘工程，按任务精确暂存并提交，从本目录 fetch/push。未提交的并行源码变化保留在工作区，不整批加入本次文档提交。不再通过 E 盘复制同步发布。

Git 接入时沿用已验证的 main 元数据，只补齐缺失的已跟踪文件，没有检出或覆盖现有模型、动画、源码、存档和配置。Content、作者二进制、缓存与构建产物按忽略规则保留本地；GitHub 当前是源码版本库，不是全部本地资源备份。

E 盘关联的旧 Godot 仓库、历史发布工作区和额外 UE5 克隆统一归档到 `E:/3d/trash/e-drive-repositories-20260910`。此前旧文件归档仍位于 `E:/3d/trash/repository-ue5-root-20260910`。详细来源/目标清单在归档根目录；这些归档不参与 D 盘构建或推送。

入口规则见 [WORKFLOW](../WORKFLOW.md)，资产说明见 [AssetSetup](AssetSetup.md)。
