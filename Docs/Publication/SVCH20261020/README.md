# SVCH、KV 瞄准镜与狙击消音器发布记录

本批发布本会话的 SVCH 枪体替换接入、机械准星、弹道标记、弹匣/通用握把、左手换弹与拉栓、V9 快速近战 R7、KV 1/2/4× 通用瞄准镜，以及 SVD/SVCH 狙击分类和特殊消音器。发布基线为 `b921d59896bc12a8c69daa1bc0c7b1ee61011bbe`，目标是 `https://github.com/allang2208/3D-FPS.git` 的 `main`。

本次只整理、沉淀经验和发布。没有启动 UE、重跑游戏或重新作联机验收。之前的构建、资产保存和检查结论见 [完成度与联机复查](../../Weapons/svch-followup-network-review-20261020.md)；精简的历史回执保存在 `HistoricalReceipts/`。

## 发布范围与共享宿主

- 可独立重放的源码增量提交到 `Source/FPSGAME/`；配置只合入 SVCH、SVD 狙击数值、KV 镜兼容选项及 SVCH 外观 Profile。其他武器、魔法、地牢、衣物及并行工作保留在原工作区。
- `recipe-manifest.json` 列出保留的作者配方，原路径位于 `SourceAssets/SVCH*/` 和 `SourceAssets/SniperSuppressor20261019/`。其中早期阶段用于历史恢复，不能把全部脚本顺次执行到当前资产上。
- 第三人称 `FPSPlayerBodyMotion.cpp` / `FPSPlayerBodyAnimInstance.cpp` 当前依赖未公开的共享身体求解宿主。本次只将 SVCH 增量保存到 `Integration/`，不把整份共享宿主混入提交。
- 原生/UDP 诊断还依赖未公开的 Shotgun/SkillNetworkAudit 夹具。`Diagnostics/` 保存独立 SVCH 检查源码，`integration-manifest.json` 记录三个夹具入口补丁，`diagnostics-manifest.json` 记录恢复目标与宿主散列。
- 补丁前置与结果散列按 UTF-8、LF 文本计算。先取得对应具名前置，核对散列，再应用补丁；不要强行应用到不同版本，也不要覆盖完整本机当前源码。这里的前置是为隔离本次增量重构的基线，不代表曾独立发布过的历史版本。

这是带恢复边界的源码发布，不能据此宣称干净检出已能完整构建或运行。完整本机工程仍是开发宿主。

## 当前资产恢复顺序

1. 恢复有权使用的 SVD/Manny 源动作、认可的 V9 原生派生、衣袖/手套母版及旧 SVCH 仍被引用的源输入。V9 的部分路径仍名为 `BarePalmV7`；以母版、骨架和散列辨识。
2. 新枪体以 `SVCHReplacement20261018` 为主：选定模型 → `SightsR2` → `RealSights20261019`。已保存的主网格为 `/Game/Weapons/SVCH/Replacement20261018/RealSights20261019/SK_SVCH_RealFoldingSights`。准星、枪口、导轨与抛壳口使用保存后的 UE 标定。
3. 保留左手换弹/拉栓、弹匣接口、根部退镜和 `ForegripFit20261019` 恢复链。五套握持 Profile 包含 base/angled/vertical/canted/prism；tactical_vertical 复用 vertical。
4. 快速近战当前入口是 `QuickMeleeGripR7_20261020`：`author_grip.py` → `bake_existing_handoff.py` → `encode_profiles.py` → 配套运行代码 → guarded install。R7 依赖 R6 的压缩源、R5 支撑、R4 原生链/相机、R3 表面修形、R2 输入及 Wrist/RootClearance 导出器。不要对已烘焙结果重复执行 handoff bake。
5. KV 镜恢复 `SVCHScopeUniversal20261019` 的各宿主拟合和承接座；稳定配件 ID `kv_scope_4x`，游戏倍率 1/2/4×，稳定性 +5%。原包名不足以确定现实型号。
6. 消音器恢复 `SniperSuppressor20261019` 及 `ScaleRepair20261019`。只适配 SVD/SVCH；速度 ×0.75、后坐力 ×0.60、稳定性 ×1.30，无声击杀复用弓的延迟警觉处理。狙击基础暴击倍率 +1.0 属于武器，不是配件。

完整保存资产散列见 `HistoricalReceipts/installed-assets.json`。几何、贴图、密集姿态、UE 包和原素材保留本机，不在公开 Git 中；只有配方不能重建缺失的许可输入。早期 Refine R5/R8/R9/R11、Sketchfab 初次作者/握持源仍有实际依赖，不能仅按版本号删除。

## 归档

本次曾将 **330 个文件、116,421,952 字节**移入 `trash/svch-retired-20261020/`，保留原相对路径。范围包括旧枪体表面样件、明确否定的姿态候选、一次性诊断/预览与备份。每项前后 SHA-256 均记录于 `archive-manifest.json`，执行回执为 `archive-receipt.json`；脚本为 `Tools/Publication/Archive-SVCH20261020.ps1`。

推送前复查发现该归档目录已不存在；用户在当前对话明确确认“我已清空 trash，无需恢复”。因此本次不恢复废案，原始清单和移动回执仅保留历史追溯，不能作为当前仍可恢复的承诺。最新状态见 `archive-current-status.json`。`trash` 不公开提交；活动生产输入仍保留在原位置。

之后将本轮完成使命的 63 份发布准备文件移入 `trash/svch-publication-prep-20261020/`，包括暂存候选、私有共享宿主基线副本及一次性整理脚本；没有留下第二份活动源码。移动后散列一致，记录见 `publication-prep-archive.json` 与 `publication-prep-receipt.json`。

## 许可与凭据

用户选定的 [Sketchfab 枪体页面](https://sketchfab.com/3d-models/chukavin-sniper-rifle-b3bb922bdf1a481a96b9e2940b2d26fc) 是来源记录，不是对原包、原游戏衍生素材或贴图的公开再分发许可。本次不提交这些资源、下载响应、访问凭据或私有宿主副本。

## 尚未完成

1. 五种通用改造枪托仍缺新 SVCH 的实际接口、原厂段隐藏和对应第三人称外观。
2. 历史 376 项原生检查和 12 个本地 UDP 表现场景，不覆盖快速近战“客机输入 → 实际接触 → 命中上报 → 服务器伤害 → 远端动作”的完整联网流程。
3. 连续多人第三人称画面、快速近战/换弹所有视角穿模、音频及消音器击杀/未击杀怪物警觉实战仍待体验。

这些边界保留在记录中，不因归档或 Git 推送而标记完成。可复用方法已同步至手臂、武器、存档联机三个 SKILL 的对应参考页。
