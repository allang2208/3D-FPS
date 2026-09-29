# 地牢房间收尾与源码发布（2026-09-29）

当前房池为原五间 + 已接入的地下车站/隔离病区，共七间。剩余温室、数据档案中心、焚化处理厅已写入 [待办](../Backlog.md)；本轮不开始新房制作。病区临时测试经用户反馈结束，生产房间继续保留。

## 归档与当前入口

第一批 182 份旧参数/作者快照、Blender 自动备份、独立地图安装器、旧程序血迹、一次性迁移脚本及旧病区独立地图，共 565,151,031 字节，已完成移动及散列核对；随后用户自行清空整个 trash，并明确告知“我已删除，你继续操作”。第一批及旧尺寸源码/车站/临时测试归档不再可恢复，保留清单记录，不重新恢复废案。

第二批 **293 份、734,583,536 字节** 当前保存在 `trash/dungeon-rooms-closeout-20260929/`：290 个已退役尺寸/偏移包、旧维修桌台 UE 包/FBX、旧病区样板封板包。后台及现有编辑器 AssetRegistry 引用读取确认 292 个 UE 包没有集合外引用或已加载对象，当前 catalog/运行源码也无旧尺寸资产路径。移动前后逐文件散列一致，第二批清单落盘完成。完整 [归档清单](Publication20260929/archive-manifest.json) 区分现存 entries 与用户已清空的 cleared_entries；[既有归档记录](Publication20260929/prior-archives.json) 仅保留历史位置。

当前生产源码、活跃资源、原始 licensed 素材、Blender/FBX、材质源、姿态/图集提取数据和落盘回执保留。床资产导入功能提取至 `BedScatter/Scripts/import_bed.py`，不加载退役独立地图。NDD 上游继续作为许可/设计参考，未安装为插件。

制作入口见 [车站](../../SourceAssets/DungeonTransitStation20260928/README.md) 与 [病区](../../SourceAssets/DungeonIsolationWard20260929/README.md)。病区 README、总体方案、缺件清单和血迹说明已更正到当前生产状态。PCG 个人技能与仓库镜像同步，新增 [特殊房与室内接入](../../skills/ue5-pcg-building/references/special-dungeon-interiors.md)，并标注旧通风组合配方退役。

## Git 边界

发布本轮作者脚本/参数、当前 catalog、恢复原五房的删除、道具精修、制作记录、来源与 SKILL。二进制 Content、模型、贴图、导入回执、原始下载和 trash 均不上传；来源与再分发边界见 [病区资产署名](../../ThirdPartyNotices/ISOLATION_WARD_ASSETS.md)。

**公共仓库仍不是完整可运行的本机工程。** 与前次地牢发布相同，生成器/遭遇/怪物接口和共享攻击链路依赖尚未整体公开的宿主接口。此次用 [运行源码交接补丁](Publication20260929/dungeon-runtime-handoff.patch) 保存 30 份地牢源码增量与新组件；基础提交、散列和缺失接口见 [运行清单](Publication20260929/runtime-handoff.json)。本轮补丁使用零上下文且归一化行尾，在准备好的接入目录用 `git apply --unidiff-zero --ignore-space-change`；已通过只读 apply-check。补丁相对其记录的 public base，已包含既有地牢差异，不应与旧补丁重复叠加，也不要应用到本机完整宿主。

共享武器、技能、工具和门文件含其他任务变更，未整份发布；只保留 [玻璃接触点摘录](Publication20260929/glass-contact-sites.json) 和 [两个精确辅助函数](Publication20260929/shared-glass-functions.json) 供人工接入。这些文档不参与编译，不宣称源码公开即已补齐所有共享依赖。本机已完成的正式 DLL 与地图不受发布影响。

仓库整理时本地 HEAD 与 origin/main 各有不同提交，未发布的另一任务提交不在本轮授权范围。app worktree 工具因当前聊天 cwd 不是该 Git 工程返回不可用，因此在同一 Git 仓库下建立临时 detached worktree，基于 origin/main 仅复制明确文件并提交；不改变宿主分支、索引或并行修改，不建立常驻同步副本。普通 `HEAD:main` 推送后回读远端 SHA；工作树完成后移除，发布提交留在远端/本地引用中。

## 本轮检查与未测边界

只做用户要求的发布检查：完整暂存差异、大小、敏感数据、许可边界、文本格式/脚本语法、归档散列、出站提交范围和远端 SHA。删除旧地图前只读当前运行世界为 DayNight、旧病区地图未加载且无未保存地图；没有关闭或重启用户 UE；退役资源引用读取使用只读后台 commandlet 和现有编辑器桥，不进行游戏测试。

不重导生产资产、不构建或运行游戏/PIE、布局、导航、性能或视觉验收。资产导入脚本提取不等于再次执行导入。上一轮病区退役构建日志 `Saved/BuildEditor/build-20260929-231035.log` 属历史已成功结果，用户测试反馈与本轮发布检查分开。
