# 手枪动作整理与发布（2026-09-15）

用户授权将废案放入 trash、整理 Git、沉淀对应 SKILL，并推送 `https://github.com/allang2208/3D-FPS.git`。执行前读取工程 AGENTS、WORKFLOW 第 4–8 节及 AssetSetup，确认实际工作区为 `D:/FPS3D/FPSGAME`、分支 `main`、远端默认分支 `main`。

## 废案归档

`trash/pistol-animation-20260915` 共 492 个文件，4,009,267,897 字节（约 4.01 GB），122 项目录/文件移动。全部保留原相对路径，移动前后 SHA-256 一致。

- 用户否定的单持 EjectHand、DonorPress：作者目录及引擎动画输出。
- 已替换的双持 ReferencePoseV2、SprintReferenceV4、最初的动画输出。
- NaturalAimV3 中已改由 SprintSmoothV5 / RevolverReloadFlickV6 加载的独立奔跑和左轮换弹导出。

UE Asset Registry 查询归档集 210 个包，未发现集合外硬/软包或管理引用；代码加载路径同时按当前分支审查。此结果用于资源整理，不是游戏动画验收。

清单：`archive-plan.json`、`archive-references.json`、`archive-manifest.json`、`archive-summary.json`。执行器为 `Tools/Publication/archive_pistol_outputs_20260915.ps1`；目录边界、重解析点和目标存在性在移动前处理，归档没有删除。

## 保留的有效依赖

- 单持 PalmClearance 当前源与七段输出，及 LeftRecovery → Natural → Motion → Split → Flick → Upgrade 的上游作者输入。
- 原始双持骨架/网格恢复文件，NaturalAimV3 当前基础动作、SprintSmoothV5 奔跑和 RevolverReloadFlickV6 左轮换弹。
- 单持 PistolLocomotion、原始模型、Manny 手模、机械源、音频和许可记录。
- 历史诊断、参考资料及包含有效动作的可编辑混合源，不根据日期批量判废。

PalmClearance 原本从两个废案读取部分作者代码和导入器；本次提取到当前 `reference_basis.py` 及独立导入脚本，再归档旧目录。正常作者/导入入口已跳过退役的双持片段。

## Git 与知识沉淀

本次发布当前单持路径、必要的 `Magic` 参数重名修正、手枪作者工具和参数、动作/归档文档，以及手臂 SKILL 的 `references/pistol-dual-revolver.md` 与手枪分卷入口。个人 SKILL 与工程镜像同步。

仓库中的其他并行修改及原有暂存内容不属于本次提交。双持输入/装备刷新等运行代码已经有已发布基础及后续并行修改，本次不把并行差异一并提交。

Blend、FBX、uasset、模型原包、完整运动采样、日志和 trash 不公开上传。当前代码的完整本机恢复仍须上面列出的授权内容；本次提交不等于完整游戏资产云备份。

## 状态与检查边界

PalmClearance 在前一开发阶段已完成七段导出、导入和必要 Editor 构建，尚无用户实机接受结论。SprintSmooth 的旧诊断记录不视为本次重测。此轮只做用户要求的归档完整性、作者依赖、发布源码/差异和推送检查，不启动游戏、不做渲染或玩法回归。

发布清单为 `publication-files.txt` 的 36 个文本文件，约 0.44 MB。11 个 Python 文件通过语法解析，9 个 JSON 可解析，归档 PowerShell 脚本通过语法解析；暂存差异无空白错误，所选文件未发现二进制或凭证格式内容。共享战斗文件仅提取本轮参数更名，使用独立 Git 暂存索引，保留原有 `Docs/AssetSetup.md` 暂存内容。
