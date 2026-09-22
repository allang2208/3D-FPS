# 枪械资料清理与 Git 发布

先读实际仓库 WORKFLOW 第 8 节及宿主 AGENTS。2026-09-10 起远端 main 是根目录 UE5 工程；旧 Godot 位于 `archive/godot-before-ue5-20260910` 标签。当前宿主及独立 Git 根目录均为 `D:/FPS3D/FPSGAME`，origin 是 `https://github.com/allang2208/3D-FPS.git`，当前 main 跟踪 origin/main。E 盘旧仓库与发布副本已归档；日常直接在 D 盘开发、提交、推送，不做常驻源码镜像。先 fetch、读取实际远端 HEAD 和待推提交。

## 文件判断

- 保留运行引用及其依赖、最终可编辑源、许可证、作者脚本、密集抓握参数、关键失败对照和最终视听证据。目录旧、名为 candidate、动画已换版，都不足以判定废案；例如 TacticalToss 依赖 SlapImpact 的源，而 SlapImpact 又依赖 WrapGrip。
- Blender `.blend1` 仅在正式可编辑文件存在且无活动调用时作为备份中间件归档；`*_silent.mp4` 仅在对应实际混音成片存在时作为合成中间件归档。未完成的唯一输出不能直接归为垃圾。
- 生成精确清单：原路径、目标 trash 路径、大小、SHA-256、理由及保留替代物。移动前检查绝对路径在本次授权根内、源未变化；移动后读回散列。保留各案例目录下可重建最终结果的输入，不清空整批 SourceAssets。
- 旧标准退出当前入口后可归档原文并留下迁移指向，避免历史链接将未来开发引回 Godot。只按当前任务处理，不能将“全部废案”解释为清理其他任务的未提交文件。

## 发布边界

- 共享工作区有其他修改时仍优先在 D 盘按明确路径提交，不 stash/reset 用户工作区，不夹带并行功能。只有实际冲突或验证隔离确需时才建临时工作区，用后归档；不要仅因目录脏就复制工程或建立常驻发布副本。
- 当前代码直接发布到根目录 `Source/`，配置到 `Config/`，工具到 `Tools/`，作者脚本到 `SourceAssets/`；`unreal/<topic>/` 是历史迁移证据，不再作为当前代码入口。完整源码与完整可运行内容分别声明，根目录 `Docs/AssetSetup.md` 记录本地 Content 恢复范围。原版模型、贴图、音频、含第三方资产的 Blend/FBX/uasset 无再分发许可时只在本机保留；“商用游戏可用”不等于“原资产可公开入库”。
- 日常发布仍按本次修改范围提交，避免混入并行功能。用户明确授权当前整个 UE 工程作为新仓库基线时，冻结完整模块、targets、配置与依赖数据并记录取样时间/散列，不只发布零散函数摘录；取样后的宿主变化留待下一次审查。
- 保持可用的工具目录关系，记录缺省宿主路径、所需已许可源资产和调用前的目的地修改。将已有检查保存为带日期的报告，不伪装成从公共快照重新运行过。
- 公开工作流入口优先仓库相对链接。绝对本机路径只能作为明确标注的宿主/案例位置，不能让网页上的主要导航只链接到本机 C 盘。
- 精确暂存后审查完整 diff、`--check`、大文件、敏感信息、许可、脚本语法和链接。已验证源码快照/文档整理不重跑无关 Godot 测试。

## 并行会话下的精确暂存（2026-09-17）

同一文件里可能同时躺着多个工作会话的未提交改动，`git add <文件>` 等于替别人发布；`git add -p` 在无人值守运行中不可用。做法：

- 先用 `Tools/AssetPipeline/stage_session_hunks.py` 逐 hunk 分类（`--file` 可多次，`--exclude` 丢掉不属于本次的 hunk），**先看分类输出再动手**，确认每个保留的 hunk 都是本次改动。
- 两个会话改了相邻行时，整块 hunk 无法按标记切开，用 `--manual` 提供手写的替换 hunk；工具会按实际增删重算 new 侧行号（丢了 hunk、改了行数后不重算，`git apply` 会以 "patch does not apply" 拒绝）。
- 应用：`git apply --cached --unidiff-zero --whitespace=nowarn --recount <patch>`。`-U0` 补丁必须带 `--unidiff-zero`，工程文件是 CRLF、索引是 LF，两者都要放宽。
- **被排除的 hunk 会成为依赖缺口**：验证暂存子集时，别把索引内容写回脏工作区再编译——其它文件带着并行改动，会报出与本次无关的假错误。要证明提交能独立编译，用 `git worktree add` 指向该提交（或在临时目录重建）后编译，验证完删掉工作树。
- 若确认某个 hunk 无法在不带上并行功能的前提下发布（例如补丁落在对方新增的函数体内），就把那部分留未提交、在交付说明里点明，不要为了"提交完整"而连带发布别人的在途工作。
- 界面类工具与暂存/发布脚本放 `Tools/AssetPipeline/`；一次性守望、备份脚本放 `Saved/`（不进仓库）。
- 仅普通非强制推送。被拒绝时重新 fetch、检查新增提交并处理本次冲突；成功后用 `ls-remote` 回读目标 SHA。记录发布工作区与提交，不为了让共享工作区看起来干净而重置其分支。

### 按标记丢弃 hunk 的通用做法（2026-09-21）

- `Tools/AssetPipeline/stage_session_hunks.py` 的标记是写死的；本轮新增通用版 `Tools/Weapons/stage_weapon_hunks.py`：`--file`（可多次）加 `--drop-contains <子串>`（可多次），保留除命中标记外的全部 hunk，**先打印 KEEP/DROP 报告再写补丁**，然后 `git apply --cached <补丁>`。丢掉前面的 hunk 会让后面的行号偏移，靠上下文匹配即可（本轮 35 保留 / 7 丢弃全部干净落位，`--check` 无告警）。
- 落地案例：`Content/ColdSteelData/gunsmith.json`（对方新增 `ue_pkm` 武器块 21 行）、`GunsmithSystem.h/.cpp`（对方 `BlockStamina` / `CooldownReduceSecondsPerHit`）、`FPSWeaponFXComponent.cpp`（对方 PKM 资产分支）、`FPSBallisticsComponent.cpp`（对方 `FWeaponDamageResult` 命中签名）。丢弃后必须复核四项：`git diff --cached` 搜对方标记为 0、`git diff --cached --check`、暂存的 JSON 能 `json.load` 且武器 id 集合与 HEAD 一致、暂存代码不引用被丢掉的字段或头文件。
- **落在对方 hunk 内部的自己那一行**（例：`ue_pkm` 块里的 `spread_mult: 2`）不要为凑完整而连块提交：留未提交，在交付说明写明"该枪系数将随对方提交一起落地"。
- PowerShell 会吞掉参数里的双引号（`--drop-contains '"id": "ue_pkm"'` 匹配不到），标记改用不含引号的子串（`ue_pkm`）。
- **生成类文档只从"已提交"的目录数据生成**（2026-09-21 补记，2026-09-22 修正）：`Tools/Weapons/dump_attachment_values.py` 直接读工作区的 `gunsmith.json`，若此时对方有未提交的目录改动（本轮 `ue_pkm` 武器块），生成出来的数值表就把**未发布的数值公开发布**了；对方后来回退，表里就留下没有出处的内容。规矩：生成前先 `git status --short -- <目录文件>`，脏就不要生成／不要提交；对方回退或改动目录后**重新生成并重读正文**。本轮据此删掉 5 行 PKM 数据行。**另一个坑**：生成器里有手写的正文断言（本轮"七把长枪含 PKM 的 `spread_mult`"），目录一变它就变成假话——生成器里的每一句数值断言都要能从目录重新推出来，或至少在改动目录后回读一遍。

## 仓库更换引擎

用户要求以当前 UE 工程重新开始时，先给原 main 建立归档标签，将隔离目录内的旧引擎文件按清单移入本机 trash，然后用普通新提交替换当前树。保留历史和原共享 checkout，不做 orphan/强推，不把缓存、未核准资产或历史草案重新塞回新主目录。验证源文件取样、UE 编译、归档散列以及远端分支/标签；保留历史意味着仓库历史体积不会立即减小。
