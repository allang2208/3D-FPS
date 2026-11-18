# 枪械资料清理与 Git 发布

仅在用户授权 Git 发布时，读取实际仓库 WORKFLOW 第 8 节及宿主 AGENTS，使用当前仓库的真实分支、远端与发布范围。FPSGAME 本机根目录为 `D:/FPS3D/FPSGAME`，旧 Godot 归档仅作历史参考。原因：目录位置不自动授权提交推送，历史远端和跟踪状态也可能变化。

## 文件判断

- 保留运行引用及其依赖、最终可编辑源、许可证、作者脚本、密集抓握参数、关键失败对照和最终视听证据。目录旧、名为 candidate、动画已换版，都不足以判定废案；例如 TacticalToss 依赖 SlapImpact 的源，而 SlapImpact 又依赖 WrapGrip。
- Blender `.blend1` 仅在正式可编辑文件存在且无活动调用时作为备份中间件归档；`*_silent.mp4` 仅在对应实际混音成片存在时作为合成中间件归档。未完成的唯一输出不能直接归为垃圾。 原因：唯一未完成输出仍有恢复价值，只有明确替代物和无活动依赖的备份才能退役。
- 生成精确清单：原路径、目标 trash 路径、大小、SHA-256、理由及保留替代物。移动前检查绝对路径在本次授权根内、源未变化；移动后读回散列。保留各案例目录下可重建最终结果的输入，不清空整批 SourceAssets。
- 旧标准退出当前入口后可归档原文并留下迁移指向，避免历史链接将未来开发引回 Godot。只按当前任务处理，不能将“全部废案”解释为清理其他任务的未提交文件。

## 发布边界

- 共享工作区有其他修改时仍优先在 D 盘按明确路径提交，不 stash/reset 用户工作区，不夹带并行功能。只有实际冲突或验证隔离确需时才建临时工作区，用后归档；不要仅因目录脏就复制工程或建立常驻发布副本。 原因：共享工作树可能包含其他任务改动，发布范围需要对应本次实际拥有的文件与差异。
- 当前代码直接发布到根目录 `Source/`，配置到 `Config/`，工具到 `Tools/`，作者脚本到 `SourceAssets/`；`unreal/<topic>/` 是历史迁移证据，不再作为当前代码入口。完整源码与完整可运行内容分别声明，根目录 `Docs/AssetSetup.md` 记录本地 Content 恢复范围。原版模型、贴图、音频、含第三方资产的 Blend/FBX/uasset 无再分发许可时只在本机保留；“商用游戏可用”不等于“原资产可公开入库”。
- 日常发布仍按本次修改范围提交，避免混入并行功能。用户明确授权当前整个 UE 工程作为新仓库基线时，冻结完整模块、targets、配置与依赖数据并记录取样时间/散列，不只发布零散函数摘录；取样后的宿主变化留待下一次审查。
- 保持可用的工具目录关系，记录缺省宿主路径、所需已许可源资产和调用前的目的地修改。将已有检查保存为带日期的报告，不伪装成从公共快照重新运行过。 原因：恢复需要真实路径与许可输入，旧报告只证明当时执行过的范围。
- 公开工作流入口优先仓库相对链接。绝对本机路径只能作为明确标注的宿主/案例位置，不能让网页上的主要导航只链接到本机 C 盘。 原因：公共网页读者无法访问本机 C 盘，公开导航应指向仓库中可到达的文档。
- 精确暂存后审查完整 diff、`--check`、大文件、敏感信息、许可、脚本语法和链接。已验证源码快照/文档整理不重跑无关 Godot 测试。

## 并行会话下的精确暂存（2026-09-17）

同一文件里可能同时躺着多个工作会话的未提交改动，`git add <文件>` 等于替别人发布；`git add -p` 在无人值守运行中不可用。做法：

- 先用 `Tools/AssetPipeline/stage_session_hunks.py` 逐 hunk 分类（`--file` 可多次，`--exclude` 丢掉不属于本次的 hunk），**先看分类输出再动手**，确认每个保留的 hunk 都是本次改动。 原因：共享文件中可能混有多个任务的改动，按实际差异提取才能保留完整上下文和其他人的内容。
- 两个会话改了相邻行时，整块 hunk 无法按标记切开，用 `--manual` 提供手写的替换 hunk；工具会按实际增删重算 new 侧行号（丢了 hunk、改了行数后不重算，`git apply` 会以 "patch does not apply" 拒绝）。
- 应用：`git apply --cached --unidiff-zero --whitespace=nowarn --recount <patch>`。`-U0` 补丁必须带 `--unidiff-zero`，工程文件是 CRLF、索引是 LF，两者都要放宽。 原因：零上下文补丁和换行格式需要明确参数，应用范围仍只能是用户授权的发布内容。
- **被排除的 hunk 会成为依赖缺口**：验证暂存子集时，别把索引内容写回脏工作区再编译——其它文件带着并行改动，会报出与本次无关的假错误。要证明提交能独立编译，用 `git worktree add` 指向该提交（或在临时目录重建）后编译，验证完删掉工作树。
- 若确认某个 hunk 无法在不带上并行功能的前提下发布（例如补丁落在对方新增的函数体内），就把那部分留未提交、在交付说明里点明，不要为了"提交完整"而连带发布别人的在途工作。
- 界面类工具与暂存/发布脚本放 `Tools/AssetPipeline/`；一次性守望、备份脚本放 `Saved/`（不进仓库）。
- 仅普通非强制推送。被拒绝时重新 fetch、检查新增提交并处理本次冲突；成功后用 `ls-remote` 回读目标 SHA。记录发布工作区与提交，不为了让共享工作区看起来干净而重置其分支。 原因：普通推送保留远端历史，拒绝后应处理实际变化，不能为整洁外观重置共享分支。

### 推送网络故障：DNS 解析到不可达 IP（2026-09-25）

本机 `github.com` 会解析到 `20.205.243.166`，该地址 443 不可达，于是 `git fetch`/`push` 报
`fatal: unable to access ...: Recv failure: Connection was reset`。**这不是凭据或权限问题，原样重试不会好。**

用户要求排查发布网络故障时，先分清是 DNS 还是链路：`Resolve-DnsName github.com` 看解析结果，`Test-NetConnection <ip> -Port 443` 逐 IP 测连通。历史 `140.82.112.3:443` 只是当次结果；若当前有可信且可达的目标地址，可用单次请求配置定位解析问题，**不改 hosts、不改系统 DNS**。原因：历史 IP 可能变化，诊断一次发布连接不应永久改写全机网络配置：

```
git -c http.curloptResolve="github.com:443:140.82.112.3" fetch origin
git -c http.curloptResolve="github.com:443:140.82.112.3" push origin HEAD:main
git -c http.curloptResolve="github.com:443:140.82.112.3" ls-remote origin
```

`-c` 只对本次命令生效，不落进仓库或全局配置。fetch、push、`ls-remote` 回读三步都要带同一个覆盖值，否则验证步骤自己会失败。可达 IP 会随时间变化，下次失败先重测，不把某个 IP 当固定值写进脚本。

### 推送网络故障二：TCP 通但 HTTPS 被重置，改走本机代理（2026-09-29）

上一条的适用边界要修正。本轮 `20.205.243.166:443` 的 `Test-NetConnection` 返回 **True**，可 `curl.exe https://github.com` 21 秒后 `http_code=000`，`git push` 仍是 `Recv failure: Connection was reset`；换 `140.82.112.3` 后 fetch 依旧被重置、push 变成 `Failed to connect ... after 21042 ms`。**TCP 探测会被中间设备假阳性放行，`Test-NetConnection` 通不等于 HTTPS 能过**；这种情况下 `curloptResolve` 覆盖无效，不要逐个 IP 试下去。

判据与出路都用 `curl` 量代理：`curl.exe -s -o NUL -w "%{http_code}" --proxy http://127.0.0.1:<port> --max-time 20 https://github.com`，本机 7890/7897 在听且返回 `200`，于是

```
git -c http.proxy=http://127.0.0.1:7890 fetch origin
git -c http.proxy=http://127.0.0.1:7890 push origin HEAD:main
git -c http.proxy=http://127.0.0.1:7890 ls-remote origin
```

同样是一次性 `-c`，不写 `http.proxy` 配置、不改 hosts；三步带同一个代理，否则验证步骤自己会失败。

### 共享工作区：他人暂存条目与"基线在工作期间前进"（2026-09-29）

- **索引里出现别人的暂存条目**（本轮 `.gitignore`、`modular_outfits.json`、`FPSModularOutfitComponent.cpp`）：既不能替对方取消暂存，也不能顺手提交。用**临时索引**自建提交树，全程不碰共享索引：`$env:GIT_INDEX_FILE=Saved/tmp-index` → `git read-tree <base>` → 逐个 `git apply --cached --unidiff-zero --whitespace=nowarn --recount <补丁>` → `git add -- <纯属本次的文件>` → `git diff --cached` 复核 → `git write-tree` + `git commit-tree <tree> -p <base> -F <说明>` → `git update-ref refs/heads/<分支> <新提交>` → 清 `GIT_INDEX_FILE`。提交后把共享索引里本次文件的条目对齐到新提交（`git update-index --cacheinfo 100644,<blob>,<路径>`），免留"假暂存"。同一路径的脏工作区与暂存条目都不要重写。 原因：共享工作树可能包含其他任务改动，发布范围需要对应本次实际拥有的文件与差异。
- **提交前远端 main 前进了**：非强制推送会被 `! [rejected] (non-fast-forward)` 正确拒绝（本轮 `155174d1` → `7382ff0b`）。先 `git log --oneline <旧base>..<新base>` 与 `git diff --stat <旧base> <新base>` 审这次推送，再看自己的补丁能否沿用：没被动过的文件直接重放，被动过的**针对新基线重新生成切片**（本轮只有 `items.json`，对方服装改动已发布，重生成后 6 个 hunk 只剩自己的 2 个）。在新 base 上用临时索引重放出线性提交再推；旧提交从未推送，留 reflog 即可，不做 force。
- **一个补丁只应用一次**：`Get-ChildItem Saved\u0-*.patch` 批处理时，新生成的文件名也在通配范围内（本轮 `u0-items-new.patch` 被循环与显式调用各应用一次，`items.json` 出现 56 行重复、JSON 里同一键两次）。落地前用 `git diff --cached --numstat` 逐个核对增删行数。
- **临时索引的基线会被本地并行提交推过去**（2026-10-07 苍龙发布）：
  - **经过**：从 `read-tree` 到 `commit-tree` 之间，其他会话在本机直接提交并推送了两次（`85728402` → `95e33ca0` → `84f42fd3`）。当时提交前取的是“此刻的 HEAD”作为父提交，`update-ref` 的旧值也是这个新 HEAD，守卫照样通过。结果树仍是旧基线加上本次改动，相当于回滚了别人的 24 个文件。推送前 `git diff --cached --name-only <新HEAD>` 显示的文件数比预期多出很多，才发现问题；随后把分支指回对方提交，再在新基线上全部重建。
  - **规则**：在 `read-tree` 时把基线写进文件；提交时用这个记下的基线做父提交，也作为 `update-ref <ref> <new> <记下的基线>` 的旧值，这样基线一变就会失败。提交前再 fetch 一次，确认 `HEAD == origin/main == 记下的基线`。
  - **其他会话的提交可能带走你的工作区改动**：它们可能把你写在共享文件里的段落一起提交（本轮联机 SKILL 的苍龙一节随 `84f42fd3` 发布）。重建前先 `git diff <新HEAD> -- <文件>`，这类文件不要再插一次，否则会出现重复章节。
  - **改名后同步共享索引**：`git restore --staged -- <路径>` 的路径清单要包含改名或删除的**旧路径**。`git diff --name-only` 开启改名检测时只列新路径，旧路径会在共享索引里残留为“已暂存新增”。

### 自己的行与并行改动相邻：改用 -U0 原子 hunk（2026-09-29）

`Tools/Weapons/stage_weapon_hunks.py` 用 `git diff -U3`，自己的新增行与对方改动**相距 3 行以内就会被并进同一个 hunk**（本轮 `FPSGAMECharacter.cpp` 的 `UpdateWeaponJumpPose`、`FPSGAMECharacterProfile.cpp` 的 `LMG201WeaponAssets.h`、`ColdSteelEnhancementSystem.cpp` 的 staff 行、`ColdSteelItemTooltipData.cpp` 的附魔卡片行都中过）。连块不能靠标记救：丢这块会丢自己的行，留这块会带上对方的行。

这时按 `-U0` 重新切片，每个 hunk 只含一段连续改动，标记永不误带。`Saved/stage_u0.py` 是这轮的一次性脚本（`--keep-contains` / `--drop-contains`，逻辑同工具版，只把 `-U3` 换成 `-U0`），补丁仍用 `git apply --cached --unidiff-zero --whitespace=nowarn --recount` 落地。`-U0` 没有上下文可模糊匹配，只能用于"索引 = 补丁基线"；基线变了要重新生成，不要挪用旧补丁。 原因：移动状态需要真实支撑和碰撞条件，达到缓存坐标并不等于动作已经安全完成。

### 纯新增 hunk 的零长度坐标（2026-10-01）

- 本轮复核发现 `stage_session_hunks.py` 重算纯新增 hunk 时少算一行：`@@ -N,0 +M,K @@` 的旧侧 N 表示“在第 N 行之后插入”，新侧首行应为 `N + 前方净增量 + 1`。直接用 `N + 净增量`，`git apply --unidiff-zero` 可能成功但将代码插到闭合括号之前；`--check` 不检查语义，不能以成功返回判断位置正确。 原因：共享文件中可能混有多个任务的改动，按实际差异提取才能保留完整上下文和其他人的内容。
- 使用该工具的纯新增结果前，先修正坐标或按旧侧边界将所选 hunk 重建为 HEAD 上的候选内容，再生成带上下文的补丁。复核暂存后的完整函数与成员顺序。本轮通过只更新自己已暂存路径的 blob 修正，工作区和其他人的暂存条目均不改写。 原因：重建需要真实的上游输入及先后顺序，仅保留最终输出无法恢复可编辑制作链。

### 按标记丢弃 hunk 的通用做法（2026-09-21）

- `Tools/AssetPipeline/stage_session_hunks.py` 的标记是写死的；本轮新增通用版 `Tools/Weapons/stage_weapon_hunks.py`：`--file`（可多次）加 `--drop-contains <子串>`（可多次），保留除命中标记外的全部 hunk，**先打印 KEEP/DROP 报告再写补丁**，然后 `git apply --cached <补丁>`。丢掉前面的 hunk 会让后面的行号偏移，靠上下文匹配即可（本轮 35 保留 / 7 丢弃全部干净落位，`--check` 无告警）。
- 落地案例：`Content/ColdSteelData/gunsmith.json`（对方新增 `ue_pkm` 武器块 21 行）、`GunsmithSystem.h/.cpp`（对方 `BlockStamina` / `CooldownReduceSecondsPerHit`）、`FPSWeaponFXComponent.cpp`（对方 PKM 资产分支）、`FPSBallisticsComponent.cpp`（对方 `FWeaponDamageResult` 命中签名）。丢弃后必须复核四项：`git diff --cached` 搜对方标记为 0、`git diff --cached --check`、暂存的 JSON 能 `json.load` 且武器 id 集合与 HEAD 一致、暂存代码不引用被丢掉的字段或头文件。 原因：共享工作树可能包含其他任务改动，发布范围需要对应本次实际拥有的文件与差异。
- **落在对方 hunk 内部的自己那一行**（例：`ue_pkm` 块里的 `spread_mult: 2`）不要为凑完整而连块提交：仅提取能独立表达的本轮片段；无法安全分离时保留未提交状态，并明确尚未发布的依赖，不承诺其他任务会代为提交。 原因：混合差异包含其他工作的所有权，无法独立提取时应说明未发布依赖而非连块带入。
- PowerShell 会吞掉参数里的双引号（`--drop-contains '"id": "ue_pkm"'` 匹配不到），标记改用不含引号的子串（`ue_pkm`）。
- **生成类文档只从"已提交"的目录数据生成**（2026-09-21 补记，2026-09-22 修正）：`Tools/Weapons/dump_attachment_values.py` 直接读工作区的 `gunsmith.json`，若此时对方有未提交的目录改动（本轮 `ue_pkm` 武器块），生成出来的数值表就把**未发布的数值公开发布**了；对方后来回退，表里就留下没有出处的内容。规矩：生成前先 `git status --short -- <目录文件>`，脏就不要生成／不要提交；对方回退或改动目录后**重新生成并重读正文**。本轮据此删掉 5 行 PKM 数据行。**另一个坑**：生成器里有手写的正文断言（本轮"七把长枪含 PKM 的 `spread_mult`"），目录一变它就变成假话——生成器里的每一句数值断言都要能从目录重新推出来，或至少在改动目录后回读一遍。 原因：发布数值应对应实际发布版本，工作区未发布变化和手写断言会让公开文档失去来源。

## 仓库更换引擎

用户要求以当前 UE 工程重新开始时，先给原 main 建立归档标签，将隔离目录内的旧引擎文件按清单移入本机 trash，然后用普通新提交替换当前树。保留历史和原共享 checkout，不做 orphan/强推，不把缓存、未核准资产或历史草案重新塞回新主目录。验证源文件取样、UE 编译、归档散列以及远端分支/标签；保留历史意味着仓库历史体积不会立即减小。

## 清理批次的发布快照与并行归属（2026-11-18）

- 个人技能源导出到仓库的发布快照，工程导航用相对链接；保留原始源散列与导出散列，不把快照另作维护源。原因：本机 C 盘正文不会随工程推送，公开入口需要可到达的依赖。
- 清理前原件和逐次写入记录用于提取本批差异；后续共享修改按记录分离，不能把当前整文件当成本批成果。原因：同一路径可能已被其他任务继续修改，路径归属不等于全部内容归属。
- 多文件拆分的旧入口、新承接文件和必要作者更新按同一组发布；未发布宿主使该组无法安全合入时，保留带前置散列的接入包并明确未合入范围。原因：只发布移出端或移入端会产生缺失或重复定义，接入包也不等于运行源码已集成。
- 原始恢复快照和编辑草稿留本机 trash，公开归档清单及有用的历史文本；不要公开含整份无关工作区的恢复副本。原因：回滚资料可能包含其他功能和本地依赖，公开发布应保持本次授权边界。
