# 地牢性能优化阶段收尾

2026-10-13 用户要求暂停优化，后续从 [待办](../../Backlog.md) 的“地牢怪群卡顿与预览退出崩溃”继续。本轮不再挂载采样、打开 UE 或运行测试。

## 已完成及当前边界

本机已实现地牢资源准备与装配重叠、同帧精确导航投影缓存、决策服务错峰、闲置图标/图鉴/掉落物预览回收、有限职员实例及 GPU 准备、F6 战斗窗口与资源观察、AI/GPU 自动追踪。后三类职员身体预热仅覆盖光栅/蒙皮/形变；完整动态光追、投手/精英及深层显存驻留归因仍未完成。

最后修订是预览场景释放前与重建后的世界通知：DynamicWind 保存场景引用，漏通知会使注销路径可能访问已释放的场景。修订匹配本机引擎生命周期，常规 Editor 构建成功（36 actions，42.22 秒）；没有运行退出试玩/重开图鉴验证，不宣称崩溃彻底解决。非 Editor 构建继续回收模型和捕获目标，保留空 FScene 到正常世界清理。

此前详细 trace 指向迎宾/研究员衣物 MorphUpdate，但最新完整逐函数窗口缺失。2026-10-13 22:16 首轮脚本调用错误在首次职员出现时停止；F6 战斗窗口已抢救。迎宾第二波后 5–10 秒约 24.5 FPS，游戏线程耗时也高；这批显存样本未显示超预算。因此后续必须同时看 CPU AI/移动/动画与 GPU 形变/等待，不能延用旧单一显存结论。修正版 Python 使用实际反射接口 `get_controlled_pawn`，可选 AI 状态失败不会再停止原生 trace；完整修正版采样仍待取得。

## Git 发布范围

- 22 个可独立接入的源码/配置目标按原路径发布：预览生命周期与三个消费方、衣物过渡的冗余更新修订、AI 作用域与同帧投影缓存、图标请求按面板状态调度、PIE 编辑器场景回收配置。共享文件只提交本轮修改块，保留其他功能在工作区。
- [runtime-integration.patch](runtime-integration.patch) 保存另外 27 个相互依赖的地牢准备、有限预热、F6 及自动导出文件。它针对本机尚未发布的部分玩法/联机上下文，而非可直接应用到公开 HEAD 的完整补丁。**不要对当前本机工程重复应用**，当前源码已包含结果。
- [integration-manifest.json](integration-manifest.json) 记录每个补丁前置内容与结果的 LF 规范化 SHA-256，并列明需要未发布上下文的文件。补丁为零上下文 unified diff，核对所有前置散列后使用 `git apply --unidiff-zero`。恢复时先取得对应玩法/联机前置版本，再核对文件散列后接入；不强制覆盖文件，不用当前公共基线反推或改写刷怪规则。
- 公开自动采样/特效准备脚本、范围内的过程说明和归档元数据。个人 SKILL 已更新性能面板归因及预览场景生命周期；仓库发布对应 references 和本轮入口链接，未夹带另一轮 SKILL 路由整理。

本机整合版本的构建结果不能替代上述 Git 发布切片的独立构建。本轮只完成用户要求的发布范围、差异、补丁和归档检查，没有新建工程副本或运行游戏。

## 本机资源与证据

UE 模型/动作/材质包、Fab/Epic 等许可依赖、压缩后天空 HDR、编译后的 Niagara 资源依然通过 [AssetSetup](../../AssetSetup.md) 恢复；本次不上传其二进制、DLL、PDB、trace、CrashContext 或日志。

- 有效历史 GPU 追踪：`Saved/DungeonEntryCaptures/20261012-154840-442768/`。
- 本轮不完整 trace 与恢复的战斗分析：`Saved/DungeonEntryCaptures/20261013-141431-711385/`，包括 `recovered-analysis.json` 和恢复 JSON 的回执。
- 恢复的报告：`Saved/PerformanceReports/performance-20261013-142031-BDE673EC4E29760E6D67168499012C75.json`。
- 22:22 第二轮仅挂载未录制，编辑器随后在退出旧试玩时崩溃；该回调已随进程终止失效。
- 最近构建：`Saved/PreviewWindLifecycle20261013/editor-build-20261013-222913.log`。
- 详细原因与证据边界：[采样恢复与预览崩溃](../../Performance/monster-attribution-and-preview-crash-20261013.txt)。

## 归档

[archive-manifest.json](archive-manifest.json) 记录 31 份旧快照、完成的一次性脚本及失效链接产物的原路径、`trash/dungeon-performance-retired-20261013/` 目标、字节数和 SHA-256，搬移前后已核对。历史文档引用的 `Saved/TaskBackups/MonsterAttribution-*`、`Saved/TaskBackups/PreviewWindLifecycle-*`、`Saved/PerformanceResidency20261013/Before` 与 `StaleLinkObjects` 现从该清单恢复。

当前生产文件、原始采样/崩溃证据、尚未完成的预热源码以及资产恢复依赖均保留。不要把未验证方案或诊断失败的样本当作没有价值的垃圾删除。

## 后续恢复顺序

1. 用户明确继续后，先确认加载了最新 Editor DLL，并验证预览重开及退出试玩稳定性。
2. 用户打开 UE、尚未试玩时，通过现有批次互斥桥挂载 `Tools/Performance/capture_dungeon_monster_attribution.py`。检查版本和 armed 回执；正式刷怪后 40 秒自动停录与导出。
3. 确认 `complete`、CPU/GPU scope 和补充 JSON 的区间完整；分析同次刷怪前/低帧/恢复阶段，不让回调间隔冒充帧时间。
4. 根据新的归因处理等价重复工作，再评估完整 GPU 预热、驻留问题和 40–50 怪同屏。保留画质、模型/衣服、光追、波次及战斗规则。
