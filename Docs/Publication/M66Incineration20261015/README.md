# M66 与焚化区发布记录

本轮从 `D:/FPS3D/FPSGAME` 发布到 `https://github.com/allang2208/3D-FPS.git` 的 `main`。用户已停止玩法排查，本次仅整理废案、沉淀技能和检查 Git 发布内容，没有重开 UE、构建或运行游戏。

## 公开内容与前置

直接公开 M66 的 41 个专属原生源码文件、共享战斗/导航/弱点/尸体中的 M66 增量、制作与导入脚本、六件焚化区收集物目录、五类掉落池和 40 个容器绑定。源码中保留显式启用的历史诊断入口，正常地图与 F6 不自动执行诊断。

共享文件按具名 Git 基线选择本轮修改，工作区的其他怪物、性能、武器、地图与技能改动保留。`Config/DefaultGame.ini` 同时记录 M66、区域怪物和收集物软引用的 Cook 目录；焚化区三个既有依赖的条目采用数组追加前缀 `+`。

[regional-integration.patch](regional-integration.patch) 保存 **11 个区域接入目标**，包括两个独立实现文件及共享生成、任务、门禁、状态复制的增量。它依赖尚未完整公开的地牢区域、生成准备队列和共享任务框架，**不能直接应用到干净公开检出，也不要重复应用到当前本机工程**。[integration-manifest.json](integration-manifest.json) 记录每个目标的 UTF-8/LF 前置/结果 SHA-256；多数前置是从当前整合源码中移除本轮增量得到的上下文，不是独立历史提交。先恢复依赖并核对散列，再使用 `git apply --unidiff-zero`；不匹配时按函数合并。完整前置/结果留在本机 `Saved/PublicationM66Incineration20261015/integration/`。

源码切片不等于可独立构建的完整工程；本机已有整合源码与资产并未因发布拆分而改变。恢复完整内容仍遵循 [AssetSetup](../../AssetSetup.md)。

## M66 当前组合

恢复入口为 [M66 README](../../../SourceAssets/IncineratorBossM66/README.md)，原蓝图 `/Game/Monsters/IncineratorBossM66/BP_M66RigPreview` 保持稳定。当前使用 V17 网格/炉息、V08 横扫、V16 握拳砸地、V07 物理资产、V10 下垂组织动态、V19 烟团历史/音效、V20 裂口弱点、V21 倒地/起身和 V22/V23 原生恢复。V01/V02/V03 等仍是作者与动作的重建输入。

横扫参考大型领主伤害档位，逐目标去重；砸地采用扩散冲击波、范围伤害与 2 秒眩晕，落拳后停顿 0.5 秒；炉息采用服务器动作时钟、锁定喷吐方向、逐跳空间/遮挡判断与中断清理。烟团历史、尸体最终姿态和声音序号覆盖晚加入恢复，声音按服务器进度跳过过期事件。

音效配方复用本机鼓囊、悬钟、螺柱和 M10 的授权声音，另存 M66 版本；保留 V17 吸气/喷吐，V19 增加左右脚步、受伤、死亡、落地、横扫挥动/命中、砸地、背烟和收势等十个绑定。公开处理脚本，不上传供体或处理后的音频。Niagara/魔法龙息供体与模型同样留本机，许可不随脚本发布而转授。

## 焚化区配置

| 房间 | 配置 |
| --- | --- |
| 第一间 ShoredBreach | 共 6～8 名普通技术员/搬运工，两种各至少一名 |
| 第二间 AbandonedIncineratorHall 一层 | 共 6～8 名普通技术员/搬运工，另有两只百目 |
| 第二间负一层 | 两只百目、两只螳螂；活着的任一玩家下楼进入后由服务器一次释放，进入前只有待生成槽位，不会受枪声吸引上楼 |
| 第三间 AbandonedFlueGasStation | 两只百目和一只指定 M66 首领，放在中央地面通道 |

本区域目标 `treatment.incinerator_m66` 只由指定首领实际死亡完成；F6 生成、销毁或生成失败不会替代击杀。主客机共享本轮 `RunId/Revision` 进度及两端闸门状态，剩余普通怪不作为开门条件；玩家所在区域决定其追踪栏视图。详见 [区域配方](../../../SourceAssets/IncinerationEncounter20261015/README.md)。

六件蓝/紫收集物及五池具体百分比见 [收集物记录](../../../SourceAssets/IncinerationCollectibles20261015/README.md)。五池首次搜索固定一件；蓝色以上约束仅限这些池与本批新物品。40 个候选容器 ID 每局选出 17～20 个实体、22～25 个搜索入口；独立抽屉分别绑定。共享实物由服务器生成一次，个人揭示进度独立，已生成/取空/保存的容器不会补刷。

六件当前为 VisualRefineV2，保留 V1/Meshes 稳定对象路径并使用 V2 材质与图标。恢复顺序：父目录基础制作与数据接入 → V2 `setup.py` / `prepare_surfaces.py` / `author_models.py` / `render_icons.py` → staged 导入 → `install_revision.ps1`。父目录制作工具和旧作者输入仍有依赖，未按旧版本号删除。区域收集物的 shared-container / 存档前置见先前 [RegionalLoot 发布](../RegionalLoot20261015/README.md) 与 [搜索收集物发布](../SearchCollectibles20261013/README.md)。

## 归档与技能

[archive-manifest.json](archive-manifest.json) 汇总移入 `trash/m66-incineration-retired-20261015/` 的 **13,243 个文件，约 1.25 GiB**；完整逐文件 SHA-256 清单在归档根 `manifest.json`。包含被否定的早期参考图、Blender 自动备份、安装前快照、测试用户缓存、旧 DLL 宿主和一次性工具。移动后已核对散列。临时宿主的两个 junction 仅解除链接，正式 Content 与插件资源没有被移动；保留链接原目标供恢复。活动作者文件、实际 Content、重建依赖和失败记录继续留本机。

个人技能维护源与仓库参考各自增量更新，保留两边已有差异：

- [怪物/M66](../../../skills/ue5-monster-workflow/references/m66-incinerator-boss.md)：双手与躯干的权重归属、根骨缩放、恢复接地、尸体交接、历史烟团与声音年龄。
- [调试/多进程证据](../../../skills/ue5-debug-validation/references/multi-process-runtime-evidence.md)：独立 DLL 不代表硬件隔离、对象散列与链接/运行结果分层、junction 归档、用户叫停边界。
- [物品/收集物](../../../skills/ue5-item-asset-workflow/references/search-collectible-assets.md)：局部稀有度约束、稳定对象路径、实际投影居中及结构材质细节。

公开 Git 只保存原创源码、算法配方、说明、精简归档元数据；用户 Meshy 模型、FBX/Blend/GLB、贴图/图标、音频、UE 包、密集姿态/权重数据、日志、原始回执和构建产物均不上传。`.gitignore` 对本批三个源目录限定了发布范围。

## 历史证据与未完成项

- V19 `Records/network-20261015-123155/summary.json`：真实主机、在线客机、晚加入客机状态检查通过，覆盖烟团、目盲、运动/冻结尸体及声音事件；`-NullRHI -nosound`，不代表画面或试听通过。
- V22 `Records/network-20261015-192708/summary.json`：平地倒地、起身中再击飞及死亡交接的三端检查通过；不是楼梯验证。
- V23 `Records/Hall-20261015-215839`：修正前真实焚化大厅的三端状态同步通过，但起身中段采样表面约浮高 14.32 cm，姿态不合格；其中一具尸体约 20 秒后停止残余运动，原平地超时未被精确复现。
- V23 已制作侧倒/起身地形支撑、站立 IK 交接、真实凸体支撑检测和专属阻尼保留。`Records/compiled_sources.json` 中七份源码与对象校验匹配；当时 DLL 副本/散列回执现位于归档宿主。对象校验本身不能替代成功链接和实际运行证据。
- 修正后 `Records/Hall-20261015-231055` 的渲染联机轮次因 Windows 重启中断，无完成摘要或通过结果。Kernel-Power 41 / EventLog 6008、Bugcheck 0 及此前内存警告不能单独证明重启原因。最后画面复查、狭窄楼梯和原超时复现仍未完成，用户随后叫停。

当前 V23 运行器已移除快照绕过共享互斥的分支，默认为 NullRHI，显式渲染时每轮只渲染指定一端；这是未运行的工具整理。归档/推送不恢复测试授权。焚化区刷怪与收集物真实主客机玩法仍待用户测试。
