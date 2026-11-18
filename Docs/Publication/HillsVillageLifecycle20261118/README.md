# 丘陵村庄制作与联机生命周期：整理发布

本批整理本会话的教堂长椅、神像底座、村庄/铁匠铺制作资料，以及怪物网络加载、夜袭持久化、GC、加入、入场与退出修复。性能复查仍按用户要求暂停；没有为整理或推送重开 UE、运行游戏、截图或渲染。

## 发布范围与恢复

- `Implementation/` 保留本轮独立新增的实现和显式测试夹具，按原目标相对路径组织；`Integration/` 只保存共享文件中本轮新增的补丁、方法片段和接入合同。清单见 [integration-manifest.json](integration-manifest.json)。
- 补丁基底是“当前共享上下文移除这些新增部分”的合成上下文，不冒充历史 Git 提交。零上下文补丁须核对目标/基线后用 `git apply --unidiff-zero` 或逐方法合并；已经接入的本机源文件不要重复套用。
- 共享宿主近期包含其他任务的河湖、木匠 NPC、角色/武器及渲染修改，本批没有整文件搬运这些内容。村庄种植实现快照排除了并行增加的阴影策略；铁匠外观准备需要已有的共享 artisan appearance API。具体依赖见 [接入合同](Integration/CONTRACT.md)。
- 原工程 `Source/` 是唯一运行真源。本发布包用于审阅与恢复，并不表示公开 main 已有完整前置或能从干净检出直接构建游戏；没有构建该公开子集。
- 教堂/铁匠铺/围墙的原创制作配方按 `Tools/` 原路径发布；当前模型、纹理、字体、第三方供体、UE 包和密集动作输入继续保留本机。长椅配置摘录列明 `Rest.ChapelPew.*`、ChapelPew 类型与三个座位，消费者仍是已有 `FPSFurnitureRestComponent`、`FPSFurnitureRestCamera` 与身体动画配置读取链。动画资产与相机采样恢复还需本机资料，不宣称完整动作二进制已经上传。

## 历史证据与待办

本机 Editor / Game 构建回执，以及成功、失败、受干扰和暂停轮次的有限 JSON 保存在 [Evidence](Evidence/)；原始路径索引见 [evidence-index.json](evidence-index.json)。详细原因和测量口径见 [生命周期记录](../../WorldGeneration/hills-lifecycle-network-20261118.md) 与 [怪物加载记录](../../WorldGeneration/hills-monster-network-loading-20261118.md)。

四轮完整本机 UDP 检查通过，60ms 延迟、2% 丢包，首次及后加入客户端各观察 90 秒；八次渲染客户端正常退出未复现原崩溃。活动期 GC 约 23–45ms、新玩家加入主机帧约 83–113ms；初始加载阶段仍有数百毫秒 GC。导航、动物音效和压草编译等待的最后修订已编译，但无外部竞争的最终性能复查未完成。受其他游戏/后台制作影响的两轮数据及用户暂停回执不改写成性能通过。

此处不是公网、专用服务器、全图/整夜战斗、全部武器外观或用户美术验收。正式村庄修复任务仍待用户设计，不在本批补做。

## 归档和保留

按 [逐文件清单](retired-files.json) 将 7,630 个文件、14,558,699,055 字节（约 13.56 GiB）及 69 个目录联接移入 `trash/hills-village-lifecycle-20261118/`，其中有 2,342 张检测图、12 个 GIF。[归档回执](archive-receipt.json)记录逐文件 SHA-256 读回；联接只移动自身，不遍历或移动活动 Content/Plugins/Shaders 目标。没有永久删除，也不将同盘移动称为释放磁盘空间。

保留正式 `Saved/SaveGames`、当前生产资产与主工程构建产物；保留 `Saved/HillsNetLoad20261118/fixed02/OriginalSaveBackup` 和 `lifecycle06/Host/Binaries/Win64` 供用户日后授权恢复复查。原始日志、Trace、重建缓存及旧宿主按同相对路径进入 trash；历史报告中的原路径可据清单定位。

`ChapelFurniture20261116/HandsR2` 的动作输入仍被 HangingHandsR3 作者读取，不能因版本旧而删除。铁匠铺当前 R8/窗口与家具混用早期母版、材质和生成输入，保留这些制作链；灰石底座的纹理/参考图也不属于检测截图。用户提供的临时剪贴板图片、其他任务的丘陵采集/木匠/修女目录不在归档范围。

## SKILL 与 Git

已将可复用经验补入性能、存档联机、调试的对应参考，个人维护源与工程镜像均追加本轮内容。没有修改跨会话记忆。

发布前确认目标为 `https://github.com/allang2208/3D-FPS.git` 的 main。共享工作区已有其他任务暂存，且远端改动与其重叠，按 WORKFLOW 第 8 节使用临时隔离发布工作区；不改变共享分支、索引或工作文件来迁就提交。仅普通非强制推送，完成后读回远端提交；临时发布材料随后归档。
