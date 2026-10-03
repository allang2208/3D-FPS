# RSH-12 暂停发布清单

本轮是暂停与源码整理。完整状态见 `Docs/Weapons/rsh12-pause-publication-20261003.md`；未完成工作进入 `Docs/Backlog.md`。不在此目录继续制作、编译或导入。

- `archive-manifest.json`：131 个已移动废案的原路径、trash 路径、大小、SHA-256、原因及替代物。实际废案内容不公开。
- `retained-recovery-dependencies.json`：仍在使用的合法原始包、供体、完整蒙皮、未修订拟合基准、作者输入、已保存资产和回滚边界。
- `published-files.json`：本批精确 Git blob 的清单与散列；共享文件只包含 RSH 片段／数据对象，不代表整个当前工作文件。为避免自引用，该清单不记录自己的散列。
- `prepare_archive.py`、`archive_retired.ps1`：本次归档计划及原生 PowerShell 移动入口，已完成。源与目标必须限定本任务；重复归档保留原清单，不重新枚举覆盖。
- `prepare_publication.py`：本次公开候选与精确暂存配方。默认只生成本机 `Local/review`；`--stage` 只在暂存区为空时写入本任务 blob，保留共享工作文件。该脚本用于这一批首次发布，发布后不要再次执行旧批次。

许可署名见 `Docs/ThirdParty/RSH12-Medji-CCBY4.md`。最新四条单动动作尚未完成烘焙，最新 Grip revision 没有实际保存回执。旧回执、旧截图、脚本标识和原生构建均不能代替该资产落盘状态。未新增游戏测试。
